"""
S3 data manager for faster Northwind data distribution.
"""
import boto3
import os
import tempfile
import requests
from botocore.exceptions import ClientError

def upload_northwind_to_s3():
    """Upload Northwind data to S3 for faster distribution."""
    s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    bucket_name = 'sales-analyst-northwind-data'
    
    try:
        # Create bucket if it doesn't exist
        try:
            s3.head_bucket(Bucket=bucket_name)
        except ClientError:
            s3.create_bucket(Bucket=bucket_name)
            print(f"Created S3 bucket: {bucket_name}")
        
        # Download Northwind data
        temp_dir = tempfile.mkdtemp()
        sqlite_path = os.path.join(temp_dir, "northwind.db")
        
        # Try multiple URLs
        urls = [
            "https://github.com/jpwhite3/northwind-SQLite3/raw/master/northwind.db",
            "https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/master/northwind.db"
        ]
        
        downloaded = False
        for url in urls:
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    with open(sqlite_path, 'wb') as f:
                        f.write(response.content)
                    downloaded = True
                    print(f"Downloaded from: {url}")
                    break
            except:
                continue
        
        if not downloaded:
            print("Failed to download from all URLs, creating sample data")
            from .northwind_bootstrapper import create_sample_northwind_data
            create_sample_northwind_data(sqlite_path)
        
        # Upload to S3 (private access)
        s3.upload_file(sqlite_path, bucket_name, 'northwind.db')
        print(f"Uploaded northwind.db to s3://{bucket_name}/northwind.db")
        
        return f"https://{bucket_name}.s3.amazonaws.com/northwind.db"
        
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return None

def download_northwind_from_s3():
    """Download Northwind data from S3 using AWS credentials."""
    bucket_name = 'sales-analyst-northwind-data'
    
    try:
        s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        temp_dir = tempfile.mkdtemp()
        sqlite_path = os.path.join(temp_dir, "northwind.db")
        
        # Download using AWS SDK (requires credentials)
        s3.download_file(bucket_name, 'northwind.db', sqlite_path)
        print(f"Downloaded Northwind data from S3")
        return sqlite_path
            
    except Exception as e:
        print(f"Error downloading from S3: {e}")
        return None