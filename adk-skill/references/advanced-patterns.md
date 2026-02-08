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

## Configuration Patterns

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

## Evaluation

### Built-in Evaluation

```bash
adk eval my_agent tests/eval_data.json
```

### Eval Data Format

```json
[
    {
        "query": "What is the weather in Paris?",
        "expected_tool_use": ["get_weather"],
        "expected_intermediate_agent_responses": [
            {"agent": "weather_agent", "contains": "Paris"}
        ],
        "reference": "The weather in Paris is..."
    }
]
```

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
