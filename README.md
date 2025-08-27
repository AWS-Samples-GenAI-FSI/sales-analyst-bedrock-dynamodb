# GenAI Sales Analyst
*(Powered by Amazon Bedrock and Amazon Redshift)*

A Streamlit application that uses Amazon Bedrock, LangGraph, and FAISS to analyze sales data using natural language queries.

## Step-by-Step Setup Guide

### Prerequisites
- AWS Account (if you don't have one, [create here](https://aws.amazon.com/free/))
- Python 3.8+ installed on your computer
- AWS Session Manager plugin (will be installed automatically, or see troubleshooting if it fails)
- Basic command line knowledge

### Step 1: Create AWS User with Required Permissions

1. **Login to AWS Console:**
   - Go to [AWS Console](https://console.aws.amazon.com/)
   - Sign in with your AWS account

2. **Create IAM User:**
   - Navigate to [IAM Console](https://console.aws.amazon.com/iam/)
   - Click "Users" → "Create user"
   - Enter username (e.g., `sales-analyst-user`)
   - Select "Programmatic access"

3. **Attach Required Policies:**
   - Click "Attach policies directly"
   - Search and select these policies:
     - `AmazonRedshiftFullAccess`
     - `AmazonEC2FullAccess` 
     - `IAMFullAccess`
     - `AmazonSSMFullAccess`
     - `AmazonBedrockFullAccess`
   - Click "Next" → "Create user"

4. **Get Your Credentials:**
   - After user creation, click "Create access key"
   - Choose "Application running outside AWS"
   - Copy your **Access Key ID** and **Secret Access Key**
   - ⚠️ **Save these safely - you won't see the secret key again!**

### Step 2: Download and Setup the Application

1. **Install Git (if missing):**
   ```bash
   # Amazon Linux / CentOS / RHEL:
   sudo yum install -y git
   
   # Ubuntu / Debian:
   sudo apt-get install -y git
   
   # Mac/Windows: Git is usually pre-installed
   ```

2. **Clone the Repository:**
   ```bash
   git clone https://github.com/AWS-Samples-GenAI-FSI/sales-analyst-bedrock-redshift.git
   cd sales-analyst-bedrock-redshift
   ```

3. **Install Dependencies (Auto-Detection)::**
   ```bash
   python3 setup.py
   ```
   
   This automatically detects your platform and installs the right dependencies:
   - **Amazon Linux 2023**: Installs SQLite libraries + FAISS fixes
   - **Ubuntu**: Installs build tools + dependencies  
   - **Mac/Windows**: Uses standard pip install

### Step 3: Configure Your AWS Credentials

**Open the `.env` file** in any text editor and **replace the placeholders** with your actual AWS credentials:
```bash
# Replace these with your actual values from Step 1
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA... # Your actual Access Key ID
AWS_SECRET_ACCESS_KEY=... # Your actual Secret Access Key
```

**Save the file**

### Step 4: Run the Application

1. **Start the app:**
   ```bash
   streamlit run app.py
   ```

2. **Wait for automatic setup** (first run takes 5-10 minutes):
   - ✅ Creates **private** Redshift cluster (secure, no public access)
   - ✅ Sets up EC2 bastion host with SSM tunnel
   - ✅ Downloads Northwind sample data
   - ✅ Loads data into Redshift
   - ✅ Configures AI components

3. **Open your browser** to the URL shown (usually `http://localhost:8501`)

### Step 5: Start Analyzing Your Data!

Once setup is complete, you can ask questions like:

**Sample Questions:**
- "What are the top 5 customers by order value?"
- "Count the number of orders by country"
- "What's the average order value by customer?"
- "Which products are most popular?"
- "Show me sales trends by month"

## What You Get

- 🤖 **Natural Language Queries:** Ask questions in plain English
- 📊 **Complete Sample Dataset:** 91 customers, 830 orders, 2155 order details
- 🔄 **Automatic Setup:** No manual database configuration needed
- 📈 **AI-Powered Analysis:** Get insights and explanations
- 🚀 **Fast Performance:** Optimized for quick responses

## Important Notes

### AWS Costs
- **Redshift cluster:** ~$0.25/hour
- **EC2 bastion:** ~$0.01/hour
- **Total:** ~$0.26/hour
- ⚠️ **Remember to run cleanup when done!**

### Security
- **Private Redshift cluster** - No public internet access
- **SSM tunnel** - Secure connection through AWS Session Manager
- Never commit your `.env` file with real credentials to git
- Your AWS credentials stay on your local machine
- All AWS resources are created in your own account

## Cleanup (Important!)

**When you're done, always run cleanup to avoid charges:**
```bash
python cleanup.py
```

This removes:
- ✅ Redshift cluster
- ✅ EC2 instances
- ✅ IAM roles
- ✅ All AWS resources

## Troubleshooting

### Common Issues

**"Permission denied" errors:**
- Verify your IAM user has all required policies attached
- Check your Access Key ID and Secret Access Key are correct

**"Setup fails" or timeouts:**
- Run `python cleanup.py` first
- Try a different AWS region in `.env` (us-west-2, eu-west-1)
- Ensure you have sufficient AWS service limits
- Wait for bastion host SSM agent to come online (can take 2-3 minutes)

**"Credentials not found":**
- Make sure you copied `.env.example` to `.env`: `cp .env.example .env`
- Make sure `.env` file is in the same directory as `app.py`
- Verify no extra spaces in your credential values
- Check that you saved the `.env` file after editing

**App won't start:**
- Ensure Python 3.8+ is installed: `python --version`
- Install requirements: `pip install -r requirements.txt`
- Try: `python -m streamlit run app.py`

**"Connection failed" or "SSM tunnel failed":**
- The app uses a private Redshift cluster with bastion host for security
- Connection goes through localhost:5439 via SSM tunnel
- If connection fails, wait 2-3 minutes for SSM agent to initialize

**Session Manager plugin installation:**
- **For macOS users:**
  ```bash
  curl 'https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip' -o 'sessionmanager-bundle.zip'
  unzip sessionmanager-bundle.zip
  sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin
  ```
- **For Windows users:**
  - Download: https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe
  - Run the installer as Administrator
- **For Linux users:**
  ```bash
  curl 'https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb' -o 'session-manager-plugin.deb'
  sudo dpkg -i session-manager-plugin.deb
  ```

### Getting Help
- Check AWS CloudFormation console for detailed error messages
- Review AWS costs in Billing console
- Ensure your AWS account has no service limits blocking resource creation

## Architecture

**Built with:**
- **Amazon Bedrock:** AI/ML models for natural language processing
- **Amazon Redshift:** Private data warehouse for fast analytics
- **EC2 + SSM:** Bastion host with Session Manager tunnel
- **FAISS:** Vector database for semantic search
- **Streamlit:** Web interface
- **LangGraph:** Workflow orchestration

**Security Architecture:**
```
Your Computer → SSM Tunnel → EC2 Bastion → Private Redshift Cluster
(localhost:5439)    (AWS Session Manager)    (No public access)
```

---

**Need help?** Open an issue on GitHub or check the troubleshooting section above.