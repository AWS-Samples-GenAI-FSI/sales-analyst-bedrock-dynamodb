import streamlit as st
import sqlite3
import pandas as pd
import os

st.title("Sales Data Analyst")
st.write("(Local SQLite - FAST)")

# Use bundled SQLite directly
db_path = "data/northwind.db"

if os.path.exists(db_path):
    st.success("✅ Database ready!")
    
    # Simple query interface
    query = st.text_input("Enter SQL query:", "SELECT * FROM customers LIMIT 5")
    
    if st.button("Run Query"):
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            st.dataframe(df)
        except Exception as e:
            st.error(f"Error: {e}")
else:
    st.error("Database not found")