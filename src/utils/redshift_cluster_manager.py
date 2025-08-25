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



def create_bastion_host():
    """Create EC2 bastion host for SSH tunnel."""
        
    ec2 = boto3.client(
        'ec2', 
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    
    try:
        # Create SSM role only
        create_ssm_role()
        
        # Check if bastion exists
        bastion_name = 'sales-analyst-bastion'
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [bastion_name]},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        
        if response['Reservations']:
            instance = response['Reservations'][0]['Instances'][0]
            return instance['InstanceId']
        
        # Get default VPC and create/update security group for bastion
        vpc_response = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        if not vpc_response['Vpcs']:
            print("No default VPC found")
            return None
        
        vpc_id = vpc_response['Vpcs'][0]['VpcId']
        
        # Create or get bastion security group
        try:
            sg_response = ec2.describe_security_groups(
                Filters=[
                    {'Name': 'group-name', 'Values': ['sales-analyst-bastion-sg']},
                    {'Name': 'vpc-id', 'Values': [vpc_id]}
                ]
            )
            if sg_response['SecurityGroups']:
                sg_id = sg_response['SecurityGroups'][0]['GroupId']
            else:
                # Create security group
                sg_response = ec2.create_security_group(
                    GroupName='sales-analyst-bastion-sg',
                    Description='Security group for sales analyst bastion host',
                    VpcId=vpc_id
                )
                sg_id = sg_response['GroupId']
                
                # Add outbound rule for Redshift (port 5439)
                ec2.authorize_security_group_egress(
                    GroupId=sg_id,
                    IpPermissions=[
                        {
                            'IpProtocol': 'tcp',
                            'FromPort': 5439,
                            'ToPort': 5439,
                            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                        }
                    ]
                )
                print(f"Created bastion security group: {sg_id}")
        except Exception as e:
            print(f"Error with security group: {e}")
            sg_id = None
        
        # Create bastion host with proper security group
        run_params = {
            'ImageId': 'ami-0c02fb55956c7d316',  # Amazon Linux 2 (stable)
            'MinCount': 1,
            'MaxCount': 1,
            'InstanceType': 't3.micro',
            'IamInstanceProfile': {'Name': 'EC2-SSM-Role'},
            'UserData': '''
#!/bin/bash
yum update -y
yum install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl restart amazon-ssm-agent
# Wait for SSM agent to be ready
sleep 30
            ''',
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': bastion_name}]
                }
            ]
        }
        
        if sg_id:
            run_params['SecurityGroupIds'] = [sg_id]
        else:
            run_params['SecurityGroups'] = ['default']
        
        response = ec2.run_instances(**run_params)
        
        instance_id = response['Instances'][0]['InstanceId']
        
        # Wait for instance to be running
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        
        # Wait for SSM agent to be ready
        print("Waiting for SSM agent to be ready...")
        ssm = boto3.client(
            'ssm', 
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Wait up to 10 minutes for SSM agent to connect
        for i in range(60):  # 60 attempts, 10 seconds each = 10 minutes
            try:
                response = ssm.describe_instance_information(
                    Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}]
                )
                if response['InstanceInformationList']:
                    instance_info = response['InstanceInformationList'][0]
                    if instance_info['PingStatus'] == 'Online':
                        print(f"SSM agent is online after {i*10} seconds")
                        break
                if i % 6 == 0:  # Show progress every minute
                    print(f"Waiting for SSM agent... ({i*10}s elapsed)")
                time.sleep(10)
            except Exception as e:
                print(f"Checking SSM status: {e}")
                time.sleep(10)
        else:
            print("SSM agent did not come online within 10 minutes")
        
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
    
    # Wait for SSM to be fully ready
    print("Allowing extra time for SSM to stabilize...")
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
        
        print("SSM connectivity confirmed")
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
    
    print(f"Starting SSM session with command: {' '.join(cmd)}")
    
    try:
        # Start session in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        
        # Give it time to establish
        print("Waiting for SSM session to establish...")
        time.sleep(15)  # Increased wait time
        
        # Check if process is still running (means session is active)
        if process.poll() is None:
<<<<<<< HEAD
            print("SSM port forwarding session started")
=======
            print("SSM session process is running, testing port forwarding...")
>>>>>>> 3f9252b (✅ Complete private Redshift setup with bastion host)
            
            # Test if port forwarding is working
            import socket
            for i in range(15):  # Try for 45 seconds
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex(('localhost', 5439))
                    sock.close()
                    
                    if result == 0:
<<<<<<< HEAD
                        print("Port forwarding is working")
                        return True
                    else:
                        print(f"Port test attempt {i+1}/10...")
=======
                        print(f"✅ Port forwarding working on attempt {i+1}")
                        return True
                    else:
                        print(f"Port test {i+1}/15 failed, retrying...")
>>>>>>> 3f9252b (✅ Complete private Redshift setup with bastion host)
                        time.sleep(3)
                except Exception as e:
                    print(f"Port test {i+1}/15 error: {e}")
                    time.sleep(3)
            
<<<<<<< HEAD
            print("Port forwarding test failed")
=======
            print("❌ Port forwarding test failed after 15 attempts")
>>>>>>> 3f9252b (✅ Complete private Redshift setup with bastion host)
            process.terminate()
            return False
        else:
            stdout, stderr = process.communicate()
<<<<<<< HEAD
            print(f"SSM session failed: {stderr.decode()}")
=======
            print(f"❌ SSM session failed to start")
            print(f"STDOUT: {stdout.decode() if stdout else 'None'}")
            print(f"STDERR: {stderr.decode() if stderr else 'None'}")
>>>>>>> 3f9252b (✅ Complete private Redshift setup with bastion host)
            return False
            
    except Exception as e:
        print(f"❌ SSM session error: {e}")
        return False

def create_redshift_cluster():
    """Create Redshift cluster and SSH tunnel if it doesn't exist."""
    import threading
    from datetime import datetime
    from .northwind_bootstrapper import download_northwind_data
    
    print("🚀 Starting Redshift cluster setup...")
    
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
    
    # Use simple cluster name
    cluster_id = 'sales-analyst-cluster'
    print(f"📝 Using cluster ID: {cluster_id}")
    
    # Start data download in background
    download_result = {'path': None}
    def download_data():
        print("📦 Loading bundled Northwind data...")
        download_result['path'] = download_northwind_data()
        print(f"✅ Data ready: {download_result['path']}")
    
    download_thread = threading.Thread(target=download_data, daemon=True)
    download_thread.start()
    
    try:
<<<<<<< HEAD
        # Check for existing sales-analyst-cluster
        print("🔍 Checking for existing Redshift cluster...")
        try:
            response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
            cluster = response['Clusters'][0]
            status = cluster['ClusterStatus']
            print(f"📊 Found cluster {cluster_id}: {status}")
            
            if status == 'available':
                print(f"✅ Cluster is available - reusing existing cluster")
                available_cluster = cluster
            elif status == 'deleting':
                print(f"⏳ Cluster is deleting - waiting for completion...")
                # Wait for deletion to complete
                while True:
                    try:
                        response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
                        if response['Clusters'][0]['ClusterStatus'] == 'deleting':
                            print(f"⏳ Still deleting... waiting 30 seconds")
                            time.sleep(30)
                        else:
                            break
                    except redshift.exceptions.ClusterNotFoundFault:
                        print(f"✅ Cluster deletion complete")
                        break
                available_cluster = None
            else:
                print(f"⚠️ Cluster in {status} state - will wait")
                available_cluster = None
        except redshift.exceptions.ClusterNotFoundFault:
            print(f"🔍 No existing cluster found")
            available_cluster = None
        
        if available_cluster:
            cluster = available_cluster
            print(f"🔄 Reusing existing cluster: {cluster['ClusterIdentifier']}")
            print(f"📍 Cluster endpoint: {cluster['Endpoint']['Address']}")
            
            # Update security group for existing cluster
            print("🔒 Updating security group for existing cluster...")
            try:
                import requests
                print("🌐 Getting local IP address...")
                local_ip = requests.get('https://api.ipify.org').text
                print(f"📍 Local IP: {local_ip}")
                
                # Get cluster's VPC security groups
                vpc_security_groups = cluster['VpcSecurityGroups']
                print(f"🛡️ Found {len(vpc_security_groups)} security groups")
                
                for sg in vpc_security_groups:
                    sg_id = sg['VpcSecurityGroupId']
                    print(f"   - Updating security group: {sg_id}")
                    
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
                        print(f"✅ Added security group rule for IP: {local_ip}")
                    except Exception as e:
                        print(f"⚠️ Security group rule may already exist for IP: {local_ip} ({e})")
            except Exception as e:
                print(f"❌ Error updating security group: {e}")
            
            # Check if tunnel is already working
            print("🔍 Checking if existing tunnel is working...")
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', 5439))
                sock.close()
                
                if result == 0:
                    print("✅ Existing tunnel is working - using localhost connection")
                    return 'localhost'
                else:
                    print("❌ No existing tunnel found - need to create SSM tunnel")
            except Exception as e:
                print(f"❌ Tunnel check failed: {e}")
            
            # Create bastion host and SSM tunnel only if needed
            print("🏗️ Creating bastion host and SSM tunnel...")
            instance_id = create_bastion_host()
            if instance_id:
                print(f"✅ Bastion instance ready: {instance_id}")
                print(f"🔗 Creating SSM tunnel to: {cluster['Endpoint']['Address']}")
                if create_ssm_tunnel(instance_id, cluster['Endpoint']['Address']):
                    print("✅ SSM tunnel established successfully")
                    os.environ['REDSHIFT_HOST'] = 'localhost'
                    return 'localhost'
                else:
                    print("❌ SSM tunnel failed - falling back to direct connection")
            else:
                print("❌ Failed to create bastion host")
            
            print(f"⚠️ Using direct connection to: {cluster['Endpoint']['Address']}")
            return cluster['Endpoint']['Address']
    except Exception as e:
        print(f"❌ Error checking existing clusters: {e}")
        print("🔄 Proceeding to create new cluster...")
    
    # If no available cluster found, create new one
    print(f"🆕 No available cluster found - creating new cluster: {cluster_id}")
    print("⚙️ Cluster configuration:")
    print("   - Node Type: ra3.xlplus")
    print("   - Database: sales_analyst")
    print("   - Port: 5439")
    print("   - Public Access: Yes")
    
    try:
=======
        # Check if cluster exists
        response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
        cluster = response['Clusters'][0]
        if cluster['ClusterStatus'] == 'available':
            cluster_endpoint = cluster['Endpoint']['Address']
            print(f"✅ Redshift cluster ready: {cluster_endpoint}")
            
            # Check if cluster is publicly accessible
            is_public = cluster.get('PubliclyAccessible', False)
            
            if not is_public:
                # Private cluster - MUST use bastion
                print("Private cluster detected - using bastion host...")
                
                # Check if tunnel is already working
                import socket
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(('localhost', 5439))
                    sock.close()
                    
                    if result == 0:
                        print("✅ SSM tunnel already active")
                        return 'localhost'
                except:
                    pass
                
                # Create bastion host and SSM tunnel
                instance_id = create_bastion_host()
                if instance_id:
                    print(f"✅ Bastion instance ready: {instance_id}")
                    if create_ssm_tunnel(instance_id, cluster_endpoint):
                        print("✅ SSM tunnel established")
                        return 'localhost'
                    else:
                        print("❌ SSM tunnel failed")
                        return None
                else:
                    print("❌ Bastion creation failed")
                    return None
            else:
                # Public cluster - try direct connection with security group update
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
                
                return cluster_endpoint
    except redshift.exceptions.ClusterNotFoundFault:
        # Create cluster in PRIVATE subnet (no public access)
>>>>>>> 3f9252b (✅ Complete private Redshift setup with bastion host)
        redshift.create_cluster(
            ClusterIdentifier=cluster_id,
            NodeType='ra3.xlplus',
            MasterUsername='admin',
            MasterUserPassword='Awsuser123$',
            DBName='sales_analyst',
            ClusterType='single-node',
            PubliclyAccessible=False,  # PRIVATE SUBNET
            Port=5439,
            ClusterSubnetGroupName='default'
        )
<<<<<<< HEAD
        print(f"✅ Cluster creation initiated: {cluster_id}")
    except Exception as e:
        print(f"❌ Failed to create cluster: {e}")
        return None
    
    # Get local IP and allow access
    print("🔒 Configuring cluster security...")
    try:
        import requests
        local_ip = requests.get('https://api.ipify.org').text
        print(f"📍 Authorizing access for IP: {local_ip}")
        redshift.authorize_cluster_security_group_ingress(
            ClusterSecurityGroupName='default',
            CIDRIP=f'{local_ip}/32'
        )
        print(f"✅ Authorized access for IP: {local_ip}")
    except Exception as e:
        print(f"⚠️ Security group authorization: {e} (may already exist or using VPC)")
    
    # Wait for cluster to be available
    print("⏳ Waiting for cluster to become available...")
    for attempt in range(60):  # 30 minutes max
        try:
=======
        
        # No security group changes needed for private cluster
        
        # Wait for cluster to be available
        while True:
>>>>>>> 3f9252b (✅ Complete private Redshift setup with bastion host)
            response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
            status = response['Clusters'][0]['ClusterStatus']
            
            if status == 'available':
                cluster_endpoint = response['Clusters'][0]['Endpoint']['Address']
<<<<<<< HEAD
                print(f"✅ Cluster is ready! Endpoint: {cluster_endpoint}")
                
                # Wait for data loading to complete
                download_thread.join(timeout=60)
                if download_result['path']:
                    os.environ['NORTHWIND_DATA_PATH'] = download_result['path']
                    print(f"✅ Data ready at: {download_result['path']}")
                
                return cluster_endpoint
            elif status in ['creating', 'modifying']:
                if attempt % 6 == 0:  # Print every 3 minutes
                    print(f"⏳ Cluster still {status}... (attempt {attempt+1}/60)")
            else:
                print(f"⚠️ Unexpected cluster status: {status}")
                
        except Exception as e:
            print(f"❌ Error checking cluster status: {e}")
            return None
            
        time.sleep(30)
=======
                print(f"✅ Redshift cluster ready: {cluster_endpoint}")
                
                # ALWAYS create bastion for private cluster
                print("Creating bastion host for private cluster...")
                instance_id = create_bastion_host()
                if instance_id:
                    print(f"✅ Bastion instance ready: {instance_id}")
                    
                    # Fix security groups before tunnel
                    try:
                        # Get cluster security groups
                        cluster_response = redshift.describe_clusters(ClusterIdentifier=cluster_id)
                        cluster = cluster_response['Clusters'][0]
                        vpc_sgs = cluster.get('VpcSecurityGroups', [])
                        
                        # Get bastion security group
                        bastion_response = ec2.describe_instances(
                            Filters=[
                                {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                                {'Name': 'instance-state-name', 'Values': ['running']}
                            ]
                        )
                        bastion_sg = bastion_response['Reservations'][0]['Instances'][0]['SecurityGroups'][0]['GroupId']
                        
                        # Add bastion access to Redshift security groups
                        for sg in vpc_sgs:
                            redshift_sg = sg['VpcSecurityGroupId']
                            try:
                                ec2.authorize_security_group_ingress(
                                    GroupId=redshift_sg,
                                    IpPermissions=[
                                        {
                                            'IpProtocol': 'tcp',
                                            'FromPort': 5439,
                                            'ToPort': 5439,
                                            'UserIdGroupPairs': [{'GroupId': bastion_sg}]
                                        }
                                    ]
                                )
                                print(f"✅ Added bastion access to Redshift SG: {redshift_sg}")
                            except Exception as e:
                                if 'already exists' in str(e):
                                    print(f"✅ Bastion access already exists for SG: {redshift_sg}")
                                else:
                                    print(f"⚠️ SG rule error: {e}")
                    except Exception as e:
                        print(f"⚠️ Security group setup error: {e}")
                    
                    if create_ssm_tunnel(instance_id, cluster_endpoint):
                        print("✅ SSM tunnel established")
                        
                        # Wait for download to complete
                        print("Waiting for data download to complete...")
                        download_thread.join(timeout=60)
                        
                        if download_result['path']:
                            os.environ['NORTHWIND_DATA_PATH'] = download_result['path']
                            print(f"Data ready at: {download_result['path']}")
                        
                        return 'localhost'  # Return localhost for tunnel
                    else:
                        print("❌ SSM tunnel failed")
                        return None
                else:
                    print("❌ Bastion creation failed")
                    return None
            time.sleep(30)
>>>>>>> 3f9252b (✅ Complete private Redshift setup with bastion host)
    
    print("❌ Cluster did not become available within 30 minutes")
    return None