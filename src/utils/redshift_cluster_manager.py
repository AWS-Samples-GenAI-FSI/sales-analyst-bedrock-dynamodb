"""
Redshift cluster manager for automatic cluster creation.
"""
import boto3
import time
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

def create_ssm_role():
    """Create IAM role for SSM access."""
    iam = boto3.client(
        'iam', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        # Check if role exists
        iam.get_role(RoleName='EC2-SSM-Role')
        return True
    except iam.exceptions.NoSuchEntityException:
        # Create role
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "ec2.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        iam.create_role(
            RoleName='EC2-SSM-Role',
            AssumeRolePolicyDocument=str(trust_policy).replace("'", '"')
        )
        
        # Attach SSM policy
        iam.attach_role_policy(
            RoleName='EC2-SSM-Role',
            PolicyArn='arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore'
        )
        
        # Create instance profile
        try:
            iam.create_instance_profile(InstanceProfileName='EC2-SSM-Role')
            iam.add_role_to_instance_profile(
                InstanceProfileName='EC2-SSM-Role',
                RoleName='EC2-SSM-Role'
            )
        except iam.exceptions.EntityAlreadyExistsException:
            pass
        
        print("Created SSM role and instance profile")
        time.sleep(10)  # Wait for role to propagate
        return True
    except Exception as e:
        print(f"Error creating SSM role: {e}")
        return False

def create_key_pair():
    """Create SSH key pair for bastion host."""
    ec2 = boto3.client(
        'ec2', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        # Check if key pair exists
        ec2.describe_key_pairs(KeyNames=['sales-analyst-key'])
        return True
    except ec2.exceptions.ClientError:
        # Create key pair
        response = ec2.create_key_pair(KeyName='sales-analyst-key')
        
        # Save private key locally
        key_path = os.path.expanduser('~/.ssh/sales-analyst-key.pem')
        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        
        with open(key_path, 'w') as f:
            f.write(response['KeyMaterial'])
        
        # Set proper permissions
        os.chmod(key_path, 0o600)
        print(f"Created SSH key: {key_path}")
        return True

def create_bastion_host():
    """Create EC2 bastion host for SSH tunnel."""
    ec2 = boto3.client(
        'ec2', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        # Create SSM role and key pair
        create_ssm_role()
        create_key_pair()
        
        # Check if bastion exists
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        if response['Reservations']:
            instance = response['Reservations'][0]['Instances'][0]
            return instance['InstanceId']
        
        # Create bastion host with SSM role and updated AMI
        response = ec2.run_instances(
            ImageId='ami-0c02fb55956c7d316',  # Amazon Linux 2 (stable)
            MinCount=1,
            MaxCount=1,
            InstanceType='t3.micro',
            IamInstanceProfile={'Name': 'EC2-SSM-Role'},
            SecurityGroups=['default'],
            UserData='''
#!/bin/bash
yum update -y
yum install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl restart amazon-ssm-agent
# Wait for SSM agent to be ready
sleep 30
            ''',
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': 'sales-analyst-bastion'}]
                }
            ]
        )
        
        instance_id = response['Instances'][0]['InstanceId']
        
        # Wait for instance to be running
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        
        # Wait for SSM agent to be ready (silent)
        ssm = boto3.client(
            'ssm', 
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Wait up to 10 minutes for SSM agent to connect (silent)
        for i in range(60):  # 60 attempts, 10 seconds each = 10 minutes
            try:
                response = ssm.describe_instance_information(
                    Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}]
                )
                if response['InstanceInformationList']:
                    instance_info = response['InstanceInformationList'][0]
                    if instance_info['PingStatus'] == 'Online':
                        break
                time.sleep(10)
            except Exception:
                time.sleep(10)
        
        # Return instance ID for SSM
        return instance_id
        
    except Exception as e:
        print(f"Error creating bastion host: {e}")
        return None

def create_ssm_tunnel(instance_id, redshift_host):
    """Create SSM port forwarding session."""
    import subprocess
    
    # Check if session manager plugin is installed
    try:
        subprocess.run(['session-manager-plugin'], capture_output=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("Installing Session Manager plugin...")
        try:
            # Download and install Session Manager plugin
            subprocess.run(['curl', '-o', '/tmp/sessionmanager-bundle.zip', 
                          'https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip'], 
                          check=True)
            subprocess.run(['unzip', '-o', '/tmp/sessionmanager-bundle.zip', '-d', '/tmp/'], check=True)
            subprocess.run(['sudo', '/tmp/sessionmanager-bundle/install', 
                          '-i', '/usr/local/sessionmanagerplugin', 
                          '-b', '/usr/local/bin/session-manager-plugin'], check=True)
            print("Session Manager plugin installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install Session Manager plugin: {e}")
            print("Please install manually:")
            print("curl 'https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip' -o 'sessionmanager-bundle.zip'")
            print("unzip sessionmanager-bundle.zip")
            print("sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin")
            return False
    
    # Kill any existing session
    subprocess.run(['pkill', '-f', 'aws ssm start-session'], stderr=subprocess.DEVNULL)
    time.sleep(2)
    
    # Wait for SSM to be fully ready (silent)
    time.sleep(60)
    
    # Test SSM connectivity
    ssm = boto3.client(
        'ssm', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    try:
        response = ssm.describe_instance_information(
            Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}]
        )
        if not response['InstanceInformationList']:
            print("Instance not found in SSM")
            return False
        
        instance_info = response['InstanceInformationList'][0]
        if instance_info['PingStatus'] != 'Online':
            print(f"Instance SSM status: {instance_info['PingStatus']}")
            return False
        
        pass  # SSM ready
    except Exception as e:
        print(f"SSM connectivity check failed: {e}")
        return False
    
    # Create SSM port forwarding session with explicit region
    cmd = [
        'aws', 'ssm', 'start-session',
        '--region', os.getenv('AWS_REGION', 'us-east-1'),
        '--target', instance_id,
        '--document-name', 'AWS-StartPortForwardingSessionToRemoteHost',
        '--parameters', f'host={redshift_host},portNumber=5439,localPortNumber=5439'
    ]
    
    try:
        # Start session in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        
        # Give it time to establish
        time.sleep(10)
        
        # Check if process is still running (means session is active)
        if process.poll() is None:
            pass  # Session started
            
            # Test if port forwarding is working
            import socket
            for i in range(10):  # Try for 30 seconds
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(('localhost', 5439))
                    sock.close()
                    
                    if result == 0:
                        return True
                    else:
                        time.sleep(3)
                except Exception as e:
                    print(f"Port test error: {e}")
                    time.sleep(3)
            
            pass  # Port test failed
            process.terminate()
            return False
        else:
            stdout, stderr = process.communicate()
            pass  # Session failed
            return False
            
    except Exception as e:
        print(f"SSM session error: {e}")
        return False

def create_redshift_cluster():
    """Create Redshift cluster and SSH tunnel if it doesn't exist."""
    import threading
    from .northwind_bootstrapper import download_northwind_data
    
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
    cluster_id = 'sales-analyst-cluster'
    
    # Start data download in background
    download_result = {'path': None}
    def download_data():
        print("Starting parallel data download...")
        download_result['path'] = download_northwind_data()
        print(f"Data download completed: {download_result['path']}")
    
    download_thread = threading.Thread(target=download_data, daemon=True)
    download_thread.start()
    
    try:
        # Check if cluster exists
        response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
        cluster = response['Clusters'][0]
        if cluster['ClusterStatus'] == 'available':
            # Update security group for existing cluster
            try:
                import requests
                local_ip = requests.get('https://api.ipify.org').text
                
                # Get cluster's VPC security groups
                vpc_security_groups = cluster['VpcSecurityGroups']
                for sg in vpc_security_groups:
                    sg_id = sg['VpcSecurityGroupId']
                    
                    # Add rule to allow local IP
                    try:
                        ec2.authorize_security_group_ingress(
                            GroupId=sg_id,
                            IpPermissions=[
                                {
                                    'IpProtocol': 'tcp',
                                    'FromPort': 5439,
                                    'ToPort': 5439,
                                    'IpRanges': [{'CidrIp': f'{local_ip}/32'}]
                                }
                            ]
                        )
                        print(f"Added security group rule for IP: {local_ip}")
                    except:
                        print(f"Security group rule may already exist for IP: {local_ip}")
            except Exception as e:
                print(f"Error updating security group: {e}")
            
            # Check if tunnel is already working
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', 5439))
                sock.close()
                
                if result == 0:
                    pass  # Tunnel working
                    return 'localhost'
            except:
                pass
            
            # Create bastion host and SSM tunnel only if needed
            instance_id = create_bastion_host()
            if instance_id:
                print(f"Bastion instance ready: {instance_id}")
                if create_ssm_tunnel(instance_id, cluster['Endpoint']['Address']):
                    return 'localhost'
                else:
                    print("SSM tunnel failed")
            return cluster['Endpoint']['Address']
    except redshift.exceptions.ClusterNotFoundFault:
        # Create cluster with public access
        redshift.create_cluster(
            ClusterIdentifier=cluster_id,
            NodeType='ra3.xlplus',
            MasterUsername='admin',
            MasterUserPassword='Awsuser123$',
            DBName='sales_analyst',
            ClusterType='single-node',
            PubliclyAccessible=True,
            Port=5439,
            ClusterSubnetGroupName='default'
        )
        
        # Get local IP and allow access
        try:
            import requests
            local_ip = requests.get('https://api.ipify.org').text
            redshift.authorize_cluster_security_group_ingress(
                ClusterSecurityGroupName='default',
                CIDRIP=f'{local_ip}/32'
            )
            print(f"Authorized access for IP: {local_ip}")
        except:
            pass  # May already exist or using VPC
        
        # Wait for cluster to be available
        while True:
            response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
            status = response['Clusters'][0]['ClusterStatus']
            if status == 'available':
                cluster_endpoint = response['Clusters'][0]['Endpoint']['Address']
                
                # Wait for download to complete
                print("Waiting for data download to complete...")
                download_thread.join(timeout=60)  # Wait max 1 minute
                
                # Store download result for later use
                if download_result['path']:
                    os.environ['NORTHWIND_DATA_PATH'] = download_result['path']
                    print(f"Data ready at: {download_result['path']}")
                
                return cluster_endpoint
            time.sleep(30)
    
    return None