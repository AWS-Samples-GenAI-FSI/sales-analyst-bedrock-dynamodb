"""Auto tunnel for friends sharing code."""
import subprocess
import socket
import time
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

def ensure_tunnel():
    """Ensure SSM tunnel is active."""
    if test_port():
        print("✅ SSM tunnel already active")
        return True
    
    print("🔗 Creating SSM tunnel...")
    success = create_tunnel()
    if not success:
        print("⚠️ No tunnel available - resources may still be setting up")
    return success

def test_port():
    """Test if port 5439 is accessible and Redshift is responding."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host='localhost',
            port=5439,
            database='sales_analyst',
            user='admin',
            password='Awsuser123$',
            connect_timeout=3
        )
        conn.close()
        return True
    except:
        return False

def create_tunnel():
    """Create SSM tunnel."""
    try:
        print("🔍 Checking Redshift cluster status...")
        redshift = boto3.client('redshift', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        try:
            # Find any available sales-analyst cluster
            clusters = redshift.describe_clusters()['Clusters']
            available_cluster = None
            for cluster in clusters:
                if cluster['ClusterIdentifier'].startswith('sales-analyst-') and cluster['ClusterStatus'] == 'available':
                    available_cluster = cluster
                    break
            
            if not available_cluster:
                print("❌ No available Redshift cluster found")
                return False
                
            redshift_host = available_cluster['Endpoint']['Address']
            print(f"✅ Redshift cluster ready: {available_cluster['ClusterIdentifier']}")
        except Exception:
            print("❌ Error checking Redshift clusters")
            return False
        
        print("🔍 Checking bastion host status...")
        ec2 = boto3.client('ec2', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        try:
            # Find any running sales-analyst bastion
            all_instances = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            bastion_instance = None
            for reservation in all_instances['Reservations']:
                for instance in reservation['Instances']:
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name' and tag['Value'].startswith('sales-analyst-bastion-'):
                            bastion_instance = instance
                            break
                    if bastion_instance:
                        break
                if bastion_instance:
                    break
            
            if not bastion_instance:
                print("❌ Bastion host not found or not running")
                return False
            
            instance_id = bastion_instance['InstanceId']
            bastion_name = next(tag['Value'] for tag in bastion_instance['Tags'] if tag['Key'] == 'Name')
            print(f"✅ Bastion host ready: {bastion_name}")
        except Exception:
            print("❌ Error checking bastion host")
            return False
        
        print("🔗 Establishing SSM tunnel...")
        subprocess.run(['pkill', '-f', 'aws ssm start-session'], stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        subprocess.Popen([
            'aws', 'ssm', 'start-session',
            '--region', os.getenv('AWS_REGION', 'us-east-1'),
            '--target', instance_id,
            '--document-name', 'AWS-StartPortForwardingSessionToRemoteHost',
            '--parameters', f'host={redshift_host},portNumber=5439,localPortNumber=5439'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("⏳ Waiting for tunnel to establish...")
        for i in range(15):
            time.sleep(3)
            if test_port():
                print("✅ SSM tunnel established successfully!")
                return True
        
        print("❌ SSM tunnel failed to establish")
        return False
        
    except Exception as e:
        print(f"❌ Error creating tunnel: {e}")
        return False