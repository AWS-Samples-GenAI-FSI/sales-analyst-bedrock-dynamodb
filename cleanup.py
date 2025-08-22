#!/usr/bin/env python3
"""
Clean up all AWS infrastructure for sales analyst app.
"""
import boto3
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

def cleanup_redshift():
    """Delete Redshift cluster."""
    redshift = boto3.client(
        'redshift', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        # Delete cluster
        redshift.delete_cluster(
            ClusterIdentifier='sales-analyst-cluster',
            SkipFinalClusterSnapshot=True
        )
        print("✅ Redshift cluster deletion initiated")
    except Exception as e:
        print(f"⚠️ Redshift cluster: {e}")

def cleanup_ec2():
    """Delete EC2 bastion host."""
    ec2 = boto3.client(
        'ec2', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        # Find and terminate bastion instance
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
            ]
        )
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                ec2.terminate_instances(InstanceIds=[instance['InstanceId']])
                print(f"✅ Terminated EC2 instance: {instance['InstanceId']}")
    except Exception as e:
        print(f"⚠️ EC2 cleanup: {e}")

def cleanup_iam():
    """Delete IAM role and instance profile."""
    iam = boto3.client(
        'iam', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        # Remove role from instance profile
        iam.remove_role_from_instance_profile(
            InstanceProfileName='EC2-SSM-Role',
            RoleName='EC2-SSM-Role'
        )
        
        # Delete instance profile
        iam.delete_instance_profile(InstanceProfileName='EC2-SSM-Role')
        
        # Detach policy from role
        iam.detach_role_policy(
            RoleName='EC2-SSM-Role',
            PolicyArn='arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
        )
        
        # Delete role
        iam.delete_role(RoleName='EC2-SSM-Role')
        print("✅ IAM role and instance profile deleted")
    except Exception as e:
        print(f"⚠️ IAM cleanup: {e}")

# Key pair cleanup removed - using SSM only

def cleanup_local():
    """Clean up local files."""
    files_to_remove = [
        'metadata_cache.pkl',
        'local_northwind.db'
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)
            print(f"✅ Removed {file}")
    
    # Kill any running SSM sessions
    try:
        subprocess.run(['pkill', '-f', 'aws ssm start-session'], stderr=subprocess.DEVNULL)
        print("✅ Killed SSM sessions")
    except:
        pass

def main():
    print("🧹 Starting cleanup of sales analyst infrastructure...")
    
    cleanup_local()
    cleanup_ec2()
    cleanup_redshift()
    cleanup_iam()
    
    print("\n✅ Cleanup complete! You can now restart the app for a fresh setup.")
    print("Run: streamlit run app.py")

if __name__ == "__main__":
    main()