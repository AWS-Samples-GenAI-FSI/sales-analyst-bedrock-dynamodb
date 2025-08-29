#!/usr/bin/env python3
"""
Test script for DynamoDB setup
"""
import os
from dotenv import load_dotenv
from src.utils.dynamodb_connector import get_available_tables, get_table_info
from src.utils.dynamodb_bootstrapper import check_northwind_exists, bootstrap_northwind

def main():
    # Load environment variables
    load_dotenv()
    
    print("🔍 Testing DynamoDB connection...")
    
    # Test connection
    try:
        tables = get_available_tables()
        print(f"✅ Connected to DynamoDB. Found {len(tables)} tables: {tables}")
    except Exception as e:
        print(f"❌ DynamoDB connection failed: {e}")
        return
    
    # Check if Northwind exists
    print("\n🔍 Checking Northwind tables...")
    if check_northwind_exists():
        print("✅ Northwind tables exist")
        
        # Show table info
        for table in ['customers', 'products', 'orders']:
            if table in tables:
                info = get_table_info(table)
                print(f"  - {table}: {info.get('item_count', 0)} items")
    else:
        print("❌ Northwind tables don't exist. Creating them...")
        success = bootstrap_northwind(show_progress=False)
        if success:
            print("✅ Northwind tables created successfully")
        else:
            print("❌ Failed to create Northwind tables")
    
    print("\n🎉 DynamoDB setup test complete!")

if __name__ == "__main__":
    main()