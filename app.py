"""
GenAI Sales Analyst - Main application file.
"""
import streamlit as st
import pandas as pd
import time
import os
import pickle
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import components
from src.bedrock.bedrock_helper import BedrockHelper
from src.vector_store.faiss_manager import FAISSManager

from src.graph.workflow import AnalysisWorkflow
from src.utils.redshift_connector import (
    get_redshift_connection, 
    execute_query,
    get_available_databases,
    get_available_schemas,
    get_available_tables,
    get_table_columns
)
from src.utils.northwind_bootstrapper import bootstrap_northwind, check_northwind_exists

def initialize_components():
    """
    Initialize application components.
    
    Returns:
        Dictionary of initialized components
    """
    # Get environment variables
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    s3_bucket = os.getenv('S3_BUCKET', 'your-bucket-name')
    
    # Initialize Bedrock client
    bedrock = BedrockHelper(region_name=aws_region)
    
    # Initialize vector store
    vector_store = FAISSManager(
        bedrock_client=bedrock,
        s3_bucket=s3_bucket
    )
    
    # No monitoring
    monitor = None
    
    # Initialize workflow
    workflow = AnalysisWorkflow(
        bedrock_helper=bedrock,
        vector_store=vector_store,
        monitor=monitor
    )
    
    return {
        'bedrock': bedrock,
        'vector_store': vector_store,
        'monitor': monitor,
        'workflow': workflow
    }


def load_all_metadata(vector_store, show_progress=False):
    """
    Load metadata from Northwind tables.
    """
    # Create simple schema context for Northwind
    schema_text = """
    Database: sales_analyst, Schema: northwind
    
    Table: customers - Customer information
    Columns: customerid (text), companyname (text), contactname (text), country (text)
    
    Table: orders - Order information  
    Columns: orderid (integer), customerid (text), orderdate (text), freight (real), shipcountry (text)
    
    Table: order_details - Order line items
    Columns: orderid (integer), productid (integer), unitprice (real), quantity (integer)
    
    Table: products - Product catalog
    Columns: productid (integer), productname (text), categoryid (integer), unitprice (real)
    
    Table: categories - Product categories
    Columns: categoryid (integer), categoryname (text), description (text)
    
    Table: suppliers - Supplier information
    Columns: supplierid (integer), companyname (text), country (text)
    
    Table: employees - Employee data
    Columns: employeeid (integer), lastname (text), firstname (text), title (text)
    
    Table: shippers - Shipping companies
    Columns: shipperid (integer), companyname (text), phone (text)
    """
    
    # Add to vector store
    texts = [schema_text]
    metadatas = [{'database': 'sales_analyst', 'schema': 'northwind', 'type': 'schema'}]
    
    # Get embeddings
    embeddings = []
    for text in texts:
        embedding = vector_store.bedrock_client.get_embeddings(text)
        embeddings.append(embedding)
    
    if embeddings:
        embeddings_array = np.array(embeddings).astype('float32')
        if embeddings_array.ndim == 1:
            embeddings_array = embeddings_array.reshape(1, -1)
        
        vector_store.texts = texts
        vector_store.metadata = metadatas
        vector_store.index.add(embeddings_array)
        
        if show_progress:
            st.sidebar.success(f"✅ Loaded Northwind schema metadata")
        
        # Return dummy dataframe
        import pandas as pd
        return pd.DataFrame({'schema': ['northwind'], 'loaded': [True]})
    
    return None


def main():
    """
    Main application function.
    """
    # Set page config
    st.set_page_config(
        page_title="Sales Data Analyst",
        page_icon="📊",
        layout="wide"
    )
    
    # Hide Streamlit branding
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Custom CSS for other elements
    st.markdown("""
    <style>
    .subheader {
        font-size: 1.8rem;
        font-weight: 600;
        color: #444;
        margin-bottom: 1rem;
    }
    .info-text {
        font-size: 1.1rem;
        color: #666;
    }
    .stProgress > div > div > div > div {
        background-color: #0066cc;
    }
    .workflow-step {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .workflow-step-completed {
        background-color: #e6f3ff;
        border-left: 4px solid #0066cc;
    }
    .workflow-step-error {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }
    .data-section {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with direct HTML and inline styles
    st.markdown('<h1 style="font-size: 50px; font-weight: 900; color: #0066cc; text-align: left; margin-bottom: 5px; line-height: 1.0;">Sales Data Analyst</h1>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 14px; color: #0066cc; margin-top: -5px; margin-bottom: 15px; text-align: left;">(Powered by Amazon Bedrock and Amazon Redshift)</p>', unsafe_allow_html=True)
    st.markdown('<div style="border-bottom: 4px double #0066cc; margin-bottom: 30px;"></div>', unsafe_allow_html=True)
    
    # Initialize components
    components = initialize_components()
    
    # Auto-create Redshift cluster and test connection
    try:
        from src.utils.redshift_cluster_manager import create_redshift_cluster
        
        # Create cluster if needed
        with st.spinner("Setting up Redshift cluster..."):
            endpoint = create_redshift_cluster()
            if endpoint:
                os.environ['REDSHIFT_HOST'] = endpoint
                st.sidebar.success(f"✅ Redshift cluster ready: {endpoint}")
            
        conn = get_redshift_connection()
        st.sidebar.success("✅ Connected to Redshift")
        conn.close()
        
        # Auto-create Northwind database if it doesn't exist
        if not check_northwind_exists():
            st.sidebar.info("🔄 Setting up Northwind database...")
            with st.spinner("Creating Northwind database with complete dataset..."):
                success = bootstrap_northwind(show_progress=True)
                if success:
                    st.sidebar.success("✅ Northwind database created successfully!")
                    # Force metadata reload after database creation
                    st.session_state.metadata_loaded = False
                else:
                    st.sidebar.error("❌ Failed to create Northwind database")
                    return
        else:
            st.sidebar.success("✅ Northwind database ready")
            
        # Test database connection only once
        if 'database_tested' not in st.session_state:
            try:
                customer_result = execute_query("SELECT COUNT(*) FROM northwind.customers")
                order_result = execute_query("SELECT COUNT(*) FROM northwind.orders")
                
                if customer_result and order_result:
                    customers = customer_result[0]['count']
                    orders = order_result[0]['count']
                    st.sidebar.success(f"✅ Database has {customers} customers, {orders} orders")
                    st.session_state.database_tested = True
                    
                    if orders == 0:
                        st.sidebar.warning("⚠️ No orders found - forcing database recreation")
                        success = bootstrap_northwind(show_progress=True)
                        if success:
                            st.sidebar.success("✅ Database recreated with sample data")
                            st.session_state.metadata_loaded = False
                else:
                    st.sidebar.warning("⚠️ Database tables may be empty")
            except Exception as e:
                st.sidebar.error(f"❌ Database test failed: {str(e)}")
                return
        else:
            st.sidebar.success("✅ Database ready")
            
    except Exception as e:
        st.sidebar.error(f"❌ Redshift connection failed: {str(e)}")
        return
    
    # Load metadata on startup if not already loaded (runs only once)
    if 'metadata_loaded' not in st.session_state or not st.session_state.metadata_loaded:
        try:
            metadata_df = load_all_metadata(components['vector_store'], show_progress=True)
            if metadata_df is not None and len(metadata_df) > 0:
                st.session_state.metadata_df = metadata_df
                st.session_state.metadata_loaded = True
                st.session_state.metadata_count = len(metadata_df)
                st.sidebar.success(f"✅ Loaded metadata for {len(metadata_df)} columns")
            else:
                st.sidebar.warning("⚠️ No metadata loaded - database may still be setting up")
                st.session_state.metadata_loaded = False
        except Exception as e:
            st.sidebar.error(f"❌ Error loading metadata: {str(e)}")
            st.session_state.metadata_loaded = False
    else:
        st.sidebar.success("✅ Metadata ready")
    
    # Sidebar
    with st.sidebar:
        st.header("Settings")
        

        
        # Workflow status
        if components['workflow']:
            st.success("✅ Analysis workflow enabled")
        
        # Reload metadata button
        if st.button("🔄 Reload Metadata", key="reload_metadata"):
            with st.spinner("Reloading database metadata..."):
                st.session_state.metadata_loaded = False
                metadata_df = load_all_metadata(components['vector_store'], show_progress=True)
                if metadata_df is not None and len(metadata_df) > 0:
                    st.session_state.metadata_df = metadata_df
                    st.session_state.metadata_loaded = True
                    st.session_state.metadata_count = len(metadata_df)
                    st.success(f"✅ Reloaded metadata for {len(metadata_df)} columns")
                    st.rerun()
                else:
                    st.error("❌ Failed to reload metadata")
        
        # Available data section moved to sidebar
        st.header("Available Data")
        st.markdown("""
        - Customer information (CUSTOMERS)
        - Order information (ORDERS)
        - Order details (ORDER_DETAILS)
        - Product information (PRODUCTS)
        - Categories (CATEGORIES)
        - Supplier information (SUPPLIERS)
        - Employee data (EMPLOYEES)
        - Shipping companies (SHIPPERS)
        """)
        
        # Show available databases and schemas
        with st.expander("Database Explorer", expanded=False):
            if st.button("Show Databases"):
                try:
                    databases = get_available_databases()
                    st.write("Available databases:")
                    st.write(", ".join(databases))
                except Exception as e:
                    st.error(f"Error listing databases: {str(e)}")
    
    # Main content area - use full width for col1
    col1 = st.container()
    
    with col1:
        st.markdown('<p class="subheader">Ask questions about your sales data</p>', unsafe_allow_html=True)
        st.markdown('<p class="info-text">You can ask about customer orders, product sales, and more.</p>', unsafe_allow_html=True)
        
        # Examples
        with st.expander("Example questions", expanded=False):
            st.markdown("""
            - What are the top 5 customers by order value?
            - Show me the schema of the CUSTOMERS table
            - Count the number of orders by country
            - What's the average order value by customer?
            - Which products are most popular?
            """)
        
        # Question input
        question = st.text_input(
            "Ask your question:",
            placeholder="e.g., What are the top 5 customers by order value?"
        )
    
    # Process question
    if question:
        if 'metadata_df' not in st.session_state or not st.session_state.get('metadata_loaded', False):
            st.error("Metadata not loaded. Please click 'Reload Metadata' button in the sidebar.")
            return
        
        try:
            # Execute workflow
            with st.spinner("Processing your question..."):
                result = components['workflow'].execute(question, execute_query)
            
            # Display workflow steps
            with st.expander("Workflow Steps", expanded=False):
                steps = result.get("steps_completed", [])
                for step in steps:
                    if "error" in step:
                        st.markdown(f'<div class="workflow-step workflow-step-error">{step}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="workflow-step workflow-step-completed">{step}</div>', unsafe_allow_html=True)
            
            # Display error if any
            if "error" in result:
                st.error(result.get("friendly_error", result["error"]))
            
            # Display SQL if generated
            if "generated_sql" in result:
                with st.expander("Generated SQL", expanded=True):
                    st.code(result["generated_sql"], language="sql")
            
            # Display results if available
            if "query_results" in result:
                st.write(f"Query executed in {result.get('execution_time', 0):.2f} seconds, returned {len(result['query_results'])} rows")
                with st.expander("Query Results", expanded=True):
                    st.dataframe(result["query_results"])
            
            # Display analysis
            if "analysis" in result:
                st.subheader("Analysis")
                st.write(result["analysis"])
            
            # Save to history
            if 'history' not in st.session_state:
                st.session_state.history = []
            
            st.session_state.history.append({
                'question': question,
                'sql': result.get('generated_sql', ''),
                'results': result.get('query_results', [])[:10],  # Store only first 10 rows
                'analysis': result.get('analysis', ''),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    # Show history
    if 'history' in st.session_state and st.session_state.history:
        with st.expander("Query History", expanded=False):
            for i, item in enumerate(reversed(st.session_state.history[-5:])):  # Show last 5 queries
                st.write(f"**{item['timestamp']}**: {item['question']}")
                if st.button(f"Show details", key=f"history_{i}"):
                    st.code(item['sql'], language="sql")
                    st.dataframe(item['results'])
                    st.write(item['analysis'])
                st.divider()


if __name__ == "__main__":
    main()