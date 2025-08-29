# GenAI Sales Analyst with Amazon DynamoDB
*(Powered by Amazon Bedrock and Amazon DynamoDB)*

A Streamlit application that uses Amazon Bedrock, LangGraph, and FAISS to analyze sales data using natural language queries with Amazon DynamoDB as the backend database.

## Architecture

This application demonstrates a modern serverless analytics architecture:

- **Amazon Bedrock**: AI/ML models for natural language processing and query generation
- **Amazon DynamoDB**: NoSQL database for fast, scalable data storage
- **FAISS**: Vector database for semantic search and metadata management
- **Streamlit**: Interactive web interface
- **LangGraph**: Workflow orchestration for complex analysis tasks

## Features

- 🤖 **Natural Language Queries**: Ask questions in plain English
- 📊 **Complete Sample Dataset**: Full Northwind database with 91 customers, 830+ orders
- 🔄 **Automatic Setup**: No manual database configuration needed
- 📈 **AI-Powered Analysis**: Get insights and explanations with client-side aggregation
- 🚀 **Fast Performance**: Sub-second query execution with DynamoDB
- 🏗️ **Serverless Architecture**: No infrastructure management required

## Quick Start

### Prerequisites
- AWS Account ([create here](https://aws.amazon.com/free/) if needed)
- Python 3.8+ installed
- Basic command line knowledge

### Step 1: Clone Repository
```bash
git clone https://github.com/AWS-Samples-GenAI-FSI/sales-analyst-bedrock-dynamodb.git
cd sales-analyst-bedrock-dynamodb
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure AWS Credentials

Create a `.env` file from the example:
```bash
cp .env.example .env
```

Edit `.env` with your AWS credentials:
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

### Step 4: Run the Application
```bash
streamlit run app.py
```

The application will automatically:
- Download the complete Northwind dataset from GitHub
- Create DynamoDB tables with proper schema
- Denormalize data for optimal NoSQL performance
- Set up AI components and vector store

### Step 5: Start Analyzing!

Open your browser to `http://localhost:8501` and ask questions like:

- "What are the top 10 customers by total order value?"
- "Which products generate the most revenue?"
- "What's the average order value by country?"
- "Which product categories sell the most?"

## Data Model

The application uses a **denormalized single-table design** optimized for DynamoDB:

### Source Tables (Normalized Northwind)
- `northwind_customers` - Customer information
- `northwind_products` - Product catalog
- `northwind_orders` - Order headers
- `northwind_order_details` - Order line items
- `northwind_categories` - Product categories
- `northwind_suppliers` - Supplier information
- `northwind_employees` - Employee data
- `northwind_shippers` - Shipping companies

### Analytics Table (Denormalized)
- `sales_transactions` - Flattened transaction data combining all related information

This design trades storage space for query performance, eliminating the need for complex JOINs.

## AWS Costs

DynamoDB pricing is based on usage:
- **On-Demand**: Pay per request (~$0.25 per million reads)
- **Provisioned**: Fixed capacity pricing
- **Storage**: ~$0.25 per GB per month

Typical costs for this demo: **< $1/month** for light usage.

## Architecture Benefits

### vs. Traditional SQL Databases
- ✅ **No server management**: Fully serverless
- ✅ **Instant scaling**: Handles any load automatically  
- ✅ **Fast queries**: Single-digit millisecond latency
- ✅ **Cost effective**: Pay only for what you use

### vs. Data Warehouses
- ✅ **No cluster provisioning**: No waiting for infrastructure
- ✅ **Real-time data**: No ETL delays
- ✅ **Simple operations**: No complex maintenance

## Sample Questions

The application can answer various business intelligence questions:

**Customer Analysis:**
- "Who are our top customers by revenue?"
- "Which countries generate the most sales?"
- "What's the customer distribution by city?"

**Product Analysis:**
- "Which products are most profitable?"
- "What are our best-selling categories?"
- "Which suppliers provide the most revenue?"

**Sales Analysis:**
- "What are our monthly sales trends?"
- "Which employees process the most orders?"
- "What's the average order value by region?"

## Development

### Project Structure
```
├── src/
│   ├── bedrock/          # Amazon Bedrock integration
│   ├── models/           # Query generation models
│   ├── utils/            # DynamoDB utilities and data loading
│   ├── vector_store/     # FAISS vector store management
│   └── graph/            # LangGraph workflow definitions
├── app.py                # Main Streamlit application
├── cleanup.py            # Resource cleanup utility
└── requirements.txt      # Python dependencies
```

### Key Components

- **DynamoDB Connector**: Handles all database operations
- **NoSQL Query Generator**: Converts natural language to DynamoDB queries
- **Data Bootstrapper**: Loads and denormalizes Northwind data
- **Analysis Workflow**: Orchestrates query execution and result processing

## Cleanup

When finished, clean up AWS resources:
```bash
python cleanup.py
```

This removes all DynamoDB tables created by the application.

## Troubleshooting

### Common Issues

**"Permission denied" errors:**
- Verify IAM user has DynamoDB permissions
- Check AWS credentials in `.env` file

**"No data found":**
- Wait for initial data loading to complete
- Check DynamoDB tables exist in AWS Console

**"Import errors":**
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Verify Python 3.8+ is being used

### Required IAM Permissions

Your AWS user needs these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:*",
                "bedrock:*"
            ],
            "Resource": "*"
        }
    ]
}
```

## Contributing

This is an AWS sample project. Please see [CONTRIBUTING](CONTRIBUTING.md) for details on submitting pull requests.

## Security

See [SECURITY](SECURITY.md) for security considerations and reporting vulnerabilities.

## License

This project is licensed under the Apache-2.0 License. See [LICENSE](LICENSE) file for details.

---

**AWS Samples** | **Amazon Bedrock** | **Amazon DynamoDB** | **Generative AI**