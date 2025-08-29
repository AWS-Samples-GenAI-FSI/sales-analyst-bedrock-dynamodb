"""
Configuration settings for the GenAI Sales Analyst application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS Bedrock settings
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DEFAULT_MODEL_ID = "amazon.nova-pro-v1:0"

# DynamoDB settings
DYNAMODB_REGION = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE_PREFIX = os.getenv("DYNAMODB_TABLE_PREFIX", "")

# Default table settings
DEFAULT_BILLING_MODE = "PAY_PER_REQUEST"

# Cache settings
SCHEMA_CACHE_TTL = 3600  # Cache schema information for 1 hour
SCHEMA_CACHE_SIZE = 100  # Maximum number of schemas to cache

# UI settings
PAGE_TITLE = "GenAI Sales Analyst – Powered by Amazon Bedrock"
PAGE_LAYOUT = "wide"

# Assets paths
ASSETS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
IMAGES_FOLDER = os.path.join(ASSETS_FOLDER, "images")