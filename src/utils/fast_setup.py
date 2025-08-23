"""
Fast setup using local SQLite - no AWS resources needed for development.
"""
import os
import sqlite3
import shutil
from pathlib import Path

def setup_local_database():
    """
    Setup local SQLite database instantly - no AWS needed.
    
    Returns:
        str: Path to local database
    """
    try:
        # Use bundled SQLite file
        bundled_path = Path(__file__).parent.parent.parent / 'data' / 'northwind.db'
        
        if bundled_path.exists():
            # Copy to local working directory
            local_path = Path('local_northwind.db')
            shutil.copy2(bundled_path, local_path)
            
            # Verify it works
            conn = sqlite3.connect(local_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM customers")
            count = cursor.fetchone()[0]
            conn.close()
            
            print(f"✅ Local database ready with {count} customers")
            return str(local_path)
        else:
            print("❌ Bundled database not found")
            return None
            
    except Exception as e:
        print(f"Error setting up local database: {e}")
        return None

def get_connection_mode():
    """
    Determine connection mode based on environment.
    
    Returns:
        str: 'local' or 'redshift'
    """
    # Check if user wants Redshift specifically
    use_redshift = os.getenv('USE_REDSHIFT', 'false').lower() == 'true'
    
    if use_redshift:
        return 'redshift'
    else:
        return 'local'

def is_redshift_available():
    """
    Quick check if Redshift is available without creating it.
    
    Returns:
        bool: True if Redshift is ready
    """
    try:
        from .redshift_connector import get_redshift_connection
        conn = get_redshift_connection()
        conn.close()
        return True
    except:
        return False