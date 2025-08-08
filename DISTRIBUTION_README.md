# GenAI Sales Analyst - Quick Setup

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
