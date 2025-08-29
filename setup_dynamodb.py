#!/usr/bin/env python3
"""
Setup script for DynamoDB version of Sales Analyst
"""
import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Check if environment is properly configured."""
    load_dotenv()
    
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease update your .env file with the required AWS credentials.")
        return False
    
    print("✅ Environment variables configured")
    return True

def test_aws_connection():
    """Test AWS connection."""
    try:
        import boto3
        
        # Test DynamoDB connection
        dynamodb = boto3.client('dynamodb', region_name=os.getenv('AWS_REGION'))
        dynamodb.list_tables()
        print("✅ AWS DynamoDB connection successful")
        return True
        
    except Exception as e:
        print(f"❌ AWS connection failed: {e}")
        return False

def setup_tables():
    """Setup DynamoDB tables."""
    try:
        from src.utils.dynamodb_bootstrapper import bootstrap_northwind
        
        print("🔄 Setting up Northwind tables in DynamoDB...")
        success = bootstrap_northwind(show_progress=False)
        
        if success:
            print("✅ Northwind tables created successfully")
            return True
        else:
            print("❌ Failed to create Northwind tables")
            return False
            
    except Exception as e:
        print(f"❌ Table setup failed: {e}")
        return False

def main():
    print("🚀 Setting up Sales Analyst with DynamoDB...")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test AWS connection
    if not test_aws_connection():
        sys.exit(1)
    
    # Setup tables
    if not setup_tables():
        sys.exit(1)
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Run: streamlit run app.py")
    print("2. Ask questions like: 'What are the top customers by order value?'")
    print("\nTo clean up later, run: python cleanup.py")

if __name__ == "__main__":
    main()