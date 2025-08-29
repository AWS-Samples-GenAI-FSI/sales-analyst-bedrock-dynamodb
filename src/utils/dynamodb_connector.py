"""
DynamoDB connector for the GenAI Sales Analyst application.
"""
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from dotenv import load_dotenv
import json
from decimal import Decimal

# Load environment variables
load_dotenv()

def get_dynamodb_client():
    """
    Get a DynamoDB client.
    
    Returns:
        DynamoDB client object
    """
    return boto3.client(
        'dynamodb',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

def get_dynamodb_resource():
    """
    Get a DynamoDB resource.
    
    Returns:
        DynamoDB resource object
    """
    return boto3.resource(
        'dynamodb',
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

def execute_query(query_dict):
    """
    Execute a query on DynamoDB.
    
    Args:
        query_dict: Dictionary containing query parameters
        
    Returns:
        List of dictionaries with query results
    """
    dynamodb = get_dynamodb_resource()
    
    try:
        table_name = query_dict.get('table_name')
        operation = query_dict.get('operation', 'scan')
        
        if not table_name:
            raise ValueError("Table name is required")
            
        table = dynamodb.Table(table_name)
        
        if operation == 'scan':
            # Simple scan operation - ignore complex filter expressions for now
            print(f"DEBUG: Scanning table {table_name}")
            response = table.scan()
            print(f"DEBUG: Found {len(response.get('Items', []))} items")
            
        elif operation == 'query':
            # Query operation
            key_condition = query_dict.get('key_condition')
            filter_expression = query_dict.get('filter_expression')
            projection_expression = query_dict.get('projection_expression')
            
            query_kwargs = {'KeyConditionExpression': key_condition}
            if filter_expression:
                query_kwargs['FilterExpression'] = filter_expression
            if projection_expression:
                query_kwargs['ProjectionExpression'] = projection_expression
                
            response = table.query(**query_kwargs)
            
        else:
            raise ValueError(f"Unsupported operation: {operation}")
            
        # Convert Decimal objects to float for JSON serialization
        items = []
        for item in response.get('Items', []):
            converted_item = convert_decimals(item)
            items.append(converted_item)
        
        print(f"DEBUG: Returning {len(items)} items")
        return items
        
    except Exception as e:
        print(f"Error executing DynamoDB query: {str(e)}")
        return []

def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj

def get_available_tables():
    """
    Get a list of available DynamoDB tables.
    
    Returns:
        List of table names
    """
    client = get_dynamodb_client()
    try:
        response = client.list_tables()
        return response.get('TableNames', [])
    except Exception as e:
        print(f"Error listing tables: {str(e)}")
        return []

def get_table_info(table_name):
    """
    Get information about a DynamoDB table.
    
    Args:
        table_name: Table name
        
    Returns:
        Dictionary with table information
    """
    client = get_dynamodb_client()
    try:
        response = client.describe_table(TableName=table_name)
        table_info = response['Table']
        
        # Extract key schema and attributes
        key_schema = table_info.get('KeySchema', [])
        attribute_definitions = table_info.get('AttributeDefinitions', [])
        
        # Get sample item to understand structure
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)
        sample_response = table.scan(Limit=1)
        sample_item = sample_response.get('Items', [{}])[0] if sample_response.get('Items') else {}
        
        return {
            'table_name': table_name,
            'key_schema': key_schema,
            'attributes': attribute_definitions,
            'sample_item': convert_decimals(sample_item),
            'item_count': table_info.get('ItemCount', 0)
        }
    except Exception as e:
        print(f"Error getting table info for {table_name}: {str(e)}")
        return {}

def create_table(table_name, key_schema, attribute_definitions, billing_mode='PAY_PER_REQUEST'):
    """
    Create a DynamoDB table.
    
    Args:
        table_name: Name of the table
        key_schema: Key schema definition
        attribute_definitions: Attribute definitions
        billing_mode: Billing mode (PAY_PER_REQUEST or PROVISIONED)
        
    Returns:
        Boolean indicating success
    """
    client = get_dynamodb_client()
    try:
        create_params = {
            'TableName': table_name,
            'KeySchema': key_schema,
            'AttributeDefinitions': attribute_definitions,
            'BillingMode': billing_mode
        }
        
        if billing_mode == 'PROVISIONED':
            create_params['ProvisionedThroughput'] = {
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        
        response = client.create_table(**create_params)
        
        # Wait for table to be created
        waiter = client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print(f"Created table: {table_name}")
        return True
        
    except client.exceptions.ResourceInUseException:
        print(f"Table {table_name} already exists")
        return True
    except Exception as e:
        print(f"Error creating table {table_name}: {str(e)}")
        return False

def put_item(table_name, item):
    """
    Put an item into a DynamoDB table.
    
    Args:
        table_name: Name of the table
        item: Item to insert
        
    Returns:
        Boolean indicating success
    """
    dynamodb = get_dynamodb_resource()
    try:
        table = dynamodb.Table(table_name)
        table.put_item(Item=item)
        return True
    except Exception as e:
        print(f"Error putting item into {table_name}: {str(e)}")
        return False

def batch_write_items(table_name, items):
    """
    Batch write items to a DynamoDB table.
    
    Args:
        table_name: Name of the table
        items: List of items to insert
        
    Returns:
        Boolean indicating success
    """
    dynamodb = get_dynamodb_resource()
    try:
        table = dynamodb.Table(table_name)
        
        # DynamoDB batch_writer handles batching automatically
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
        
        print(f"Batch wrote {len(items)} items to {table_name}")
        return True
        
    except Exception as e:
        print(f"Error batch writing to {table_name}: {str(e)}")
        return False

def delete_table(table_name):
    """
    Delete a DynamoDB table.
    
    Args:
        table_name: Name of the table to delete
        
    Returns:
        Boolean indicating success
    """
    client = get_dynamodb_client()
    try:
        client.delete_table(TableName=table_name)
        
        # Wait for table to be deleted
        waiter = client.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
        
        print(f"Deleted table: {table_name}")
        return True
        
    except Exception as e:
        print(f"Error deleting table {table_name}: {str(e)}")
        return False