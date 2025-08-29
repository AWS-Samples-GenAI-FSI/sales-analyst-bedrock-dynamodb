# Security Policy

## Reporting a Vulnerability

If you discover a potential security issue in this project, we ask that you notify AWS Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public GitHub issue.

## Security Considerations

This sample application demonstrates integration with AWS services and includes several security considerations:

### AWS Credentials
- Never commit AWS credentials to version control
- Use IAM roles when running on AWS infrastructure
- Follow the principle of least privilege for IAM permissions
- Rotate access keys regularly

### Data Protection
- The sample uses the Northwind dataset which contains no sensitive information
- In production, ensure proper data classification and protection
- Consider encryption at rest and in transit for sensitive data

### Network Security
- The application runs locally by default
- When deploying to production, implement proper network controls
- Use VPC endpoints for AWS service communication when possible

### Application Security
- Keep dependencies updated to address known vulnerabilities
- Validate and sanitize all user inputs
- Implement proper error handling to avoid information disclosure

### DynamoDB Security
- Use IAM policies to control access to DynamoDB tables
- Enable point-in-time recovery for production tables
- Consider using DynamoDB encryption at rest
- Monitor access patterns with CloudTrail

## Supported Versions

This project follows AWS best practices for security. We recommend always using the latest version of the sample code and keeping dependencies updated.

## Security Updates

Security updates will be communicated through:
- GitHub Security Advisories
- Updates to this SECURITY.md file
- Release notes for new versions