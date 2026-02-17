# ADK Troubleshooting

## Project Setup Errors

### Agent Not Found / ModuleNotFoundError

**Symptom:** `adk run` fails with module not found or agent not discovered.

**Causes and fixes:**

1. **Missing `__init__.py`** -- Every ADK agent package MUST have `__init__.py` that imports the agent module:
   ```python
   # my_agent/__init__.py
   from . import agent
   ```

2. **Missing `root_agent` variable** -- The framework entry point must be a module-level variable named exactly `root_agent`:
   ```python
   # my_agent/agent.py
   root_agent = Agent(name="my_agent", ...)
   ```
   Not `agent`, not `my_agent`, not `ROOT_AGENT` (Python). Must be `root_agent`.

3. **Wrong directory structure** -- The agent package must be nested:
   ```
   my_agent/           # outer project dir
   └── my_agent/       # inner package dir (this has __init__.py)
       ├── __init__.py
       └── agent.py
   ```

### API Key / Authentication Errors

**Symptom:** `google.api_core.exceptions.PermissionDenied` or `GOOGLE_API_KEY not set`.

**Fix:** Set one of these in `.env` or environment:
```bash
# Option A: API key (simplest)
GOOGLE_API_KEY=your-key-here

# Option B: Vertex AI (production)
GOOGLE_CLOUD_PROJECT=my-project
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

### Import Errors After pip install

**Symptom:** `ImportError: cannot import name 'Agent' from 'google.adk'`

**Fixes:**
- Ensure Python 3.10+: `python --version`
- Install with correct extras: `pip install google-adk` (base) or `pip install google-adk[a2a]` (A2A support)
- Check for conflicting google packages: `pip list | grep google`

---

## Runtime Errors

### Agent Returns Empty / No Response

**Causes:**
1. **Missing `instruction`** -- Agent has no system prompt. Add `instruction="..."` to agent definition.
2. **`output_schema` mismatch** -- If using structured output, ensure the model can produce valid JSON matching your Pydantic model.
3. **Tool errors swallowed** -- Check tool functions for exceptions. Add logging to tool functions.

### State Not Shared Between Agents

**Symptom:** Agent B cannot read data written by Agent A.

**Fixes:**
1. Use `output_key` on Agent A so its output is written to `state["key"]`.
2. Agent B reads via `state['key']` in its instruction or tool.
3. Both agents must be sub-agents of the same parent (SequentialAgent, ParallelAgent, etc.) to share state scope.
4. Verify scope prefix: `state["key"]` is session-scoped. Use `app:key` for app-wide, `user:key` for user-wide.

### LoopAgent Runs Forever

**Symptom:** Agent never terminates, runs indefinitely.

**Fixes:**
1. Always set `max_iterations` on LoopAgent as a safety bound.
2. If using a checker agent, verify `tool_context.actions.escalate = True` is called when done.
3. Check that the escalation tool is actually invoked by the checker (add logging).

### Callback Returns Wrong Type

**Symptom:** Callback doesn't intercept or causes unexpected behavior.

**Rules:**
- `before_tool_callback`: Return `None` to proceed, return `dict` to skip tool with that response.
- `before_model_callback`: Return `None` to proceed, return `types.Content` to skip model call.
- `before_agent_callback`: Return `None` to proceed, return `types.Content` to skip agent entirely.

---

## A2A (Agent-to-Agent) Errors

### A2A Dependencies Missing

**Symptom:** `ImportError` when using `to_a2a()` or `RemoteA2aAgent`.

**Fix:** Install with A2A extras:
```bash
pip install google-adk[a2a]
```
The base `google-adk` package does not include A2A dependencies (httpx, a2a-sdk, etc.).

### A2A Connection Refused

**Symptom:** `RemoteA2aAgent` fails to connect to remote agent.

**Checklist:**
1. Remote agent server is running (`adk api_server` or `to_a2a()` app started)
2. Agent card URL is correct (default: `http://localhost:8000/.well-known/agent.json`)
3. No firewall blocking the port
4. Remote agent's `root_agent` is properly defined

### Async Event Loop Errors in A2A Tests

**Symptom:** `RuntimeError: Event loop is closed` in pytest.

**Fix:** Run all A2A async operations in a single `asyncio.run()` call. Do not create multiple event loops:
```python
# WRONG -- breaks httpx
async def test_a2a():
    ...  # This creates/closes event loop per test

# CORRECT -- single event loop
def test_a2a():
    asyncio.run(run_all_a2a_tests())
```

---

## MCP Integration Errors

### MCP Tool Not Available

**Symptom:** Agent cannot find MCP tools.

**Checklist:**
1. MCP server command is correct in `StdioServerParameters`
2. The MCP server binary/package is installed (e.g., `npx` can find it)
3. Tool names in skill instructions match MCP server's registered tool names (case-sensitive)

### MCP Connection Timeout

**Symptom:** Agent hangs or times out when calling MCP tools.

**Fixes:**
- Verify MCP server starts independently: run the command from `StdioServerParameters` manually
- Check for missing environment variables the MCP server needs
- Use `SseConnectionParams` instead of `StdioConnectionParams` for remote MCP servers

---

## Testing Errors

### InMemoryRunner Test Fails

**Symptom:** Tests pass locally but assertions fail on event content.

**Tips:**
1. Always check the last event for final response: `events[-1].content.parts[0].text`
2. Use `event.author` to filter events by agent name
3. For multi-agent tests, collect all events and filter by author
4. Use `@pytest.mark.asyncio` and `async def test_*` for async runner tests
5. Create a fresh session per test to avoid state leakage:
   ```python
   session = await runner.session_service.create_session(
       user_id="test_user", app_name="test",
   )
   ```

---

## Performance Tips

- Use `gemini-2.5-flash` for most agents, reserve `gemini-2.5-pro` for complex reasoning
- Set `temperature=0.1-0.4` for deterministic tasks, `0.7-0.9` for creative tasks
- Split agents with 5+ tools into focused specialists
- Use `output_schema` (Pydantic) between pipeline stages for reliable data passing
- Keep agent hierarchies max 3-4 levels deep
