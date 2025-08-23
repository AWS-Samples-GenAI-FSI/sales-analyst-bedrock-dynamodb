"""
Resource checker to ensure previous cleanup is complete before starting new resources.
"""
import boto3
import time
import os
from dotenv import load_dotenv

load_dotenv()

def wait_for_cleanup_completion(max_wait_seconds=60):
    """
    Check if previous resources are still being deleted.
    
    Returns:
        bool: True if cleanup is complete, False if resources still deleting
    """
    try:
        print("🔍 Checking if previous cleanup is complete...")
        
        redshift = boto3.client(
            'redshift', 
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        ec2 = boto3.client(
            'ec2', 
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Check for deleting Redshift clusters
        try:
            clusters = redshift.describe_clusters()['Clusters']
            deleting_clusters = [c for c in clusters if c['ClusterStatus'] == 'deleting' and c['ClusterIdentifier'].startswith('sales-analyst-')]
            
            if deleting_clusters:
                print(f"⏳ Found {len(deleting_clusters)} Redshift clusters still deleting...")
                return False
        except Exception as e:
            print(f"Error checking Redshift clusters: {e}")
        
        # Check for terminating EC2 instances
        try:
            instances = ec2.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['shutting-down', 'terminating']},
                    {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion*']}
                ]
            )
            
            terminating_instances = []
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name' and 'sales-analyst-bastion' in tag['Value']:
                            terminating_instances.append(instance)
                            break
            
            if terminating_instances:
                print(f"⏳ Found {len(terminating_instances)} EC2 instances still terminating...")
                return False
        except Exception as e:
            print(f"Error checking EC2 instances: {e}")
        
        print("✅ Previous cleanup is complete")
        return True
        
    except Exception as e:
        print(f"Error checking cleanup status: {e}")
        # If we can't check, assume it's safe to proceed
        return True

def check_resource_conflicts():
    """
    Check for any existing sales-analyst resources that might conflict.
    
    Returns:
        dict: Status of existing resources
    """
    try:
        redshift = boto3.client(
            'redshift', 
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        ec2 = boto3.client(
            'ec2', 
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        status = {
            'clusters': [],
            'instances': [],
            'conflicts': False
        }
        
        # Check Redshift clusters
        try:
            clusters = redshift.describe_clusters()['Clusters']
            sales_clusters = [c for c in clusters if c['ClusterIdentifier'].startswith('sales-analyst-')]
            status['clusters'] = [(c['ClusterIdentifier'], c['ClusterStatus']) for c in sales_clusters]
            
            if any(c['ClusterStatus'] in ['creating', 'deleting', 'modifying'] for c in sales_clusters):
                status['conflicts'] = True
        except Exception:
            pass
        
        # Check EC2 instances
        try:
            instances = ec2.describe_instances()
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] in ['pending', 'running', 'shutting-down', 'terminating']:
                        for tag in instance.get('Tags', []):
                            if tag['Key'] == 'Name' and 'sales-analyst-bastion' in tag['Value']:
                                status['instances'].append((instance['InstanceId'], instance['State']['Name']))
                                if instance['State']['Name'] in ['pending', 'shutting-down', 'terminating']:
                                    status['conflicts'] = True
                                break
        except Exception:
            pass
        
        return status
        
    except Exception as e:
        print(f"Error checking resource conflicts: {e}")
        return {'clusters': [], 'instances': [], 'conflicts': False}