#!/usr/bin/env python3
"""
Fix SSM tunnel connection for Redshift access.
"""
import boto3
import subprocess
import time
import os
import socket
from dotenv import load_dotenv

load_dotenv()

def get_redshift_endpoint():
    """Get the Redshift cluster endpoint."""
    redshift = boto3.client(
        'redshift', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        response = redshift.describe_clusters(ClusterIdentifier='sales-analyst-cluster')
        return response['Clusters'][0]['Endpoint']['Address']
    except Exception as e:
        print(f"Error getting Redshift endpoint: {e}")
        return None

def get_bastion_instance():
    """Get the bastion instance ID."""
    ec2 = boto3.client(
        'ec2', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        if response['Reservations']:
            return response['Reservations'][0]['Instances'][0]['InstanceId']
        return None
    except Exception as e:
        print(f"Error getting bastion instance: {e}")
        return None

def test_port_connection(host='localhost', port=5439, timeout=2):
    """Test if port is accessible."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def create_ssm_tunnel():
    """Create SSM tunnel to Redshift."""
    redshift_host = get_redshift_endpoint()
    instance_id = get_bastion_instance()
    
    if not redshift_host:
        print("❌ Could not get Redshift endpoint")
        return False
        
    if not instance_id:
        print("❌ Could not get bastion instance")
        return False
    
    print(f"🔗 Creating tunnel: {instance_id} -> {redshift_host}:5439")
    
    # Kill existing sessions
    subprocess.run(['pkill', '-f', 'aws ssm start-session'], stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # Create new session
    cmd = [
        'aws', 'ssm', 'start-session',
        '--region', os.getenv('AWS_REGION', 'us-east-1'),
        '--target', instance_id,
        '--document-name', 'AWS-StartPortForwardingSessionToRemoteHost',
        '--parameters', f'host={redshift_host},portNumber=5439,localPortNumber=5439'
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        
        print("⏳ Establishing tunnel...")
        time.sleep(10)
        
        # Test connection
        for i in range(10):
            if test_port_connection():
                print("✅ Tunnel established successfully!")
                return True
            time.sleep(2)
            
        print("❌ Tunnel failed to establish")
        process.terminate()
        return False
        
    except Exception as e:
        print(f"❌ Error creating tunnel: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Fixing SSM tunnel connection...")
    
    if test_port_connection():
        print("✅ Port 5439 is already accessible")
    else:
        print("🔧 Creating SSM tunnel...")
        if create_ssm_tunnel():
            print("✅ Tunnel fixed! You can now restart the Streamlit app.")
        else:
            print("❌ Failed to fix tunnel. Check AWS credentials and permissions.")