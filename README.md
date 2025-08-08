# GenAI Sales Analyst
*(Powered by Amazon Bedrock and Amazon Redshift)*

A Streamlit application that uses Amazon Bedrock, LangGraph, and FAISS to analyze sales data using natural language queries.

## Quick Start for Colleagues

### Prerequisites
- AWS Account with programmatic access
- Python 3.8+ installed
- AWS CLI configured (`aws configure`)

### Setup (5 minutes)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure AWS credentials:**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials
   ```

3. **Run the app:**
   ```bash
   streamlit run app.py
   ```

### What happens automatically:
- ✅ Creates Redshift cluster in your AWS account
- ✅ Sets up EC2 bastion host with SSM tunnel  
- ✅ Downloads complete Northwind dataset from GitHub
- ✅ Loads data into Redshift with proper relationships
- ✅ Configures AI workflow and vector store
- ✅ Ready to query with natural language!

### Sample Questions:
- "What are the top 5 customers by order value?"
- "Count the number of orders by country"
- "What's the average order value by customer?"
- "Which products are most popular?"
- "Show me sales trends by month"

### Features:
- 🤖 Natural language to SQL conversion
- 📊 Complete Northwind dataset (91 customers, 830 orders, 2155 order details)
- 🔄 Automatic infrastructure setup
- 📈 Rich data analysis and insights
- 🚀 Fast queries after initial setup

### Cleanup:
When done, remove AWS resources:
```bash
python cleanup.py
```

### Estimated AWS Costs:
- Redshift cluster: ~$0.25/hour
- EC2 bastion: ~$0.01/hour
- **Total: ~$0.26/hour** (remember to cleanup!)

### Troubleshooting:
- If setup fails, run `python cleanup.py` and try again
- Ensure AWS credentials have proper permissions
- Check AWS region is set correctly in `.env`

---
**Built with:** Amazon Bedrock • Amazon Redshift • LangGraph • Streamlit