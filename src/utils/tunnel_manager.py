"""
Automated SSM tunnel manager for reliable Redshift connections.
"""
import boto3
import subprocess
import time
import socket
import os
import threading
from dotenv import load_dotenv

load_dotenv()

class TunnelManager:
    def __init__(self):
        self.tunnel_process = None
        self.monitoring = False
        
    def test_connection(self, timeout=2):
        """Test if localhost:5439 is accessible."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(('localhost', 5439))
            sock.close()
            return result == 0
        except:
            return False
    
    def get_cluster_info(self):
        """Get Redshift cluster and bastion instance info."""
        try:
            # Get Redshift endpoint
            redshift = boto3.client(
                'redshift', 
                region_name=os.getenv('AWS_REGION', 'us-east-1'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            cluster_response = redshift.describe_clusters(ClusterIdentifier='sales-analyst-cluster')
            redshift_host = cluster_response['Clusters'][0]['Endpoint']['Address']
            
            # Get bastion instance
            ec2 = boto3.client(
                'ec2', 
                region_name=os.getenv('AWS_REGION', 'us-east-1'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            ec2_response = ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                    {'Name': 'instance-state-name', 'Values': ['running']}
                ]
            )
            
            if ec2_response['Reservations']:
                instance_id = ec2_response['Reservations'][0]['Instances'][0]['InstanceId']
                return redshift_host, instance_id
            return redshift_host, None
        except:
            return None, None
    
    def create_tunnel(self):
        """Create SSM tunnel."""
        redshift_host, instance_id = self.get_cluster_info()
        
        if not redshift_host or not instance_id:
            return False
        
        # Kill existing sessions
        subprocess.run(['pkill', '-f', 'aws ssm start-session'], stderr=subprocess.DEVNULL)
        time.sleep(2)
        
        # Create tunnel
        cmd = [
            'aws', 'ssm', 'start-session',
            '--region', os.getenv('AWS_REGION', 'us-east-1'),
            '--target', instance_id,
            '--document-name', 'AWS-StartPortForwardingSessionToRemoteHost',
            '--parameters', f'host={redshift_host},portNumber=5439,localPortNumber=5439'
        ]
        
        try:
            self.tunnel_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
            )
            
            # Wait for tunnel to establish
            for _ in range(15):
                if self.test_connection():
                    return True
                time.sleep(2)
            return False
        except:
            return False
    
    def ensure_tunnel(self):
        """Ensure tunnel is active, create if needed."""
        if self.test_connection():
            return True
        return self.create_tunnel()
    
    def start_monitoring(self):
        """Start background tunnel monitoring."""
        if self.monitoring:
            return
            
        self.monitoring = True
        
        def monitor():
            while self.monitoring:
                if not self.test_connection():
                    self.create_tunnel()
                time.sleep(30)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def stop(self):
        """Stop tunnel and monitoring."""
        self.monitoring = False
        if self.tunnel_process:
            self.tunnel_process.terminate()
        subprocess.run(['pkill', '-f', 'aws ssm start-session'], stderr=subprocess.DEVNULL)

# Global instance
tunnel_manager = TunnelManager()