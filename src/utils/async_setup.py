"""
Async infrastructure setup to avoid blocking the UI.
"""
import boto3
import os
import time
from dotenv import load_dotenv

load_dotenv()

def check_infrastructure_status():
    """
    Quick check of infrastructure status without blocking.
    
    Returns:
        dict: Status information
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
        
        # Check Redshift clusters
        try:
            clusters = redshift.describe_clusters()['Clusters']
            sales_clusters = [c for c in clusters if c['ClusterIdentifier'].startswith('sales-analyst-')]
            
            if not sales_clusters:
                return {'status': 'none', 'message': 'No infrastructure found'}
            
            for cluster in sales_clusters:
                if cluster['ClusterStatus'] == 'available':
                    # Check if we can connect
                    try:
                        from .redshift_connector import get_redshift_connection
                        conn = get_redshift_connection()
                        conn.close()
                        return {'status': 'ready', 'message': 'Infrastructure ready'}
                    except:
                        return {'status': 'creating', 'message': 'Setting up connection...'}
                elif cluster['ClusterStatus'] == 'creating':
                    return {'status': 'creating', 'message': 'Creating Redshift cluster...'}
                elif cluster['ClusterStatus'] == 'deleting':
                    return {'status': 'deleting', 'message': 'Deleting old resources...'}
                    
        except Exception:
            pass
        
        # Check EC2 instances
        try:
            instances = ec2.describe_instances()
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name' and 'sales-analyst-bastion' in tag['Value']:
                            if instance['State']['Name'] == 'terminating':
                                return {'status': 'deleting', 'message': 'Cleaning up old resources...'}
                            elif instance['State']['Name'] == 'pending':
                                return {'status': 'creating', 'message': 'Starting bastion host...'}
        except Exception:
            pass
        
        return {'status': 'none', 'message': 'No infrastructure found'}
        
    except Exception as e:
        return {'status': 'error', 'message': f'Error checking status: {str(e)}'}

def start_infrastructure_async():
    """
    Start infrastructure creation without blocking.
    """
    try:
        from .redshift_cluster_manager import create_redshift_cluster
        # This will run in background
        create_redshift_cluster()
        return True
    except Exception as e:
        print(f"Error starting infrastructure: {e}")
        return False

def quick_connection_test():
    """
    Quick connection test without waiting.
    
    Returns:
        bool: True if connected, False otherwise
    """
    try:
        from .redshift_connector import get_redshift_connection
        conn = get_redshift_connection()
        conn.close()
        return True
    except:
        return False