"""
Local SQLite connector for fast development.
"""
import sqlite3
import os
import pandas as pd

def get_local_connection():
    """
    Get connection to local SQLite database.
    
    Returns:
        sqlite3.Connection: Database connection
    """
    db_path = os.getenv('LOCAL_DB_PATH', 'local_northwind.db')
    return sqlite3.connect(db_path)

def execute_local_query(query):
    """
    Execute query on local SQLite database.
    
    Args:
        query (str): SQL query to execute
        
    Returns:
        list: Query results as list of dictionaries
    """
    try:
        conn = get_local_connection()
        
        # Convert to pandas for consistent output format
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert to list of dictionaries (same format as Redshift connector)
        return df.to_dict('records')
        
    except Exception as e:
        print(f"Local query error: {e}")
        return []

def check_local_northwind_exists():
    """
    Check if local Northwind database exists and has data.
    
    Returns:
        bool: True if database exists with data
    """
    try:
        conn = get_local_connection()
        cursor = conn.cursor()
        
        # Check if customers table exists and has data
        cursor.execute("SELECT COUNT(*) FROM customers")
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
        
    except Exception:
        return False