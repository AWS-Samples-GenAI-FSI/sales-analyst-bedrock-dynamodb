"""
LangGraph workflow for the GenAI Sales Analyst application.
"""
from typing import Dict, Any, List, Tuple
import json
from datetime import datetime


class AnalysisWorkflow:
    """
    LangGraph workflow for sales data analysis.
    """
    
    def __init__(self, bedrock_helper, vector_store, monitor=None):
        """
        Initialize the analysis workflow.

        Args:
            bedrock_helper: Client for Amazon Bedrock API
            vector_store: Vector store for similarity search
            monitor: Optional monitoring client
        """
        self.bedrock = bedrock_helper
        self.vector_store = vector_store
        self.monitor = monitor
    
    def understand_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Understand and classify the user query.

        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        query = state['query']
        
        prompt = f"""Analyze this query and classify it:
        
Query: {query}

Determine:
1. Query type (analysis/nosql/metadata/comparison)
2. Required data sources or tables
3. Time frame mentioned (if any)
4. Specific metrics requested (if any)

Return as JSON with these fields.
"""
        
        try:
            response = self.bedrock.invoke_model(prompt)
            
            # Parse the response as JSON
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # If not valid JSON, create a simple structure
                analysis = {
                    "type": "analysis",
                    "data_sources": [],
                    "time_frame": "not specified",
                    "metrics": []
                }
            
            return {
                **state,
                "query_analysis": analysis,
                "steps_completed": state.get("steps_completed", []) + ["understand_query"]
            }
        except Exception as e:
            return {
                **state,
                "error": f"Error in understand_query: {str(e)}",
                "steps_completed": state.get("steps_completed", []) + ["understand_query_error"]
            }
    
    def retrieve_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve relevant context from vector store.

        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with relevant context
        """
        if "error" in state:
            return state
            
        query = state['query']
        
        try:
            # Get similar documents from vector store
            similar_docs = self.vector_store.similarity_search(query, k=5)
            
            # Handle empty results
            if not similar_docs:
                # For queries with no context, use DynamoDB table info
                return {
                    **state,
                    "relevant_context": [{
                        "text": "Use DynamoDB tables: customers, orders, order_details, products, categories, suppliers, employees, shippers"
                    }],
                    "steps_completed": state.get("steps_completed", []) + ["retrieve_context", "fallback_context"]
                }
            
            return {
                **state,
                "relevant_context": similar_docs,
                "steps_completed": state.get("steps_completed", []) + ["retrieve_context"]
            }
        except Exception as e:
            return {
                **state,
                "error": f"Error in retrieve_context: {str(e)}",
                "steps_completed": state.get("steps_completed", []) + ["retrieve_context_error"]
            }
    
    def generate_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate DynamoDB query based on the query and context.

        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with generated query
        """
        if "error" in state:
            return state
            
        query = state['query']
        context = state.get('relevant_context', [])
        
        # Import NoSQL generator
        from ..models.nosql_generator import NoSQLGenerator
        from ..utils.dynamodb_connector import get_available_tables, get_table_info
        
        try:
            # Get table schemas
            tables = get_available_tables()
            table_schemas = {}
            if 'sales_transactions' in tables:
                table_schemas['sales_transactions'] = get_table_info('sales_transactions')
            
            # Generate NoSQL query
            generator = NoSQLGenerator()
            query_dict = generator.generate_query(query, table_schemas)
            
            return {
                **state,
                "generated_query": query_dict,
                "steps_completed": state.get("steps_completed", []) + ["generate_query"]
            }
        except Exception as e:
            return {
                **state,
                "error": f"Error in generate_query: {str(e)}",
                "steps_completed": state.get("steps_completed", []) + ["generate_query_error"]
            }
    
    def analyze_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze query results and provide an answer.

        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with analysis
        """
        if "error" in state:
            return state
            
        query = state['query']
        query_dict = state.get('generated_query', {})
        results = state.get('query_results', [])
        
        # Convert results to string representation
        if not results:
            analysis = "No results found for this query."
            
            return {
                **state,
                "analysis": analysis,
                "steps_completed": state.get("steps_completed", []) + ["analyze_results"]
            }
        
        results_str = "\n".join([str(row) for row in results[:10]])
        if len(results) > 10:
            results_str += f"\n... and {len(results) - 10} more rows"
        
        prompt = f"""Analyze these DynamoDB query results to answer the user's question:
        
Question: {query}

DynamoDB Query: {json.dumps(query_dict, indent=2)}

Query Results (first 10 rows):
{results_str}

Provide a clear, concise analysis that directly answers the question. Include key insights from the data.
"""
        
        try:
            analysis = self.bedrock.invoke_model(prompt)
            
            return {
                **state,
                "analysis": analysis.strip(),
                "steps_completed": state.get("steps_completed", []) + ["analyze_results"]
            }
        except Exception as e:
            return {
                **state,
                "error": f"Error in analyze_results: {str(e)}",
                "steps_completed": state.get("steps_completed", []) + ["analyze_results_error"]
            }
    
    def handle_error(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle errors in the workflow.

        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state with error handling
        """
        error = state.get('error', 'Unknown error')
        
        # Generate a user-friendly error message
        prompt = f"""An error occurred while processing this query:
        
Query: {state.get('query', '')}

Error: {error}

Generate a user-friendly error message explaining what went wrong and suggesting how to fix it.
"""
        
        try:
            friendly_message = self.bedrock.invoke_model(prompt)
        except Exception:
            friendly_message = f"Sorry, an error occurred: {error}. Please try rephrasing your question."
        
        return {
            **state,
            "error_handled": True,
            "friendly_error": friendly_message.strip(),
            "steps_completed": state.get("steps_completed", []) + ["handle_error"]
        }
    
    def execute(self, query: str, execute_query_func=None) -> Dict[str, Any]:
        """
        Execute the analysis workflow.

        Args:
            query: User query string
            execute_query_func: Function to execute DynamoDB queries
            
        Returns:
            Final workflow state
        """
        # Initialize state
        state = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "steps_completed": []
        }
        
        # Execute workflow steps manually instead of using LangGraph
        state = self.understand_query(state)
        
        if "error" not in state:
            state = self.retrieve_context(state)
        
        if "error" not in state:
            state = self.generate_query(state)
        
        # Execute DynamoDB query if available and no errors
        if "generated_query" in state and "error" not in state and execute_query_func:
            try:
                start_time = datetime.now()
                results = execute_query_func(state["generated_query"])
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                state["query_results"] = results
                state["execution_time"] = execution_time
                
                # Process aggregations if needed
                query_dict = state["generated_query"]
                print(f"DEBUG: Raw results count: {len(results)}")
                if self._needs_aggregation(state['query']):
                    print(f"DEBUG: Processing aggregation for query: {state['query']}")
                    results = self._process_aggregation(results, state['query'])
                    print(f"DEBUG: After aggregation count: {len(results)}")
                    state["query_results"] = results
                
                # Analyze results
                state = self.analyze_results(state)
                
            except Exception as e:
                state["error"] = f"Error executing DynamoDB query: {str(e)}"
                state = self.handle_error(state)
        elif "error" in state:
            state = self.handle_error(state)
        
        return state
    
    def _needs_aggregation(self, query: str) -> bool:
        """Check if query needs aggregation processing."""
        aggregation_keywords = ['top', 'best', 'highest', 'lowest', 'most', 'least', 'average', 'total', 'sum', 'count']
        return any(keyword in query.lower() for keyword in aggregation_keywords)
    
    def _process_aggregation(self, results: List[Dict], query: str) -> List[Dict]:
        """Process aggregation on results."""
        from ..models.nosql_generator import process_aggregation, group_by_field
        
        query_lower = query.lower()
        print(f"DEBUG: Processing aggregation for query: {query_lower}")
        
        # For product revenue queries
        if 'product' in query_lower and 'revenue' in query_lower:
            print(f"DEBUG: Grouping by product_name and summing line_total")
            return group_by_field(results, 'product_name', 'line_total', 'sum')[:10]
        elif 'customer' in query_lower and ('order value' in query_lower or 'total' in query_lower):
            return group_by_field(results, 'customer_name', 'line_total', 'sum')[:10]
        elif 'count' in query_lower and 'country' in query_lower:
            return group_by_field(results, 'customer_country', None, 'count')[:10]
        elif 'price' in query_lower and ('highest' in query_lower or 'expensive' in query_lower):
            if results and 'unit_price' in results[0]:
                results.sort(key=lambda x: float(x.get('unit_price', 0)), reverse=True)
                return results[:10]
        
        return results[:10]