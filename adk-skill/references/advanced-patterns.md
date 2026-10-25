# ADK Advanced Patterns

Python API target: **google-adk 2.13.0**. Composition fragments below assume the named application agents and tools already exist.

## Multi-Agent Architecture Patterns

### Hierarchical Workflow

Template composition fragment for existing agents. Define `publish_email`, `post_to_slack`, `message_enhancer`, and `summary_agent` in your application:

```python
from google.adk.agents import Agent, SequentialAgent, ParallelAgent

# Level 3: Leaf agents
email_drafter = Agent(
    name="email_drafter",
    model="gemini-flash-latest",
    instruction="Draft an email announcement based on the message in state.",
    output_key="email_draft",
)

email_publisher = Agent(
    name="email_publisher",
    model="gemini-flash-latest",
    instruction="Review and publish the email draft.",
    tools=[publish_email],
)

slack_drafter = Agent(
    name="slack_drafter",
    model="gemini-flash-latest",
    instruction="Draft a Slack message based on the announcement.",
    output_key="slack_draft",
)

slack_publisher = Agent(
    name="slack_publisher",
    model="gemini-flash-latest",
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
from google.adk.agents import Agent, LlmAgent, ParallelAgent, SequentialAgent

creative_writer = LlmAgent(
    name="creative_writer",
    model="gemini-flash-latest",
    instruction="Write a creative, imaginative version.",
    output_key="creative_candidate",
)

focused_writer = LlmAgent(
    name="focused_writer",
    model="gemini-flash-latest",
    instruction="Write a precise, factual version.",
    output_key="focused_candidate",
)

judge = Agent(
    name="judge",
    model="gemini-flash-latest",
    instruction="""Compare these candidates:
    Creative: {creative_candidate}
    Focused: {focused_candidate}
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
    model="gemini-flash-latest",
    instruction="""You are a customer service router.
    - For billing questions, transfer to billing_agent
    - For technical issues, transfer to tech_support_agent
    - For general inquiries, handle directly""",
    sub_agents=[billing_agent, tech_support_agent],
)
```

Chat-mode delegation uses `transfer_to_agent`; the sub-agent handles the conversation and can transfer back. Task/single-turn modes instead expose framework delegation tools. In 2.9+ transfer reasons help diagnose handoff loops.

---

## Callback Patterns

### Rate Limiting

This callback limits calls within one session. Concurrent sessions and replicas need a shared limiter at the service boundary. The wait is asynchronous so it does not block unrelated runs.

```python
import asyncio
import time
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest

async def rate_limit_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    quota, window = 15, 60.0
    now = time.time()
    start = callback_context.state.get("rate_window_start", now)
    count = callback_context.state.get("rate_request_count", 0)
    if now - start >= window:
        start, count = now, 0
    if count >= quota:
        await asyncio.sleep(max(0.0, window - (now - start)))
        start, count = time.time(), 0
    callback_context.state["rate_window_start"] = start
    callback_context.state["rate_request_count"] = count + 1
```

### Input Validation

```python
from google.adk.tools import BaseTool, ToolContext

def validate_before_tool(
    tool: BaseTool, args: dict, tool_context: ToolContext
) -> dict | None:
    """Validate tool inputs, return dict to skip execution."""

    # Validate customer ID format
    if "customer_id" in args:
        if not isinstance(args["customer_id"], str) or not args["customer_id"].startswith("CUST-"):
            return {"error": "Invalid customer ID format. Expected CUST-XXXX."}

    return None  # Proceed with tool execution
```

### State Initialization

```python
import uuid
from datetime import datetime, timezone
from google.adk.agents.callback_context import CallbackContext

def init_session(callback_context: CallbackContext):
    """Initialize session state before agent starts."""
    callback_context.state.setdefault("session_id", str(uuid.uuid4()))
    callback_context.state.setdefault("started_at", datetime.now(timezone.utc).isoformat())
    callback_context.state.setdefault("turn_count", 0)
    callback_context.state["turn_count"] += 1
```

---

## Safety and Guardrails

### Before-Model Guardrail

Application fragment: provide a deterministic `is_unsafe(text)` policy function. A model callback returns `LlmResponse`; an agent callback returns `types.Content`.

```python
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types

def content_safety_check(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    if not llm_request.contents:
        return None
    last_msg = llm_request.contents[-1]
    text = " ".join(part.text for part in last_msg.parts or [] if part.text)
    if last_msg.role == "user" and is_unsafe(text):
        return LlmResponse(content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="Please rephrase this request.")],
        ))
    return None
```

### Plugin-Based Safety

`ModelArmorPlugin` (2.8+) can screen prompts and responses with a configured Google Cloud Model Armor template. Configure its project, location, template IDs, credentials, and policy deliberately; it is not a local zero-configuration judge. `ToolCallIntegrityPlugin` (2.11+) adds checks around tool-call/response pairing; it does not authorize tool actions. Use tool confirmations and application authorization for external writes.

A returning `after_tool_callback` can replace the result passed to the model, including with an empty dictionary. In 2.12+ use this to screen tool output before model consumption; plugin and agent callback precedence still applies.

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
    my_agent
```

### Vertex AI Agent Engine

```python
from google.adk.agents import Agent
from google.adk.sessions import VertexAiSessionService

agent = Agent(
    name="production_agent",
    model="gemini-flash-latest",
    instruction="...",
)

# Use Vertex AI for session management
session_service = VertexAiSessionService(
    project="my-project",
    location="us-central1",
)
```

Deploy the agent directory with a dedicated runtime identity (2.12+):

```bash
adk deploy agent_engine --project=my-project --region=us-central1 \
    --service_account="$RUNTIME_SERVICE_ACCOUNT" my_agent
```

Cloud deployments accept repeatable `--extra_packages` local file/directory paths (2.13). Avoid local package names that shadow installed dependencies. In 2.12 the Agent Platform integration moved to the 2.2 SDK surface (`agentplatform`); migrate direct `vertexai.preview` RAG/example-store imports using the installed SDK, rather than mixing old and new clients. Session TTL/expiration remains backend-specific.

### GKE

Containerize the FastAPI app (or the Go launcher binary) and deploy with `kubectl`. Requires a GKE cluster; supports Agent Platform or AI Studio via `GOOGLE_GENAI_USE_ENTERPRISE`. See https://adk.dev/deploy/gke/.

### API Server (FastAPI Integration)

Endpoint fragment for an existing `root_agent` and session. In a real service derive `user_id` from authenticated identity and create/authorize the session before invoking the runner.

```python
from fastapi import FastAPI
from google.adk.runners import InMemoryRunner
from google.genai import types

app = FastAPI()
runner = InMemoryRunner(agent=root_agent, app_name="api")

@app.post("/chat")
async def chat(message: str, session_id: str):
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=message)],
    )
    response_parts = []
    async for event in runner.run_async(
        user_id="api_user",
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            response_parts.extend(
                part.text for part in event.content.parts or []
                if part.text and not part.thought
            )
    return {"response": "\n".join(response_parts)}
```

---

## Project Configuration

### pyproject.toml

```toml
[project]
name = "my-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["google-adk==2.13.0"]

[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"
```

### Environment-Based Config

This optional example requires `pydantic-settings`. Provider credentials remain in the environment read by the selected model SDK.

```python
from google.adk.agents import Agent
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGENT_",
    )

    model: str = "gemini-flash-latest"

config = Config()

root_agent = Agent(
    name="configurable_agent",
    model=config.model,
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
        overlap_size=1,         # Overlap by 1 invocation
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

summarizer = LlmEventSummarizer(llm=Gemini(model="gemini-flash-latest"))
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

Completed checkpoints can be replayed; failed nodes run again on resume (2.9+). An external action completed before a crash may therefore execute again. Use an application idempotency key or deduplication record for writes; resumability does not provide exactly-once external side effects. Task-mode graph nodes also support state-based resumption.

### Context Caching

Cut cost/latency on long, stable prefixes by caching context at the App level (all agents in the app share the setting):

```python
from google.adk.apps.app import App
from google.adk.agents.context_cache_config import ContextCacheConfig

app = App(
    name="my-caching-agent-app",
    root_agent=root_agent,
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,    # Minimum tokens to trigger caching (default 0)
        ttl_seconds=600,    # Cache lifetime in seconds (default 1800)
        cache_intervals=5,  # Max uses before refresh (default 10)
    ),
)
```

If cache creation times out or fails, requests proceed uncached. ADK warns when agent transfer runs without a cache config (2.7+).

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
import logging
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import InMemoryRunner

log = logging.getLogger(__name__)

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
| `before_agent_callback` / `after_agent_callback` | Agent lifecycle | Skip agent / add output |
| `before_model_callback` / `after_model_callback` | LLM call | Yes (cached response) / Yes |
| `on_model_error_callback` | LLM error | Yes (fallback response) |
| `before_tool_callback` / `after_tool_callback` | Tool execution | Yes / Yes |
| `on_tool_error_callback` | Tool error | Yes (fallback dict) |
| `on_agent_error_callback` | Agent invocation error (2.5+) | — |
| `on_run_error_callback` | Run-level error (2.5+) | — |
| `on_event_callback` | Event yielded | Yes (replace event) |
| `after_run_callback` | Runner finishes | No (teardown only) |

### Prebuilt Plugins

- **Reflect and Retry**: Auto-retries failed tools; `ReflectAndRetryModelPlugin` (2.6+) self-heals model errors by reflecting on the failure and retrying
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
        model="gemini-flash-latest",
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

## Managed Agents (Preview, 2.4+)

`ManagedAgent` delegates to Google-hosted agent builds via the Managed Agents API instead of running the model loop yourself:

```python
import os
from google.adk.agents import ManagedAgent
from google.adk.tools import google_search

agent = ManagedAgent(
    name="my_managed_agent",
    agent_id=os.environ["MANAGED_AGENT_ID"],  # Gemini API or Agent Platform backend
    instruction="You are a helpful research assistant.",  # forwarded as system_instruction (2.6+)
    tools=[google_search],
)
```

Behavior notes:
- `mode="single_turn"` supported since 2.5; single_turn non-LlmAgent sub-agents are wrapped as inline tools.
- Remote MCP servers work with runtime header callbacks (2.5+).
- Sessions stay local; execution state lives remotely — see https://adk.dev/agents/managed-agents/.

---

## Ambient Agents (1.29+)

Run agents without a user in the loop: events from Pub/Sub push or Eventarc trigger runs over HTTP.

```bash
# /run endpoint (manual event posting)
adk api_server --auto_create_session path/to/agent

# Trigger endpoints for event sources
adk api_server --trigger_sources "pubsub,eventarc" path/to/agent
```

```bash
curl -X POST http://localhost:8000/apps/my_agent/trigger/pubsub \
  -H "Content-Type: application/json" \
  -d '{"message": {"data": "<base64 json>", "attributes": {"source": "orders-service"}}}'
```

Trigger endpoints parse the source format, decode base64 payloads, auto-create a session per event, run the agent with the decoded event as the user message, and return 200/500 so the source can retry on failure. See https://adk.dev/runtime/ambient-agents/.

---

## Multi-Model Support

ADK supports non-Gemini models via adapters:

| Provider | Model Config | Notes |
|----------|-------------|-------|
| Gemini (default: `gemini-3.5-flash`) | `model="gemini-flash-latest"` | Full feature support; OCI GenAI also available (2.6+) |
| Claude (Anthropic) | Claude model ID or `Claude` instance | Anthropic SDK; `[extensions]` extra |
| Ollama | `LiteLlm(model="ollama_chat/<installed-model>")` | Local Ollama server; `[extensions]` extra |
| LiteLLM | `LiteLlm(model="openai/<model-id>")` | Provider-prefixed IDs; `[extensions]` extra |
| vLLM | Custom adapter | Self-hosted models |
| OpenAI | `OpenAILlm` / `OpenAIResponsesLlm` | `google.adk.integrations.openai`; `[openai]` extra (2.10+) |

Select a model ID offered by your provider. Install the provider extra and configure its credentials before invocation; Gemini's ADK default remains `gemini-3.5-flash`, which does not guarantee availability at every endpoint.

```python
import os
from google.adk.agents import Agent
from google.adk.integrations.openai import OpenAILlm

agent = Agent(
    name="openai_agent",
    model=OpenAILlm(model=os.environ["OPENAI_MODEL"]),
    instruction="Answer the user's request.",
)
```

Set `OPENAI_API_KEY` for the SDK. `api_key` and `base_url` may be set per model; `api_key` also accepts a per-request sync/async callable for rotating credentials. Prefer `integrations.openai` over the compatibility re-exports under `labs.openai`. Use `OpenAIGenerateContentConfig.effort` for reasoning effort: `OpenAIResponsesLlm` warns and ignores Gemini `thinking_config` settings (2.10+).

---

## Live Voice Integrations (Experimental)

Use public imports under `google.adk.live`; legacy live-audio modules under `google.adk.flows.llm_flows` are deprecated (2.10+). These integrations use the live runner contract; they do not make graph workflows support Live streaming.

- **LiveKit** (2.9+): `google.adk.integrations.livekit.LiveKitRunner` bridges an existing ADK `Runner` and connected `rtc.Room` to WebRTC/SIP transport. Install `google-adk[livekit]`; supply LiveKit credentials and ADK user/session IDs. It is a transport bridge, not a separate agent framework.
- **CascadeLive** (2.12+, expanded in 2.13): compose speech recognition, a text reasoner, and speech synthesis. `GeminiSTT` and `GeminiTTS` provide Gemini transforms without a separate speech-provider extra. Barge-in cancels pending audio generation and truncates history to speech already delivered; clients must stop playback when interrupted and provide echo cancellation.

```python
from google.adk.agents import Agent
from google.adk.live import CascadeLive, GeminiSTT, GeminiTTS

voice_agent = Agent(
    name="voice_assistant",
    model=CascadeLive(
        model="gemini-flash-latest",
        stt=GeminiSTT(),
        tts=GeminiTTS(),
    ),
    instruction="Answer briefly for a spoken conversation.",
)
```

Connect with `Runner.run_live` and `LiveRequestQueue`, plus the appropriate live `RunConfig`. Confirm speech-model availability for the chosen endpoint. Cascading adds transcription/synthesis latency; interruptions during tool execution need integration testing. Outside live mode, `CascadeLive` delegates directly to its text model.

---

## Telemetry Migration (2.13)

The default OpenTelemetry GenAI schema is `otel_semconv_1_44` (v2). Update dashboards/exporters that expect the legacy `invocation` or `call_llm` spans: v2 uses `invoke_workflow`, removes `call_llm`, and records tool content under `gen_ai.tool.call.*`. Per-workflow data aggregates a conversation turn; per-agent data describes one agent within it.

For a temporary compatibility window, set this before starting the application:

```bash
export ADK_TELEMETRY_SCHEMA_VERSION_OPT_IN=otel_semconv_1_36
```

This pins the old format; migrate consumers before removing the override. Skill tool span names and load/script attributes have also changed, so compare exported traces rather than relying only on span counts. Configure content collection deliberately: trace payloads can contain prompts, tool data, and user files. Logging plugins in 2.13 also capture node results, terminations, and error-bearing tool results.

---

## Evaluation

For evaluation patterns, test data formats, metrics, and CI/CD integration, see the evaluation reference linked from SKILL.md. ADK 2.2+ adds `RubricBasedMultiTurnTrajectoryEvaluator` for multi-turn trajectory scoring.

## Agent Config (YAML-based Agents)

Define agents without writing Python code using YAML:

```bash
adk create --type=config my_agent
```

This generates `my_agent/root_agent.yaml`:

```yaml
name: assistant_agent
model: gemini-flash-latest
description: A helper agent that can answer users' questions.
instruction: You are an agent to help answer users' various questions.
tools:
  - name: google_search
```

Run from the parent directory: `adk web` (serves the agents directory) or `adk run my_agent`. Agent Config and tool confirmations are stable in 2.13; this does not make every optional integration stable.

Load programmatically:

```python
from google.adk.agents import config_agent_utils
agent = config_agent_utils.from_config("my_agent/root_agent.yaml")
```

The [Visual Builder](https://adk.dev/visual-builder/) in `adk web` provides a drag-and-drop UI that generates Agent Config YAML files.

---

## Anti-Patterns to Avoid

1. **Don't use global variables for state** - Use `tool_context.state` or `callback_context.state`
2. **Don't create monolithic agents** - Split into focused sub-agents
3. **Import code-based agents** - Python packages need `__init__.py`; YAML-only Agent Config projects do not
4. **Don't hardcode API keys** - Use `.env` files and environment variables
5. **Don't ignore structured output** - Use `output_schema` for data pipelines
6. **Don't nest references too deep** - Keep agent hierarchies max 3-4 levels
7. **Don't forget `root_agent`** - Must be defined at module level
8. **Don't override `_run_async_impl()` in ADK 2.0** - Use callbacks instead
9. **Don't append events directly to session** - Yield events from nodes
10. **Don't catch `BaseException` in tools** - Breaks HITL and auto-retries
11. **Don't put all prompts inline** - Extract to `prompts.py` for maintainability
12. **Don't skip testing** - Use `InMemoryRunner` for unit tests


## Tagged API Sources

- [ADK 2.13 release](https://github.com/google/adk-python/releases/tag/v2.13.0) and [2.12 release](https://github.com/google/adk-python/releases/tag/v2.12.0)
- [Live composition](https://github.com/google/adk-python/blob/v2.13.0/docs/guides/live/cascade_live/index.md) and [LiveKit](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/integrations/livekit/README.md)
- [Telemetry schema contract](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/telemetry/_schema_version.py)
- [OpenAI integration](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/integrations/openai/README.md) and [ManagedAgent fields](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/agents/_managed_agent.py)
