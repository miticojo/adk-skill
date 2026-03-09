# ADK Advanced Patterns

## Multi-Agent Architecture Patterns

### Hierarchical Workflow

Nest agents for complex multi-step workflows with branching:

```python
from google.adk.agents import Agent, SequentialAgent, ParallelAgent

# Level 3: Leaf agents
email_drafter = Agent(
    name="email_drafter",
    model="gemini-2.5-flash",
    instruction="Draft an email announcement based on the message in state.",
    output_key="email_draft",
)

email_publisher = Agent(
    name="email_publisher",
    model="gemini-2.5-flash",
    instruction="Review and publish the email draft.",
    tools=[publish_email],
)

slack_drafter = Agent(
    name="slack_drafter",
    model="gemini-2.5-flash",
    instruction="Draft a Slack message based on the announcement.",
    output_key="slack_draft",
)

slack_publisher = Agent(
    name="slack_publisher",
    model="gemini-2.5-flash",
    instruction="Post the Slack message.",
    tools=[post_to_slack],
)

# Level 2: Channel pipelines
email_pipeline = SequentialAgent(
    name="email_pipeline",
    sub_agents=[email_drafter, email_publisher],
)

slack_pipeline = SequentialAgent(
    name="slack_pipeline",
    sub_agents=[slack_drafter, slack_publisher],
)

# Level 1: Broadcast
broadcast = ParallelAgent(
    name="broadcast",
    sub_agents=[email_pipeline, slack_pipeline],
)

# Root: Full workflow
root_agent = SequentialAgent(
    name="announcement_workflow",
    sub_agents=[
        message_enhancer,  # Enhance with search
        broadcast,         # Send to channels
        summary_agent,     # Summarize results
    ],
)
```

### Creative Pipeline (Parallel Writers + Judge)

Generate multiple candidates in parallel and select the best:

```python
from google.genai import types

creative_writer = LlmAgent(
    name="creative_writer",
    model="gemini-2.5-pro",
    generate_content_config=types.GenerateContentConfig(temperature=0.9),
    instruction="Write a creative, imaginative version.",
    output_key="creative_candidate",
)

focused_writer = LlmAgent(
    name="focused_writer",
    model="gemini-2.5-pro",
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    instruction="Write a precise, factual version.",
    output_key="focused_candidate",
)

judge = Agent(
    name="judge",
    model="gemini-2.5-pro",
    instruction="""Compare the creative_candidate and focused_candidate.
    Select the best one and explain why.""",
    output_key="final_selection",
)

root_agent = SequentialAgent(
    name="best_of_n",
    sub_agents=[
        ParallelAgent(
            name="parallel_writers",
            sub_agents=[creative_writer, focused_writer],
        ),
        judge,
    ],
)
```

### Agent Transfer (Sub-Agent Routing)

Let the LLM decide which sub-agent to delegate to:

```python
root_agent = Agent(
    name="router",
    model="gemini-2.5-flash",
    instruction="""You are a customer service router.
    - For billing questions, transfer to billing_agent
    - For technical issues, transfer to tech_support_agent
    - For general inquiries, handle directly""",
    sub_agents=[billing_agent, tech_support_agent],
)
```

The model can transfer control by calling a sub-agent by name. The sub-agent handles the conversation and can transfer back.

---

## Callback Patterns

### Rate Limiting

```python
import time

RPM_QUOTA = 15
RATE_LIMIT_SECS = 60

def rate_limit_callback(callback_context: CallbackContext, llm_request: LlmRequest):
    now = time.time()
    if "timer_start" not in callback_context.state:
        callback_context.state["timer_start"] = now
        callback_context.state["request_count"] = 1
        return

    count = callback_context.state["request_count"] + 1
    elapsed = now - callback_context.state["timer_start"]

    if count > RPM_QUOTA:
        delay = RATE_LIMIT_SECS - elapsed + 1
        if delay > 0:
            time.sleep(delay)
        callback_context.state["timer_start"] = now
        callback_context.state["request_count"] = 1
    else:
        callback_context.state["request_count"] = count
```

### Input Validation

```python
def validate_before_tool(
    tool: BaseTool, args: dict, tool_context: CallbackContext
) -> dict | None:
    """Validate tool inputs, return dict to skip execution."""

    # Validate customer ID format
    if "customer_id" in args:
        if not args["customer_id"].startswith("CUST-"):
            return {"error": "Invalid customer ID format. Expected CUST-XXXX."}

    # Auto-approve small discounts
    if tool.name == "approve_discount":
        if args.get("value", 0) <= 10:
            return {"status": "auto_approved", "value": args["value"]}

    return None  # Proceed with tool execution
```

### State Initialization

```python
import uuid
from datetime import datetime

def init_session(callback_context: CallbackContext):
    """Initialize session state before agent starts."""
    callback_context.state.setdefault("session_id", str(uuid.uuid4()))
    callback_context.state.setdefault("started_at", datetime.now().isoformat())
    callback_context.state.setdefault("turn_count", 0)
    callback_context.state["turn_count"] += 1
```

---

## Safety and Guardrails

### Before-Model Guardrail

```python
from google.genai import types

def content_safety_check(callback_context: CallbackContext, llm_request: LlmRequest):
    """Block unsafe requests before they reach the model."""
    if not llm_request.contents:
        return None

    last_msg = llm_request.contents[-1]
    if last_msg.role == "user":
        text = last_msg.parts[0].text if last_msg.parts else ""
        if is_unsafe(text):
            return types.Content(
                role="model",
                parts=[types.Part.from_text(
                    "I cannot process this request. Please rephrase."
                )],
            )
    return None
```

### Plugin-Based Safety

```python
from google.adk.agents.plugins import LlmAsAJudge
from google.adk.runners import InMemoryRunner

runner = InMemoryRunner(
    agent=root_agent,
    app_name="safe_app",
    plugins=[LlmAsAJudge()],
)
```

---

## Deployment

### Local (adk CLI)

```bash
adk run my_agent          # Interactive terminal
adk web my_agent          # Web UI on localhost
```

### Cloud Run

```bash
adk deploy cloud_run \
    --project=my-project \
    --region=us-central1 \
    --service_name=my-agent \
    --app_name=my_agent \
    --agent_module=my_agent.agent
```

### Vertex AI Agent Engine

```python
from google.adk.agents import Agent
from google.adk.sessions import VertexAiSessionService

agent = Agent(
    name="production_agent",
    model="gemini-2.5-flash",
    instruction="...",
)

# Use Vertex AI for session management
session_service = VertexAiSessionService(
    project="my-project",
    location="us-central1",
)
```

### API Server (FastAPI Integration)

```python
from fastapi import FastAPI
from google.adk.runners import InMemoryRunner

app = FastAPI()
runner = InMemoryRunner(agent=root_agent, app_name="api")

@app.post("/chat")
async def chat(message: str, session_id: str):
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    )
    events = []
    async for event in runner.run_async(
        user_id="api_user",
        session_id=session_id,
        new_message=content,
    ):
        events.append(event)
    return {"response": events[-1].content.parts[0].text}
```

---

## Project Configuration

### pyproject.toml

```toml
[project]
name = "my-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["google-adk"]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
```

### Environment-Based Config

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT_",
    )

    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    google_api_key: str = ""
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"

config = Config()

root_agent = Agent(
    name="configurable_agent",
    model=config.model,
    generate_content_config=types.GenerateContentConfig(
        temperature=config.temperature,
    ),
)
```

### .env File

```bash
GOOGLE_API_KEY=your-api-key
# OR for Vertex AI:
GOOGLE_CLOUD_PROJECT=my-project
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE
```

---

## App Object (Runtime Configuration)

The `App` class wraps your `root_agent` with runtime configuration for context compaction, resumability, and plugins:

```python
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.apps.app import ResumabilityConfig

app = App(
    name='my-agent',
    root_agent=root_agent,
    # Context compaction: summarize older events to keep context small
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,  # Compact every 3 invocations
        overlap_size=1,         # Keep 1 prior event in new window
    ),
    # Resumability: recover from interruptions
    resumability_config=ResumabilityConfig(
        is_resumable=True,
    ),
)
```

### Custom Summarizer for Compaction

```python
from google.adk.apps.llm_event_summarizer import LlmEventSummarizer
from google.adk.models import Gemini

summarizer = LlmEventSummarizer(llm=Gemini(model="gemini-2.5-flash"))
app = App(
    name='my-agent',
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1,
        summarizer=summarizer,
    ),
)
```

### How Resumability Works

When enabled, ADK tracks workflow execution via Events. On interruption and restart:
- **SequentialAgent**: Resumes from `current_sub_agent` state
- **LoopAgent**: Continues from saved `current_sub_agent` + `times_looped`
- **ParallelAgent**: Runs only sub-agents that haven't completed

Tools that completed successfully are NOT re-run. Tools run at-least-once, so idempotency matters.

---

## Session Rewind

Undo interactions and restore session state to a previous point (v1.17.0+):

```python
runner = InMemoryRunner(agent=root_agent, app_name="test")
session = await runner.session_service.create_session(
    app_name="test", user_id="user",
)

# Run some interactions...
events = await call_agent(runner, "user", session.id, "set color to blue")
rewind_id = events[0].invocation_id

# Rewind: undo "set color to blue" and all interactions after it
await runner.rewind_async(
    user_id="user",
    session_id=session.id,
    rewind_before_invocation_id=rewind_id,
)
```

**Limitations:**
- Only session-level state/artifacts are restored (not `app:` or `user:` scoped)
- External side effects (API calls, emails) are NOT undone
- Do not rewind active sessions or manipulate artifacts during rewind

---

## Plugins (Global Lifecycle Hooks)

Plugins extend `BasePlugin` and apply globally across all agents, tools, and LLM calls in a `Runner`:

```python
from google.adk.plugins.base_plugin import BasePlugin

class MetricsPlugin(BasePlugin):
    def __init__(self):
        super().__init__(name="metrics")
        self.llm_calls = 0

    async def before_model_callback(self, *, callback_context, llm_request):
        self.llm_calls += 1
        return None  # None = proceed, return value = short-circuit

    async def on_model_error_callback(self, *, callback_context, llm_request, error):
        log.error(f"Model failed: {error}")
        return None  # None = re-raise, return LlmResponse = suppress error

# Register on Runner
runner = InMemoryRunner(
    agent=root_agent,
    app_name="app",
    plugins=[MetricsPlugin()],
)
```

### Plugin vs Agent Callbacks

| | Plugins | Agent Callbacks |
|---|---------|----------------|
| Scope | Global (all agents/tools/LLMs) | Local (single agent) |
| Priority | Run BEFORE agent callbacks | Run AFTER plugin callbacks |
| Use case | Logging, policy, monitoring, caching | Agent-specific logic |

### Available Callback Hooks

| Hook | When | Can Short-Circuit |
|------|------|-------------------|
| `on_user_message_callback` | User sends message | Yes (replace message) |
| `before_run_callback` | Runner starts | Yes |
| `before_agent_callback` / `after_agent_callback` | Agent lifecycle | Yes / No |
| `before_model_callback` / `after_model_callback` | LLM call | Yes (cached response) / Yes |
| `on_model_error_callback` | LLM error | Yes (fallback response) |
| `before_tool_callback` / `after_tool_callback` | Tool execution | Yes / Yes |
| `on_tool_error_callback` | Tool error | Yes (fallback dict) |
| `on_event_callback` | Event yielded | Yes (replace event) |
| `after_run_callback` | Runner finishes | No (teardown only) |

### Prebuilt Plugins

- **Reflect and Retry**: Auto-retries failed tools
- **BigQuery Analytics**: Agent logging to BigQuery
- **Context Filter**: Reduces context size
- **Global Instruction**: App-level instructions
- **Save Files as Artifacts**: Saves user-uploaded files
- **Logging**: Logs at each callback point

---

## AG-UI Integration (Rich User Interfaces)

[AG-UI](https://docs.ag-ui.com/) is an open protocol for building rich UIs on top of ADK agents. It handles streaming events, shared state, and bidirectional communication.

### Quick Start with CopilotKit

```bash
npx copilotkit@latest create -f adk
export GOOGLE_API_KEY="your-key"
npm install && npm run dev
```

This starts a web UI at `http://localhost:3000` and ADK backend at `http://localhost:8000`.

### Key AG-UI Features

| Feature | Description |
|---------|-------------|
| Chat | Streaming messages between users and agents |
| Generative UI | Render tool calls as custom React components |
| Shared State | Sync agent state with UI bidirectionally |
| Human-in-the-Loop | User confirmations for critical actions |
| Frontend Actions | UI-triggered agent actions |

```tsx
// Shared state example (CopilotKit + ADK)
const { state, setState } = useCoAgent({
  name: "my_agent",
  initialState: { items: [] },
});
```

---

## Interactions API (Stateful Gemini Conversations)

For long conversations, use the Interactions API to chain requests by ID instead of sending full history (v1.21.0+):

```python
from google.adk.models.google_llm import Gemini

root_agent = Agent(
    model=Gemini(
        model="gemini-2.5-flash",
        use_interactions_api=True,
    ),
    name="stateful_agent",
    tools=[get_weather],
)
```

**Limitation:** Cannot mix custom function tools with built-in tools (like Google Search). Workaround:
```python
from google.adk.tools.google_search_tool import GoogleSearchTool
# Convert built-in to function tool
tools=[GoogleSearchTool(bypass_multi_tools_limit=True), custom_tool]
```

---

## Multi-Model Support

ADK supports non-Gemini models via adapters:

| Provider | Model Config | Notes |
|----------|-------------|-------|
| Gemini (default) | `model="gemini-2.5-flash"` | Full feature support |
| Claude (Anthropic) | `model="claude-sonnet-4-20250514"` | Via google-genai |
| Ollama | `model="ollama/llama3"` | Local models |
| LiteLLM | `model="litellm/gpt-4o"` | Multi-provider proxy |
| vLLM | Custom adapter | Self-hosted models |

```python
# Claude example
agent = Agent(
    model="claude-sonnet-4-20250514",
    name="claude_agent",
    instruction="...",
)

# Ollama example
from google.adk.models.ollama_llm import OllamaLlm
agent = Agent(
    model=OllamaLlm(model="gemma3"),
    name="local_agent",
    instruction="...",
)
```

---

## Evaluation

For evaluation patterns, test data formats, metrics, and CI/CD integration, see [evaluation.md](evaluation.md).

---

## Anti-Patterns to Avoid

1. **Don't use global variables for state** - Use `tool_context.state` or `callback_context.state`
2. **Don't create monolithic agents** - Split into focused sub-agents
3. **Don't skip `__init__.py`** - ADK won't find your agent without it
4. **Don't hardcode API keys** - Use `.env` files and environment variables
5. **Don't ignore structured output** - Use `output_schema` for data pipelines
6. **Don't nest references too deep** - Keep agent hierarchies max 3-4 levels
7. **Don't forget `root_agent`** - Must be defined at module level
8. **Don't use Agent when SequentialAgent is needed** - If steps must run in order, use SequentialAgent
9. **Don't put all prompts inline** - Extract to `prompts.py` for maintainability
10. **Don't skip testing** - Use `InMemoryRunner` for unit tests
