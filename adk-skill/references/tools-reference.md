# ADK Tools Reference (Python 2.13.0)

## FunctionTool (Explicit Wrapping)

When you need more control over tool creation:

```python
import math
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

def calculate(left: float, right: float) -> dict[str, float]:
    """Add two finite numbers.

    Args:
        left: First number.
        right: Second number.
    """
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool)
               and math.isfinite(value) for value in (left, right)):
        raise ValueError("Both operands must be finite numbers")
    result = left + right
    if not math.isfinite(result):
        raise ValueError("Result must be finite")
    return {"result": result}

calc_tool = FunctionTool(func=calculate)

agent = LlmAgent(
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
import os
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams

tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp"),
    ),
)
```

### MCP Extras (2.7+)

- `elicitation_callback=` on `MCPToolset` — handle server elicitation requests programmatically.
- `MCPToolset` can reuse the server's tool list instead of re-declaring schemas.
- HTTP trace debugging extends to MCP toolset operations (2.4+).
- ADK 2.9+ supports MCP SDK 1.x and 2.x. For SDK 2.x, `ADK_ENABLE_MCP_MODERN_PROTOCOL=1` opts into the modern wire path (2.11+); SDK compatibility does not turn that behavior on automatically.
- Keep connection/toolset cleanup in the runner's lifecycle. Prefer Streamable HTTP for new remote servers; SSE is a legacy transport.

## Agent as MCP Server

Expose an entire ADK agent as one MCP tool so any MCP host (Claude Code, IDEs, Codex) can drive it — the MCP counterpart of `to_a2a()` (2.5+):

```python
from google.adk.tools.mcp_tool import to_mcp_server

server = to_mcp_server(root_agent)   # -> FastMCP; name/instructions/runner optional
server.run(transport="stdio")        # or transport="streamable-http"
```

One ADK session is kept per MCP connection, so successive calls form a multi-turn conversation.

## Vertex AI RAG Retrieval

```python
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from agentplatform import rag

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

## Managed API and Pub/Sub Integrations

Use `AgentRegistry` from `google.adk.integrations.agent_registry` for managed MCP/A2A discovery. Its import needs the `[agent-identity]` extra and runtime credentials. The old `integrations.api_registry.ApiRegistry` is deprecated; there is no `tools.api_registry_toolset.APIRegistryToolset` module in 2.13.

Pub/Sub uses `PubSubToolset` from `google.adk.tools.pubsub.pubsub_toolset`, with `credentials_config` and `pubsub_tool_config`, not a `PubSubTool(project=..., topic=...)` constructor. Install `[gcp]` when using cloud tool integrations. Configure allowed operations and project scope before adding tools that publish messages.

Sources: [Agent Registry](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/integrations/agent_registry/agent_registry.py), [Pub/Sub toolset](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/tools/pubsub/pubsub_toolset.py).

## Eventarc Advanced Toolset

Receive and act on Google Cloud events via Eventarc Advanced (2.6+):

```python
from google.adk.integrations.eventarc import EventarcToolset
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="event_responder",
    tools=[EventarcToolset()],
)
```

Supports Context callables and correct OMIT behavior (2.7+).

## OpenAPI Tools

Generate tools from an OpenAPI spec (REST APIs):

```python
from google.adk.tools.openapi_tool import OpenAPIToolset
from pathlib import Path

toolset = OpenAPIToolset(
    spec_str=Path("openapi.yaml").read_text(), spec_str_type="yaml",
    # Optional: auth header
    header_provider=lambda context: {"Authorization": f"Bearer {get_token()}"},
)

agent = Agent(
    name="rest_agent",
    tools=[toolset],
)
```

## SkillToolset (Agent Skills)

Load Agent Skills (per [agentskills.io spec](https://agentskills.io/specification)) into your agent at runtime. `SkillToolset` is stable in 2.13. Skills are modular instruction packages with three levels: L1 (metadata for discovery), L2 (instructions loaded on trigger), L3 (references/assets/scripts loaded on demand).

### Load from Directory

```python
import pathlib
from google.adk import Agent
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

weather_skill = load_skill_from_dir(
    pathlib.Path(__file__).parent / "skills" / "weather_skill"
)

root_agent = Agent(
    model="gemini-flash-latest",
    name="skill_user_agent",
    instruction="You are a helpful assistant that can leverage skills.",
    tools=[
        skill_toolset.SkillToolset(skills=[weather_skill]),
    ],
)
```

### Directory Structure

```
my_agent/
├── agent.py
├── skills/
│   └── weather_skill/          # Follows Agent Skill spec
│       ├── SKILL.md            # Required: frontmatter + instructions
│       ├── references/         # Optional: extended guidance
│       │   └── api-details.md
│       └── assets/             # Optional: templates, data
│           └── schema.json
```

### Define Inline (in Code)

```python
from google.adk.skills import models

greeting_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="greeting-skill",
        description="A friendly greeting skill.",
    ),
    instructions="Greet the user warmly. Refer to references for style.",
    resources=models.Resources(
        references={
            "style.md": "Always greet with enthusiasm and use the user's name.",
        },
    ),
)
```

**Notes (2.5+ / 2.7+):**
- The Google Cloud Skill Registry backend migrated to the Agent Registry endpoint — enable the Agent Registry API and migrate data when upgrading.
- Non-blocking skill loading is supported in async runtimes.
- Skills can execute `scripts/` inside an [Environment](#environments-sandboxed-code-execution) (Daytona, Cloud Run sandbox).

### Discovery and Lifecycle (2.10+)

The following standalone configuration illustrates a bounded catalog. Enable `ADK_ENABLE_SKILL_LIFECYCLE=1` before starting the process to use lifecycle behavior; it remains experimental and off by default even though `SkillToolset` is stable.

```python
from google.adk.skills import models
from google.adk.tools.skill_toolset import (
    SkillToolset, SkillDiscoveryMode, SkillLifecycleConfig, SkillLifecycleMode,
)

greeting_skill = models.Skill(
    frontmatter=models.Frontmatter(name="greeting-skill", description="Greet a user."),
    instructions="Greet the user briefly.",
)
skill_tools = SkillToolset(
    skills=[greeting_skill],
    discovery_mode=SkillDiscoveryMode.LAZY,
    lifecycle_config=SkillLifecycleConfig(
        default_mode=SkillLifecycleMode.BOUNDED, max_active_skills=3,
    ),
)
```

`LAZY` offers discovery on demand; `EAGER` includes the catalog in instructions. `PERSISTENT` skills stay active and do not count against the cap; `BOUNDED` skills are evicted by the cap; `EPHEMERAL` skills expire after the invocation that loaded them (under `run_live` they persist for the stream). Programmatic APIs are `await skill_tools.load_skill(ctx, name)`, `skill_tools.unload_skill(ctx, name)` and `skill_tools.list_active_skills(ctx)`. Unloading removes later instruction injection; it does not delete external files or revoke effects already performed.

`SkillLifecycleConfig(revalidate_skills=True)` checks for changed content; this may require registry reads and invalidate prompt caches. `SkillToolset(save_output_artifacts=True)` persists generated script output files as artifacts (2.12+); configure an artifact service and a code executor/environment. The script tool is offered only when script execution is configured.

---

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
4. **Distinguish failures**: Return structured results for expected domain errors; raise transient failures when a configured retry policy should retry them. Retried operations must be idempotent.
5. **Keep tools focused**: One tool = one action
6. **Use ToolContext for state**: Don't use global variables
7. **Never catch `BaseException`**: It traps `NodeInterruptedError`, breaking HITL pause/resume

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

## Tool Authentication

Configure authentication for custom tools (API keys, OAuth):

```python
import os
from fastapi.openapi.models import APIKey, APIKeyIn
from google.adk.auth.auth_credential import AuthCredential, AuthCredentialTypes
from google.adk.auth.auth_tool import AuthConfig
from google.adk.tools.authenticated_function_tool import AuthenticatedFunctionTool

def get_customer_data(customer_id: str, credential: AuthCredential) -> dict:
    """Prepare an authenticated CRM request for a customer.

    Args:
        customer_id: Customer identifier.
    """
    # Use credential.api_key in your HTTP client's header; never return it.
    return {"customer_id": customer_id, "status": "ready"}

# Tool with API key auth
tool = AuthenticatedFunctionTool(
    func=get_customer_data,
    auth_config=AuthConfig(
        auth_scheme=APIKey(**{"in": APIKeyIn.header}, name="X-API-Key"),
        raw_auth_credential=AuthCredential(
            auth_type=AuthCredentialTypes.API_KEY, api_key=os.environ["CRM_API_KEY"],
        ),
    ),
)
```

## Tool Action Confirmations

Request human confirmation before executing sensitive tool operations:

```python
from google.adk.tools import FunctionTool

def delete_account(account_id: str) -> dict:
    """Delete a user account. Requires confirmation."""
    ...

# Mark tool as requiring confirmation
delete_tool = FunctionTool(
    func=delete_account,
    require_confirmation=True,
)
```

When the LLM calls a tool with `require_confirmation=True`, the framework pauses execution and waits for human approval before proceeding.

## LoadArtifactsTool

Built-in tool for loading binary artifacts into the agent context:

```python
from google.adk.tools.load_artifacts_tool import LoadArtifactsTool

agent = LlmAgent(
    name="artifact_reader", model="gemini-flash-latest",
    instruction="Answer questions about available user files.",
    tools=[LoadArtifactsTool()],
)
```

When the model calls `load_artifacts`, the selected artifact contents are temporarily appended to the LLM request. The content is not permanently saved to session history. 2.5+ parses binary text documents (e.g. DOCX); 2.7+ lets you customize how attachment data is fed to the LLM.

## Media in Function Responses

Since 2.7, tools can return media (images/audio) as part of the function response instead of text-only results — return the media `Part` in the response payload and ADK forwards it to the model/user.

## Environments (Sandboxed Code Execution)

Code-executor environments include E2B (`[e2b]`), Daytona (`[daytona]`), Cloud Run, OpenSandbox (`[opensandbox]`, 2.13+) and `AgentEngineEnvironment` (2.13+). These backends have different isolation and credential requirements; choose a configured remote environment for untrusted scripts. Skills scripts run against the configured environment.

## Model Consultation (2.11+)

Use an advisor when the executor needs another model's analysis, while retaining control of the tools. This differs from model failover, which retries a failed generation on a backup model.

```python
from google.adk.agents import LlmAgent
from google.adk.tools import ModelConsultTool

agent = LlmAgent(
    name="executor", model="gemini-flash-latest",
    instruction="Consult the advisor for difficult decisions; execute tools yourself.",
    tools=[ModelConsultTool(
        model="gemini-flash-latest", max_uses=1, session_max_uses=3,
        timeout_seconds=30,
    )],
)
```

The advisor receives context but no executable tools. Budgets are per invocation and per session. ADK 2.13 adds `ForceEscalationPlugin` for deterministic consultation and consultation token/cost telemetry; configure these only when the workflow requires them.

## Versioned Sources

- [Skill discovery, lifecycle and artifact persistence](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/tools/skill_toolset.py)
- [Feature stages and defaults](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/features/_feature_registry.py)
- [Model consultation](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/tools/model_consult/_model_consult_tool.py)
- [2.8 auth, duplicate-call, credential-redaction and memory-search fixes](https://github.com/google/adk-python/releases/tag/v2.8.0)
