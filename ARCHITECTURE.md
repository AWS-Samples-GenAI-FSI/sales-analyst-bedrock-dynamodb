# Architecture Overview

## System Architecture

The GenAI Sales Analyst with DynamoDB follows a serverless, event-driven architecture optimized for scalability and cost-effectiveness.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │   Amazon         │    │   Amazon        │
│   Web App       │◄──►│   Bedrock        │    │   DynamoDB      │
│                 │    │                  │    │                 │
│ • User Interface│    │ • Claude/Titan   │    │ • Northwind     │
│ • Query Input   │    │ • Embeddings     │    │ • Sales Data    │
│ • Results       │    │ • Text Gen       │    │ • NoSQL Schema  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌──────────────────┐            │
         └──────────────►│   LangGraph      │◄───────────┘
                        │   Workflow       │
                        │                  │
                        │ • Query Planning │
                        │ • Execution      │
                        │ • Aggregation    │
                        └──────────────────┘
                                 │
                        ┌──────────────────┐
                        │   FAISS Vector   │
                        │   Store          │
                        │                  │
                        │ • Schema Search  │
                        │ • Metadata       │
                        └──────────────────┘
```

## Component Details

### 1. Streamlit Web Application
- **Purpose**: User interface and application orchestration
- **Responsibilities**:
  - Render interactive web interface
  - Handle user input and session management
  - Display results and visualizations
  - Manage application state

### 2. Amazon Bedrock
- **Purpose**: AI/ML services for natural language processing
- **Models Used**:
  - **Claude 3**: Advanced reasoning and query generation
  - **Titan Embeddings**: Vector representations for semantic search
- **Capabilities**:
  - Natural language to NoSQL query translation
  - Result analysis and explanation generation
  - Semantic understanding of business questions

### 3. Amazon DynamoDB
- **Purpose**: Primary data store for sales analytics
- **Design Pattern**: Single-table design with denormalized data
- **Tables**:
  - `sales_transactions`: Denormalized transaction data
  - `northwind_*`: Normalized source tables (8 tables)
- **Benefits**:
  - Sub-millisecond latency
  - Automatic scaling
  - No infrastructure management

### 4. LangGraph Workflow Engine
- **Purpose**: Orchestrate complex analysis workflows
- **Workflow Steps**:
  1. **Query Understanding**: Parse natural language intent
  2. **Schema Retrieval**: Find relevant data structures
  3. **Query Generation**: Create optimized DynamoDB queries
  4. **Execution**: Run queries against DynamoDB
  5. **Aggregation**: Process results client-side
  6. **Analysis**: Generate insights and explanations

### 5. FAISS Vector Store
- **Purpose**: Semantic search for database metadata
- **Contents**:
  - Table schemas and relationships
  - Column descriptions and data types
  - Query patterns and examples
- **Usage**: Help AI understand available data for better query generation

## Data Flow

### 1. User Query Processing
```
User Question → Streamlit → LangGraph → Bedrock (Understanding)
```

### 2. Schema Discovery
```
LangGraph → FAISS → Relevant Schema → Bedrock (Context)
```

### 3. Query Generation
```
Bedrock → NoSQL Query → DynamoDB → Raw Results
```

### 4. Result Processing
```
Raw Results → Client Aggregation → Bedrock (Analysis) → User
```

## Design Patterns

### Single-Table Design
- **Principle**: Store related data together to minimize queries
- **Implementation**: Denormalized `sales_transactions` table
- **Benefits**:
  - Faster queries (no JOINs)
  - Predictable performance
  - Cost optimization

### Client-Side Aggregation
- **Rationale**: DynamoDB doesn't support complex aggregations
- **Implementation**: Pandas operations on query results
- **Trade-offs**: 
  - ✅ Flexibility in analysis
  - ❌ Memory usage for large datasets

### AI-Driven Query Generation
- **Approach**: Natural language → Structured queries
- **Benefits**:
  - No SQL knowledge required
  - Adaptive to various question types
  - Contextual understanding

## Scalability Considerations

### DynamoDB Scaling
- **Read Capacity**: Auto-scales based on demand
- **Write Capacity**: Batch operations for data loading
- **Partitioning**: Designed for even data distribution

### Application Scaling
- **Stateless Design**: Each request is independent
- **Caching**: FAISS index loaded once per session
- **Resource Management**: Efficient memory usage patterns

### Cost Optimization
- **On-Demand Pricing**: Pay only for actual usage
- **Efficient Queries**: Minimize read operations
- **Data Lifecycle**: Automated cleanup capabilities

## Security Architecture

### Data Protection
- **Encryption**: DynamoDB encryption at rest
- **Access Control**: IAM-based permissions
- **Network Security**: VPC endpoints (optional)

### Application Security
- **Credential Management**: Environment variables
- **Input Validation**: Sanitized user inputs
- **Error Handling**: No sensitive data exposure

## Monitoring and Observability

### Metrics
- **DynamoDB**: Read/write capacity, throttling, latency
- **Bedrock**: Model invocations, token usage, errors
- **Application**: Query performance, user sessions

### Logging
- **Application Logs**: Query patterns, errors, performance
- **AWS CloudTrail**: API calls and access patterns
- **Custom Metrics**: Business-specific KPIs

## Future Enhancements

### Potential Improvements
1. **Real-time Data**: DynamoDB Streams for live updates
2. **Advanced Analytics**: Integration with Amazon QuickSight
3. **Multi-tenancy**: Partition data by organization
4. **Caching Layer**: ElastiCache for frequently accessed data
5. **API Gateway**: RESTful API for external integrations

### Scalability Roadmap
1. **Global Tables**: Multi-region deployment
2. **Lambda Integration**: Serverless compute for complex operations
3. **Event-Driven Architecture**: Asynchronous processing
4. **Machine Learning**: Predictive analytics with SageMaker