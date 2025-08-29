# Deployment Guide

This guide covers different deployment options for the GenAI Sales Analyst application.

## Local Development

### Quick Start
```bash
# Clone repository
git clone https://github.com/AWS-Samples-GenAI-FSI/sales-analyst-bedrock-dynamodb.git
cd sales-analyst-bedrock-dynamodb

# Run setup script
python setup.py

# Configure AWS credentials in .env file
# Then start the application
streamlit run app.py
```

### Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your AWS credentials
# Start application
streamlit run app.py
```

## AWS Deployment Options

### Option 1: Amazon EC2

Deploy on EC2 for persistent hosting:

```bash
# Launch EC2 instance (Amazon Linux 2023 recommended)
# Install Python 3.8+
sudo yum update -y
sudo yum install -y python3 python3-pip git

# Clone and setup
git clone https://github.com/AWS-Samples-GenAI-FSI/sales-analyst-bedrock-dynamodb.git
cd sales-analyst-bedrock-dynamodb
python3 setup.py

# Configure environment
# Use IAM roles instead of access keys when possible

# Run with public access (configure security groups appropriately)
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

### Option 2: AWS App Runner

Deploy using AWS App Runner for serverless hosting:

1. Create `apprunner.yaml`:
```yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  runtime-version: 3.8
  command: streamlit run app.py --server.address 0.0.0.0 --server.port 8501
  network:
    port: 8501
    env: PORT
  env:
    - name: AWS_REGION
      value: us-east-1
```

2. Deploy via AWS Console or CLI

### Option 3: Amazon ECS/Fargate

Deploy using containers:

1. Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
```

2. Build and deploy to ECS

## Security Considerations

### IAM Permissions

Minimum required permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DeleteTable",
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
                "dynamodb:PutItem",
                "dynamodb:BatchWriteItem",
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/northwind_*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DeleteTable",
                "dynamodb:DescribeTable",
                "dynamodb:PutItem",
                "dynamodb:BatchWriteItem",
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/sales_transactions"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        }
    ]
}
```

### Network Security

- Use VPC endpoints for DynamoDB access
- Implement proper security groups
- Consider using Application Load Balancer with SSL/TLS

### Data Protection

- Enable DynamoDB encryption at rest
- Use HTTPS for web traffic
- Implement proper authentication for production use

## Monitoring and Logging

### CloudWatch Integration

Monitor application performance:
- DynamoDB metrics (read/write capacity, throttling)
- Application logs via CloudWatch Logs
- Custom metrics for query performance

### Cost Optimization

- Use DynamoDB On-Demand for variable workloads
- Monitor and optimize query patterns
- Implement caching for frequently accessed data

## Troubleshooting

### Common Issues

1. **Permission Errors**: Verify IAM permissions
2. **Region Mismatch**: Ensure consistent AWS region configuration
3. **Network Issues**: Check security groups and VPC configuration
4. **Performance**: Monitor DynamoDB capacity and optimize queries

### Debugging

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Considerations

- Implement proper authentication and authorization
- Set up monitoring and alerting
- Configure backup and disaster recovery
- Implement rate limiting and input validation
- Use environment-specific configurations