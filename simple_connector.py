"""Simple Redshift connector that just works."""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    """Get direct connection to Redshift."""
    return psycopg2.connect(
        host='sales-analyst-08221713.cbasetcizzff.us-east-1.redshift.amazonaws.com',
        port=5439,
        database='sales_analyst',
        user='admin',
        password='Awsuser123$',
        connect_timeout=10
    )

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("✅ Connection works!")
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")