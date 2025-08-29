"""
NoSQL query generation model using Amazon Bedrock for DynamoDB.
"""
import streamlit as st
from ..utils.bedrock_client import invoke_bedrock_model
from ..config.settings import DEFAULT_MODEL_ID
from boto3.dynamodb.conditions import Key, Attr
import json

class NoSQLGenerator:
    """
    NoSQL Generator class using Amazon Bedrock for DynamoDB queries.
    """
    
    def __init__(self, model_id=DEFAULT_MODEL_ID):
        """
        Initialize the NoSQL Generator.

        Args:
            model_id (str, optional): The model ID to use. Defaults to DEFAULT_MODEL_ID.
        """
        self.model_id = model_id
    
    def generate_query(self, nl_query, table_schemas):
        """
        Generate DynamoDB query from natural language query.

        Args:
            nl_query (str): Natural language query.
            table_schemas (dict): Dictionary of table schemas.
            
        Returns:
            dict: Query parameters for DynamoDB
        """
        schema_context = self._build_schema_context(table_schemas)
        
        message_content = (
            f"You are an expert DynamoDB query generator. "
            f"Generate a DynamoDB query operation based on the natural language request.\n\n"
            f"Available Tables and Schema:\n{schema_context}\n\n"
            f"Natural Language Query: {nl_query}\n\n"
            f"Generate a JSON response with the following structure:\n"
            f"{{\n"
            f'  "operation": "scan" or "query",\n'
            f'  "table_name": "table_name",\n'
            f'  "key_condition": "for query operations only",\n'
            f'  "filter_expression": "optional filter",\n'
            f'  "projection_expression": "optional projection",\n'
            f'  "explanation": "brief explanation of the query"\n'
            f"}}\n\n"
            f"Important DynamoDB Guidelines:\n"
            f"- Use 'scan' for full table scans or when filtering on non-key attributes\n"
            f"- Use 'query' only when filtering by partition key (and optionally sort key)\n"
            f"- For aggregations like COUNT, SUM, AVG, use scan with appropriate filters\n"
            f"- Return only valid JSON, no additional text\n"
        )

        result = invoke_bedrock_model(message_content, self.model_id)
        
        if result:
            try:
                # Extract JSON from response
                response_text = self._extract_response_text(result)
                # Clean up response text
                response_text = response_text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                response_text = response_text.strip()
                
                query_dict = json.loads(response_text)
                return query_dict
            except (json.JSONDecodeError, KeyError) as e:
                return self._fallback_query(nl_query)
        else:
            return self._fallback_query(nl_query)
    
    def _extract_response_text(self, response_json):
        """Extract text from Bedrock response."""
        if isinstance(response_json, dict):
            content = response_json.get("output", {}).get("message", {}).get("content", [])
            if isinstance(content, list) and content:
                return content[0].get("text", "").strip()
        return str(response_json).strip()
    
    def _build_schema_context(self, table_schemas):
        """Build schema context string for the AI model."""
        context = ""
        for table_name, schema in table_schemas.items():
            context += f"\nTable: {table_name}\n"
            context += f"Key Schema: {schema.get('key_schema', [])}\n"
            
            # Add sample item structure if available
            sample_item = schema.get('sample_item', {})
            if sample_item:
                context += f"Sample Item Structure: {list(sample_item.keys())}\n"
            
            context += f"Description: {self._get_table_description(table_name)}\n"
        
        return context
    
    def _get_table_description(self, table_name):
        """Get description for common Northwind tables."""
        descriptions = {
            'customers': 'Customer information including company name, contact details, and location',
            'products': 'Product catalog with names, prices, categories, and stock levels',
            'orders': 'Order information including dates, customer, employee, and shipping details',
            'order_details': 'Order line items with product, quantity, price, and discount information',
            'categories': 'Product categories with names and descriptions',
            'suppliers': 'Supplier information including company details and contacts',
            'employees': 'Employee data including names, titles, and hire dates',
            'shippers': 'Shipping company information'
        }
        return descriptions.get(table_name, 'Business data table')
    
    def _fallback_query(self, nl_query):
        """Generate fallback query for common cases."""
        return {
            'operation': 'scan',
            'table_name': 'sales_transactions',
            'explanation': 'Scanning denormalized sales transactions table for analysis'
        }

def process_aggregation(items, aggregation_type, field=None):
    """
    Process aggregation operations on DynamoDB results.
    
    Args:
        items (list): List of items from DynamoDB
        aggregation_type (str): Type of aggregation (count, sum, avg, max, min)
        field (str): Field to aggregate on (for sum, avg, max, min)
        
    Returns:
        dict: Aggregation result
    """
    if not items:
        return {'result': 0, 'count': 0}
    
    if aggregation_type.lower() == 'count':
        return {'result': len(items), 'count': len(items)}
    
    if not field:
        return {'result': len(items), 'count': len(items)}
    
    # Extract numeric values for the field
    values = []
    for item in items:
        if field in item:
            try:
                value = float(item[field])
                values.append(value)
            except (ValueError, TypeError):
                continue
    
    if not values:
        return {'result': 0, 'count': 0}
    
    if aggregation_type.lower() == 'sum':
        return {'result': sum(values), 'count': len(values)}
    elif aggregation_type.lower() == 'avg':
        return {'result': sum(values) / len(values), 'count': len(values)}
    elif aggregation_type.lower() == 'max':
        return {'result': max(values), 'count': len(values)}
    elif aggregation_type.lower() == 'min':
        return {'result': min(values), 'count': len(values)}
    else:
        return {'result': len(values), 'count': len(values)}

def group_by_field(items, group_field, aggregation_field=None, aggregation_type='count'):
    """
    Group items by a field and perform aggregation.
    
    Args:
        items (list): List of items from DynamoDB
        group_field (str): Field to group by
        aggregation_field (str): Field to aggregate (optional)
        aggregation_type (str): Type of aggregation
        
    Returns:
        list: List of grouped results
    """
    groups = {}
    
    for item in items:
        if group_field not in item:
            continue
            
        group_key = str(item[group_field])
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(item)
    
    results = []
    for group_key, group_items in groups.items():
        agg_result = process_aggregation(group_items, aggregation_type, aggregation_field)
        results.append({
            group_field: group_key,
            f'{aggregation_type}_{aggregation_field or "items"}': agg_result['result'],
            'count': agg_result['count']
        })
    
    # Sort by aggregation result descending
    results.sort(key=lambda x: x[f'{aggregation_type}_{aggregation_field or "items"}'], reverse=True)
    return results