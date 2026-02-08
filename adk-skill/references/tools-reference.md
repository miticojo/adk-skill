# ADK Tools Reference

## FunctionTool (Explicit Wrapping)

When you need more control over tool creation:

```python
from google.adk.tools import FunctionTool

def calculate(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

calc_tool = FunctionTool(func=calculate)

agent = Agent(
    name="calculator",
    tools=[calc_tool],
)
```

## ToolboxToolset (Database Tools)

Connect to MCP Toolbox for database access:

```python
from google.adk.tools.toolbox_toolset import ToolboxToolset

toolset = ToolboxToolset(
    server_url="http://127.0.0.1:5000",
)

agent = Agent(
    name="db_agent",
    tools=[toolset],
)
```

### With Authentication (Workload Identity)

```python
from toolbox_adk import CredentialStrategy

creds = CredentialStrategy.workload_identity(target_audience="<TOOLBOX_URL>")

toolset = ToolboxToolset(
    server_url="<TOOLBOX_URL>",
    credentials=creds,
)
```

### With Parameter Binding

```python
toolset = ToolboxToolset(
    server_url="...",
    bound_params={
        "region": "us-central1",
        "api_key": lambda: get_api_key(),
    },
)
```

## MCP Tools (Detailed)

### Stdio Connection (Local MCP Server)

```python
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp import StdioServerParameters

tools = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server", "--readOnly"],
            env={
                "MDB_MCP_CONNECTION_STRING": "mongodb://localhost:27017/myDb",
            },
        ),
        timeout=30,
    ),
)
```

### Streamable HTTP Connection (Remote MCP Server)

```python
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp"),
    ),
)
```

## Vertex AI RAG Retrieval

```python
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai import rag

retrieval_tool = VertexAiRagRetrieval(
    name="retrieve_docs",
    description="Search internal documentation",
    rag_resources=[rag.RagResource(rag_corpus=os.environ["RAG_CORPUS"])],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

agent = Agent(
    name="rag_agent",
    tools=[retrieval_tool],
)
```

## Long-Running Tools

For tools with async operations that require polling:

```python
from google.adk.tools import ToolContext

def start_batch_job(job_config: str, tool_context: ToolContext) -> dict:
    """Start a batch processing job."""
    job_id = submit_job(job_config)
    tool_context.state["pending_job"] = job_id
    return {"status": "started", "job_id": job_id}

def check_job_status(job_id: str) -> dict:
    """Check status of a batch job."""
    status = get_job_status(job_id)
    return {"status": status, "job_id": job_id}
```

## Tool Best Practices

1. **Clear docstrings**: The docstring becomes the tool description for the LLM
2. **Type hints**: All parameters must have type hints
3. **Return useful data**: Return structured dicts, not raw strings
4. **Handle errors gracefully**: Return error info, don't raise exceptions
5. **Keep tools focused**: One tool = one action
6. **Use ToolContext for state**: Don't use global variables

```python
# Good: focused, typed, documented
def get_user_profile(user_id: str, tool_context: ToolContext) -> dict:
    """Get a user's profile information.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        dict with name, email, and role fields.
    """
    try:
        profile = db.get_user(user_id)
        return {"name": profile.name, "email": profile.email, "role": profile.role}
    except UserNotFoundError:
        return {"error": f"User {user_id} not found"}

# Bad: vague, no types, no docs
def get_data(id):
    return str(db.query(id))
```
