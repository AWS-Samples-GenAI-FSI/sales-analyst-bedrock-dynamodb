#!/usr/bin/env python3
"""
Setup script for distributing the sales analyst app.
Run this once to prepare the app for distribution to friends.
"""
import boto3
import os
from dotenv import load_dotenv
from src.utils.s3_data_manager import upload_northwind_to_s3

load_dotenv()

def setup_s3_data():
    """Upload Northwind data to S3 for faster distribution."""
    print("📦 Setting up S3 data distribution...")
    s3_url = upload_northwind_to_s3()
    if s3_url:
        print(f"✅ Northwind data available at: {s3_url}")
        return True
    else:
        print("❌ Failed to setup S3 data distribution")
        return False

def create_distribution_readme():
    """Create README for distribution."""
    readme_content = """# GenAI Sales Analyst - Quick Setup

## Prerequisites
1. AWS Account with programmatic access
2. Python 3.8+ installed
3. AWS CLI configured (`aws configure`)

## Quick Start
1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   Copy `.env.example` to `.env` and update:
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials and region
   ```

3. **Run the app:**
   ```bash
   streamlit run app.py
   ```

## What happens automatically:
- ✅ Creates Redshift cluster in your AWS account
- ✅ Sets up EC2 bastion host with SSM tunnel
- ✅ Downloads and loads Northwind sample database
- ✅ Configures vector store and AI workflow
- ✅ Ready to query with natural language!

## Sample Questions:
- "What are the top 5 customers by order value?"
- "Count the number of orders by country"
- "Which products are most popular?"

## Cleanup:
When done, run cleanup to remove AWS resources:
```bash
python cleanup.py
```

## Estimated AWS Costs:
- Redshift cluster: ~$0.25/hour
- EC2 bastion: ~$0.01/hour
- Total: ~$0.26/hour (remember to cleanup!)
"""
    
    with open('DISTRIBUTION_README.md', 'w') as f:
        f.write(readme_content)
    print("✅ Created DISTRIBUTION_README.md")

def create_env_example():
    """Create .env.example file."""
    env_example = """# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Redshift Configuration
REDSHIFT_HOST=localhost
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=sales_analyst
REDSHIFT_USER=admin
REDSHIFT_PASSWORD=Awsuser123$

# Optional: LangFuse Monitoring
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=

# Optional: S3 Bucket for caching
S3_BUCKET=your-bucket-name
"""
    
    with open('.env.example', 'w') as f:
        f.write(env_example)
    print("✅ Created .env.example")

def main():
    print("🚀 Setting up Sales Analyst app for distribution...")
    
    # Setup S3 data distribution
    setup_s3_data()
    
    # Create distribution files
    create_distribution_readme()
    create_env_example()
    
    print("\n✅ Distribution setup complete!")
    print("\n📋 Next steps:")
    print("1. Test the app locally: streamlit run app.py")
    print("2. Share the entire folder with your friends")
    print("3. They just need to follow DISTRIBUTION_README.md")
    print("\n💡 The app will automatically set up all AWS infrastructure!")

if __name__ == "__main__":
    main()