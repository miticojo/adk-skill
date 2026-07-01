# ADK Memory & Artifacts Reference

## Memory Service

The `MemoryService` provides long-term knowledge that persists across sessions — think of it as a searchable archive the agent can consult.

### Memory Backends

| Service | Persistence | Search | Best For |
|---------|-----------|--------|----------|
| `InMemoryMemoryService` | None (lost on restart) | Keyword matching | Prototyping, testing |
| `VertexAiMemoryBankService` | Yes (Agent Platform) | Semantic search | Production, LLM-extracted memories |
| `VertexAiRagMemoryService` | Yes (Knowledge Engine) | Vector similarity | RAG pipelines, transcript search |

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

agent = LlmAgent(
    name="memory_agent", model="gemini-3-flash-preview",
    tools=[PreloadMemoryTool()],
)
```

**LoadMemory** — agent decides when to retrieve memories:

```python
from google.adk.tools import load_memory

agent = LlmAgent(
    name="memory_agent", model="gemini-3-flash-preview",
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
async def auto_save_to_memory(callback_context):
    await callback_context.add_session_to_memory()

agent = LlmAgent(
    name="agent", model="gemini-3-flash-preview",
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
| `GcsArtifactService` | Google Cloud Storage | Yes | Production |

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

# In a tool:
def save_report(filename: str, tool_context: ToolContext) -> str:
    pdf_bytes = generate_pdf()
    artifact = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
    version = tool_context.save_artifact(filename, artifact)
    return f"Saved {filename} (version {version})"

def load_latest_report(filename: str, tool_context: ToolContext) -> dict:
    artifact = tool_context.load_artifact(filename)  # Latest version
    # artifact = tool_context.load_artifact(filename, version=2)  # Specific version
    if artifact is None:
        return {"error": f"{filename} not found"}
    return {"mime_type": artifact.inline_data.mime_type, "size": len(artifact.inline_data.data)}

def list_files(tool_context: ToolContext) -> list[str]:
    return tool_context.list_artifacts()
```

### Namespacing

- **Session scope** (default): `"report.pdf"` — tied to `app_name + user_id + session_id`
- **User scope**: `"user:profile.png"` — accessible across all sessions for that user

```python
# Session-scoped
tool_context.save_artifact("summary.txt", artifact)

# User-scoped (accessible from any session for this user)
tool_context.save_artifact("user:settings.json", artifact)
```

### LoadArtifactsTool

Built-in tool that lets the LLM decide which artifacts to load before answering:

```python
from google.adk.tools.load_artifacts_tool import LoadArtifactsTool

agent = LlmAgent(
    name="artifact_reader", model="gemini-3-flash-preview",
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
