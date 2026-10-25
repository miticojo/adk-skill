# ADK Memory & Artifacts Reference (Python 2.13.0)

## Memory Service

The `MemoryService` provides long-term knowledge that persists across sessions — think of it as a searchable archive the agent can consult.

### Memory Backends

| Service | Persistence | Search | Best For |
|---------|-----------|--------|----------|
| `InMemoryMemoryService` | None (lost on restart) | Keyword matching | Prototyping, testing |
| `SqliteMemoryService` (2.11+) | Local SQLite file | FTS when available, keyword fallback | Persistent single-host agents |
| `VertexAiMemoryBankService` | Yes (Agent Platform) | Semantic search | Production, LLM-extracted memories |
| `VertexAiRagMemoryService` | Yes (Knowledge Engine) | Vector similarity | RAG pipelines, transcript search |
| `MongoDbMemoryService` (2.13, experimental) | MongoDB collection | Ranked keyword overlap | Shared memory across replicas |

### Persistent Local Memory

```python
from pathlib import Path
from google.adk.memory import SqliteMemoryService

def create_memory(db_path: Path) -> SqliteMemoryService:
    return SqliteMemoryService(db_path=db_path, max_results=20)
```

Attach the service to your runner; close it with `await memory_service.close()` at shutdown. CLI/server service URIs also accept `sqlite://` for memory. Keep the file on durable local storage and back it up as application data. This is a separate database from session history even when both use SQLite.

### MongoDB Sessions and Memory (Experimental)

Install `google-adk[mongodb]`. `MongoDbSessionService` and `MongoDbMemoryService` are exported from `google.adk.integrations.mongodb`; both take `database_name` and either `connection_string` or `mongo_client`. Supply the connection string from your secret configuration. Construction may create indexes, so configure and test against an authorized database.

Session storage retains conversation events/state across runner replicas. Memory search uses keyword overlap without embeddings or a vector index; the separate `MongoDbToolset` supports vector/hybrid search and Atlas Automated Embedding. These are distinct APIs. Agent Engine deployments can resolve toolset credentials at runtime instead of packaging connection strings.

### Memory Mutation APIs

`BaseMemoryService` defines `add_events_to_memory` for incremental ingestion, `add_memory` for explicit entries and `delete_memory(app_name=..., user_id=..., memory_id=...)` (2.13+) for deleting a specific returned memory ID. Backends may raise `NotImplementedError`; check support before using these optional operations. For example, 2.13 SQLite supports session/event ingestion and search, but inherits the unsupported direct-write/delete implementations. Do not treat `memory_id=None` as a portable delete-all operation.

### Adding Sessions to Memory

```python
from google.adk.memory import InMemoryMemoryService
from google.adk.runners import Runner

memory_service = InMemoryMemoryService()

runner = Runner(
    agent=agent, app_name="my_app",
    session_service=session_service,
    memory_service=memory_service,
)

# After a session completes:
completed_session = await runner.session_service.get_session(
    app_name="my_app", user_id="user1", session_id="session-123",
)
await memory_service.add_session_to_memory(completed_session)
```

### Retrieving Memories

**PreloadMemoryTool** — always loads relevant memories at the start of each turn:

```python
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="memory_agent", model="gemini-flash-latest",
    tools=[PreloadMemoryTool()],
)
```

**LoadMemory** — agent decides when to retrieve memories:

```python
from google.adk.tools import load_memory
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="memory_agent", model="gemini-flash-latest",
    tools=[load_memory],
)
```

### Searching Memory Within a Tool

```python
from google.adk.tools import ToolContext

async def search_past_conversations(query: str, tool_context: ToolContext) -> dict:
    response = await tool_context.search_memory(query)
    return {
        "results": [
            part.text
            for entry in response.memories
            for part in (entry.content.parts or [])
            if part.text
        ]
    }
```

### Auto-Saving Sessions via Callback

```python
from google.adk.agents import LlmAgent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

async def auto_save_to_memory(callback_context):
    await callback_context.add_session_to_memory()

agent = LlmAgent(
    name="agent", model="gemini-flash-latest",
    after_agent_callback=auto_save_to_memory,
    tools=[PreloadMemoryTool()],
)
```

### Using Multiple Memory Services

You can manually instantiate a second `BaseMemoryService` for a separate knowledge base:

```python
from google.adk.memory import InMemoryMemoryService

docs_memory = InMemoryMemoryService()  # Second service for docs

async def search_all_memory(query: str, tool_context: ToolContext) -> dict:
    conversational = await tool_context.search_memory(query)
    docs = await docs_memory.search_memory(
        app_name="docs", user_id="shared", query=query
    )
    return {"from_conversations": [...], "from_docs": [...]}
```

---

## Artifacts

Artifacts are named, versioned binary data (files, images, audio) managed by an `ArtifactService`. They persist independently of session state.

### Artifact Backends

| Service | Storage | Persistence | Best For |
|---------|---------|-----------|----------|
| `InMemoryArtifactService` | Python dict | Lost on restart | Prototyping, testing |
| `FileArtifactService` | Local directory | Yes, if disk is retained | Local persistent agents |
| `GcsArtifactService` | Google Cloud Storage | Yes | Production |

`FileArtifactService(root_dir=...)` isolates artifacts by application/user/session and publishes versions atomically. Choose an application-owned directory; do not expose arbitrary user filesystem paths as artifact names.

### Configuring the Runner

```python
from google.adk.artifacts import InMemoryArtifactService, GcsArtifactService
from google.adk.runners import Runner

artifact_service = InMemoryArtifactService()  # Or GcsArtifactService("my-bucket")

runner = Runner(
    agent=agent, app_name="my_app",
    session_service=session_service,
    artifact_service=artifact_service,
)
```

### Saving and Loading Artifacts

```python
import google.genai.types as types
from google.adk.tools import ToolContext

# In a tool:
async def save_report(filename: str, tool_context: ToolContext) -> str:
    """Save a small UTF-8 report as a versioned artifact."""
    artifact = types.Part.from_bytes(data=b"Report ready\n", mime_type="text/plain")
    version = await tool_context.save_artifact(filename, artifact)
    return f"Saved {filename} (version {version})"

async def load_latest_report(filename: str, tool_context: ToolContext) -> dict:
    """Read the latest report's binary metadata."""
    artifact = await tool_context.load_artifact(filename)  # Latest version
    # artifact = await tool_context.load_artifact(filename, version=2)
    if artifact is None:
        return {"error": f"{filename} not found"}
    if artifact.inline_data is None:
        return {"error": "Artifact contains a URI instead of inline bytes"}
    return {"mime_type": artifact.inline_data.mime_type, "size": len(artifact.inline_data.data or b"")}

async def list_files(tool_context: ToolContext) -> list[str]:
    """List the current session's artifact filenames."""
    return await tool_context.list_artifacts()
```

### Namespacing

- **Session scope** (default): `"report.pdf"` — tied to `app_name + user_id + session_id`
- **User scope**: `"user:profile.png"` — accessible across all sessions for that user

```python
# Session-scoped
await tool_context.save_artifact("summary.txt", artifact)

# User-scoped (accessible from any session for this user)
await tool_context.save_artifact("user:settings.json", artifact)
```

### LoadArtifactsTool

Built-in tool that lets the LLM decide which artifacts to load before answering:

```python
from google.adk.tools.load_artifacts_tool import LoadArtifactsTool
from google.adk.agents import LlmAgent

agent = LlmAgent(
    name="artifact_reader", model="gemini-flash-latest",
    instruction="Answer questions about available user files. Call load_artifacts before answering.",
    tools=[LoadArtifactsTool()],
)
```

Loaded artifact content is temporarily appended to the LLM request, not permanently saved to session history.

### Best Practices

- Use descriptive filenames with extensions (`"monthly_report.pdf"`, `"avatar.jpg"`)
- Always specify correct `mime_type` when creating the artifact `Part`
- `load_artifact()` without version retrieves the latest
- Check if `artifact_service` is configured before calling context methods (raises `ValueError` if None)
- `load_artifact()` returns `None` if the artifact doesn't exist
- Implement cleanup strategies for production (`GcsArtifactService` artifacts persist until explicitly deleted)

`GcsArtifactService` also provides `get_authenticated_url` and `get_signed_url` (2.9+) for controlled file access. A signed URL is a bearer capability: set an appropriate expiry and avoid logging it. In-memory services copy stored artifact values to prevent caller mutation from changing persisted data (2.12+).

## Versioned Sources

- [Memory service optional operations](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/memory/base_memory_service.py)
- [SQLite memory](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/memory/_sqlite_memory_service.py)
- [MongoDB integrations](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/integrations/mongodb/README.md)
- [File artifacts](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/artifacts/file_artifact_service.py)
