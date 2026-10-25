---
name: adk-skill
description: "Builds and migrates Google ADK agents in Python, Java, Go, Kotlin and TypeScript. Use for ADK workflows, tools, MCP/A2A, memory, artifacts, evaluation or deployment. Excludes standalone Gemini API tasks and LangChain, CrewAI or AutoGen projects."
license: MIT
compatibility: "Python examples verified with google-adk 2.13.0 and Python 3.11+. Other SDKs: Java 17+, Go 1.26.6+ for ADK v2.6, Node 24+. Requires Gemini API credentials or configured Google Cloud authentication for model calls. Optional integrations require package extras. Older ADK versions may lack the APIs shown here."
metadata:
  author: Giorgio <miticojo@gmail.com>
  version: "2.2.0"
  mcp-server: adk-docs
---

# Google Agent Development Kit (ADK) Guide

## Overview

ADK is Google's open-source framework for building model-agnostic AI agents. This guide targets Python **2.13.0**. Its **Workflow Runtime** composes agents, tools and functions into graphs, with memory, artifacts, callbacks and deployment support. Verify the target SDK's versioned API before using examples; named application agents/tools in composition fragments must be supplied by the application.

## Critical Rules

1. **Entry point is `root_agent`** — a module-level variable in `agent.py`, or a `Workflow` object for graph-based agents.
2. **Code-based packages need `__init__.py`** importing the agent module: `from . import agent`. YAML-only agents do not.
3. **Configure credentials for model calls.** Deterministic function-only workflows run without them.
4. **In ADK 2.0, agents are nodes.** Do NOT override `_run_async_impl()` — use `BeforeAgentCallback` / `AfterAgentCallback` instead.
5. **Do NOT append events directly** to `context.session.events`. Yield events from your node so the framework manages persistence and routing.
6. **Never catch `BaseException` in tools** — it breaks HITL pause/resume and automatic retries.
7. **Group tools by responsibility.** Split unrelated domains when it improves routing; tool count alone does not require more agents.
8. **Use `output_key` + `output_schema`** for reliable data flow between agents — not free text.

## Documentation & Resources
- **ADK Docs**: https://adk.dev/llms.txt
- **Official Samples**: https://github.com/google/adk-samples
- **2.0 Migration Guide**: https://adk.dev/2.0/

## Supported Languages

| Language | Package | Install | ADK 2.x |
|----------|---------|---------|---------|
| Python | `google-adk` | `pip install google-adk==2.13.0` | 2.13.0 |
| Go | `google.golang.org/adk/v2` | `go get google.golang.org/adk/v2@v2.6.0` | 2.6.0 |
| Java | `com.google.adk:google-adk` | Maven/Gradle | 1.13.0; experimental graphs |
| Kotlin | `com.google.adk:google-adk-kotlin-core` | Gradle | 1.4.0; stable core, experimental graphs |
| TypeScript | `@google/adk` | `npm install @google/adk@2.3.0` | 2.3.0 |

Go and TypeScript also publish parallel 1.x LTS lines (`google.golang.org/adk` / `@google/adk@^1`).

This guide shows Python examples. For Java, Go, Kotlin, and TypeScript patterns, see [references/multi-language.md](references/multi-language.md).

## Prerequisites

Python 3.11+ with `pip install "google-adk==2.13.0"`; model calls need `GOOGLE_API_KEY` or Google Cloud authentication. Other languages: Java 17+, Go 1.26.6+ (ADK v2.6), Node 24+. Install needed extras: `[db]`, `[a2a]`, `[openai]`, `[mongodb]`, `[eval]`, `[bigquery-analytics]`; Jinja2 is optional.

## Quick Reference

| Task | ADK 2.x Approach |
|------|-----------------|
| Single agent | `LlmAgent` with model, instruction, tools |
| Graph-based workflow | `Workflow(edges=[...])` with Agent/Function nodes |
| Dynamic (code-driven) workflow | `@node` decorator + `ctx.run_node()` loops/branches |
| Collaborative team | Agent with `sub_agents` + `mode='single_turn'/'task'/'chat'` |
| Sequential pipeline | `SequentialAgent` or `Workflow` chain |
| Parallel execution | `ParallelAgent` or `asyncio.gather(ctx.run_node(...))` |
| Iterative refinement | `LoopAgent` or `while` loop in dynamic workflow |
| Agent-as-tool | `AgentTool` for on-demand delegation |
| Inline specialist with pause/resume | `sub_agents` with `mode="single_turn"` |
| Backup models / advisor | Experimental `FallbackModel` / `ModelConsultTool` |
| Google-managed agent | `ManagedAgent` (Preview, 2.4+) |
| Agent as MCP server | `agent.to_mcp_server()` (2.5+) |
| Remote agent (A2A) | `RemoteA2aAgent` + `to_a2a()` |
| Custom tools | Python functions with type hints + docstrings |
| OpenAPI tools | `OpenAPIToolset` from OpenAPI spec |
| Structured output | Pydantic model via `output_schema` + `output_key` |
| State management | `callback_context.state` and `tool_context.state` |
| Cross-session memory | `MemoryService` + `PreloadMemoryTool` / `LoadMemory` |
| Binary data persistence | `ArtifactService` (`save_artifact`, `load_artifact`) |
| MCP integration | `MCPToolset`; SDK 2.x modern wire path is opt-in |
| YAML agent config / session rewind | `adk create --type=config` / `runner.rewind_async()` |
| Streaming (Live API) | `LiveRequestQueue` for bidirectional audio/video |
| Testing | `pytest` with `InMemoryRunner` |
| Evaluation | EvalSet with `.test.json`, `adk eval` CLI |

## Project Structure

**Code-based project:**
```
my_agent/
├── my_agent/
│   ├── __init__.py          # Must import agent module
│   ├── agent.py             # Defines root_agent (entry point)
│   ├── prompts.py           # Instruction strings (optional)
│   ├── tools.py             # Custom tool functions (optional)
│   └── sub_agents/          # Sub-agent packages (optional)
├── tests/test_agent.py
├── pyproject.toml
└── .env
```

**YAML-based project:** `adk create --type=config my_agent` generates `my_agent/root_agent.yaml` + `.env`.

### Critical: __init__.py and root_agent

```python
# my_agent/__init__.py
from . import agent
```

In ADK 2.0, `root_agent` can be a `LlmAgent` or a `Workflow` object:

```python
# my_agent/agent.py
from google.adk.agents import LlmAgent

root_agent = LlmAgent(
    name="my_agent",
    # model is optional — built-in default: gemini-3.5-flash
    description="Brief description for agent discovery",
    instruction="Detailed system prompt...",
    tools=[],
)
```

## Workflow Types

ADK 2.0 offers three ways to compose multi-agent work. Template workflows from 1.x still work but are superseded.

### 1. Graph-based Workflows

Declarative graph of nodes (Agents, Functions, Tools) with explicit routing edges. Best for deterministic, structured processes.

```python
from google.adk import Workflow, Event
from google.adk.agents import LlmAgent

classifier = LlmAgent(
    name="classifier", model="gemini-flash-latest",
    instruction="Classify input as 'BUG', 'SUPPORT', or 'LOGISTICS'.",
    output_schema=str,
)

def router(node_input: str):
    routes = [r.strip() for r in node_input.split(",")]
    return Event(route=routes)

def handle_bug():    return Event(message="Handling bug...")
def handle_support(): return Event(message="Handling support...")
def handle_logistics(): return Event(message="Handling logistics...")

root_agent = Workflow(
    name="routing_workflow",
    edges=[
        ("START", classifier, router),
        (router, {"BUG": handle_bug, "SUPPORT": handle_support, "LOGISTICS": handle_logistics}),
    ],
)
```

### 2. Dynamic Workflows

Programmatic orchestration with `@node` decorators and `ctx.run_node()`. Best for complex branching or iterative logic.

```python
from google.adk import Context, Workflow
from google.adk.workflow import node

@node(name="process_item")
def process(node_input: str) -> str:
    return f"Processed: {node_input}"

@node(rerun_on_resume=True)
async def orchestrator(ctx: Context, node_input: list[str]) -> str:
    results = []
    for item in node_input:
        result = await ctx.run_node(process, item)
        results.append(result)
    return "\n".join(results)

root_agent = Workflow(
    name="dynamic_workflow",
    edges=[("START", orchestrator)],
)
```

For HITL: yield `RequestInput` from a node. See [references/workflows.md](references/workflows.md).

### 3. Collaborative Agents

Coordinator delegates to sub-agents with operating modes:

```python
from google.adk.agents import LlmAgent

weather_agent = LlmAgent(
    name="weather_checker", mode="single_turn", tools=[get_weather],
)
flight_agent = LlmAgent(
    name="flight_booker", mode="task",
    input_schema=FlightInput, output_schema=FlightResult,
    tools=[search_flights, book_flight],
)
root_agent = LlmAgent(
    name="travel_planner",  # Coordinator — auto-injects request_task_* tools
    sub_agents=[weather_agent, flight_agent],
)
```

### Collaboration Modes

Modes: `chat` (conversation until handoff), `task` (auto-return via `finish_task`, may ask for clarification), `single_turn` (no user interaction, returns result). Full table: [references/workflows.md](references/workflows.md).

Set modes on sub-agents to control delegation. Task-mode wrappers support nested delegation and resumption in 2.12+. The root is the conversation entry point.

### 4. Template Workflows (1.x Compatible)

`SequentialAgent`, `ParallelAgent`, and `LoopAgent` still work but are superseded. See [references/advanced-patterns.md](references/advanced-patterns.md).

## Tools

### Function Tools

Any Python function with type hints and a docstring becomes a tool:

```python
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city.

    Args:
        city: The city name to look up weather for.
        units: Temperature units - 'celsius' or 'fahrenheit'.
    """
    return {"temperature": 22, "conditions": "sunny", "humidity": 45}

agent = LlmAgent(
    name="weather_agent", model="gemini-flash-latest",
    instruction="Help users check the weather.", tools=[get_weather],
)
```

**Requirements:** Type hints on all parameters, docstring with description and Args, return type annotation.

### Tools with State Access

```python
from google.adk.tools import ToolContext

def add_to_cart(item: str, quantity: int, tool_context: ToolContext) -> dict:
    """Add an item to the shopping cart."""
    cart = tool_context.state.get("cart", [])
    cart.append({"item": item, "quantity": quantity})
    tool_context.state["cart"] = cart
    return {"status": "added", "cart_size": len(cart)}
```

### AgentTool

```python
from google.adk.tools.agent_tool import AgentTool

specialist = LlmAgent(
    name="code_reviewer", model="gemini-flash-latest",
    instruction="Review code for bugs and best practices.",
)
coordinator = LlmAgent(
    name="coordinator", model="gemini-flash-latest",
    instruction="Coordinate tasks. Use code_reviewer for code reviews.",
    tools=[AgentTool(agent=specialist)],
)
```

### Built-in, OpenAPI, MCP

```python
from google.adk.tools import google_search, load_memory
from google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset import OpenAPIToolset
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp import StdioServerParameters

# Built-in
agent = LlmAgent(name="researcher", tools=[google_search, load_memory])

# OpenAPI (generate tools from REST API spec)
toolset = OpenAPIToolset(spec_str=openapi_spec_json, spec_str_type="json")

# MCP
mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(command="npx", args=["-y", "some-mcp-server"]),
    ),
)
```

For tool auth, confirmations, MCP, stable `SkillToolset`, experimental skill lifecycle, script artifacts and advisor budgets, see [references/tools-reference.md](references/tools-reference.md).

---
## Memory & Artifacts

### Memory (Cross-Session)

Long-term memory persists across sessions. Agents retrieve memories with built-in tools:

```python
from google.adk.memory import InMemoryMemoryService
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.preload_memory_tool import PreloadMemoryTool

memory_service = InMemoryMemoryService()  # Prototyping (or VertexAiMemoryBankService for prod)

agent = LlmAgent(
    name="memory_agent", model="gemini-flash-latest",
    instruction="Answer questions using past conversation history.",
    tools=[PreloadMemoryTool()],
)

runner = Runner(
    agent=agent, app_name="my_app",
    session_service=InMemorySessionService(),
    memory_service=memory_service,
)
```

Backends include in-memory, SQLite, Vertex Memory Bank/RAG and experimental MongoDB. Optional mutation APIs vary by backend. See [references/memory-artifacts.md](references/memory-artifacts.md).

### Artifacts (Binary Data)

Versioned binary data (files, images, audio); continuing the runner example above:

```python
from google.adk.artifacts import InMemoryArtifactService

artifact_service = InMemoryArtifactService()  # Or GcsArtifactService

runner = Runner(
    agent=agent, app_name="my_app",
    session_service=InMemorySessionService(),
    artifact_service=artifact_service,
)
# In async tools: await tool_context.save_artifact(filename, part)
#                 await tool_context.load_artifact(filename)
#                 await tool_context.list_artifacts()
```

See [references/memory-artifacts.md](references/memory-artifacts.md).

---
## State Management

State is a shared dictionary across agents, tools, and callbacks. Scopes: `state["key"]` (session), `app:key` (app-wide), `user:key` (user-wide). Pass data between agents via `output_key` + `output_schema`. Instructions support `{var}` / `{prefix:var}` placeholders; opt-in Jinja2 templates (`use_jinja2=True`, 2.7+, optional dep) add conditionals, loops, and dotted access:

```python
from google.adk.agents import LlmAgent, SequentialAgent
from pydantic import BaseModel

class ResearchOutput(BaseModel):
    findings: list[str]

researcher = LlmAgent(name="researcher", output_key="findings", output_schema=ResearchOutput)
writer = LlmAgent(name="writer", instruction="Write a report based on {findings}.")
pipeline = SequentialAgent(name="pipeline", sub_agents=[researcher, writer])
```

---
## Callbacks

Callbacks intercept the agent lifecycle. Return `None` to proceed, return a value to short-circuit. **In ADK 2.0, use callbacks instead of overriding `_run_async_impl()`.**

| Callback | Signature | Use Case |
|----------|-----------|----------|
| `before_agent_callback` | `(CallbackContext)` | Initialize state |
| `before_tool_callback` | `(BaseTool, dict, ToolContext) -> dict\|None` | Validate inputs |
| `after_tool_callback` | `(BaseTool, dict, ToolContext, dict) -> dict\|None` | Post-process results |
| `before_model_callback` | `(CallbackContext, LlmRequest)` | Rate limit, safety |

```python
def before_tool(tool, args, tool_context) -> dict | None:
    if tool.name == "approve_discount" and args.get("value", 0) > 50:
        return {"status": "rejected", "reason": "Discount too large"}
    return None  # Proceed normally
```

---
## Structured Output

Use Pydantic models for typed, validated agent output:

```python
from pydantic import BaseModel
from google.adk.agents import LlmAgent

class AnalysisResult(BaseModel):
    summary: str
    key_findings: list[str]
    confidence: float
    recommendations: list[str]

agent = LlmAgent(
    name="analyzer", model="gemini-flash-latest",
    instruction="Analyze the provided data and return structured results.",
    output_schema=AnalysisResult,
    output_key="analysis",
)
```

## Running and Testing

```bash
pip install "google-adk==2.13.0"
export GOOGLE_API_KEY="your-key"
adk run my_agent          # Interactive CLI
adk web my_agent          # Web UI (includes Visual Builder)
adk api_server my_agent   # REST API server
adk create --type=config my_agent  # YAML-based agent
```

### Testing

```python
import pytest
from google.adk.runners import InMemoryRunner
from google.genai import types

@pytest.mark.asyncio
async def test_agent():
    runner = InMemoryRunner(agent=root_agent, app_name="test")
    session = await runner.session_service.create_session(
        user_id="test_user", app_name="test",
    )
    content = types.Content(
        role="user", parts=[types.Part.from_text(text="Hello")],
    )
    events = []
    async for event in runner.run_async(
        user_id="test_user", session_id=session.id, new_message=content,
    ):
        events.append(event)
    text = " ".join(
        part.text for event in events if event.is_final_response() and event.content
        for part in (event.content.parts or []) if part.text and not part.thought
    )
    assert "expected" in text.lower()
```

### Evaluation

Define eval cases in `.test.json` files, run with `adk eval`, `pytest`, or web UI. ADK 2.2+ adds `RubricBasedMultiTurnTrajectoryEvaluator`. See [references/evaluation.md](references/evaluation.md).

## Model Selection

The built-in default remains `gemini-3.5-flash`. `gemini-flash-latest` is a rolling alias; choose a pinned model offered by the provider/region for reproducible deployments. Provider sampling/reasoning parameters differ: inspect the selected model's supported configuration. OpenAI adapters use `google.adk.integrations.openai` and the `[openai]` extra; other provider patterns are in the advanced reference.

## Design Patterns

| Pattern | When to Use | ADK 2.0 Implementation |
|---------|------------|------------------------|
| Graph workflow | Deterministic multi-step process | `Workflow` with explicit `edges` |
| Dynamic workflow | Complex branching, iteration | `@node` + `ctx.run_node()` code |
| Collaborative team | Self-managing specialist group | Coordinator + `sub_agents` with mode |
| Fan-out / Fan-in | Independent parallel tasks | `ParallelAgent` or `asyncio.gather` |
| Reflection loop | Quality > speed | `LoopAgent` or `while` in dynamic workflow |
| Dynamic routing | Input-dependent handler selection | Router function in `Workflow` edges |
| Model failover | Eligible model errors | Experimental `FallbackModel`; explicit recovery for tools |
| Guardrailed agent | Safety/compliance enforced | `before_model_callback` + `before_tool_callback` |
| Resource tiering | Cost optimization | Different `model` per agent |

**Key design rules:**
- Prefer graph-based or dynamic workflows over template workflows for new development.
- Group agents by responsibility; split unrelated domains when routing benefits.
- Pass data between agents via `output_key` + `output_schema` (Pydantic) — never rely on free text.
- Separate generation from evaluation — use a different agent to critique.
- Write precise sub-agent `description` fields — they drive Auto-Flow routing decisions.
- Embed reasoning steps in instructions: "1. Analyze 2. Plan 3. Execute 4. Verify".
- Include a fallback route for unclear inputs in graph edges.

See also: [references/workflows.md](references/workflows.md) (graph routing, HITL, dynamic loops) | [references/advanced-patterns.md](references/advanced-patterns.md) (Agent Config, deployment, AG-UI) | [references/design-patterns.md](references/design-patterns.md) (chaining, reflection, planning) | [references/a2a-protocol.md](references/a2a-protocol.md) (A2A server/client) | [references/memory-artifacts.md](references/memory-artifacts.md) (memory backends, artifacts) | [references/troubleshooting.md](references/troubleshooting.md) (debugging, 1.x->2.0 migration).

## Limitations

Graph workflows: no Live streaming; no legacy orchestrators as nodes; chat-mode agents only from `START`; task-mode-in-graph needs 2.5+ resumability. Full list: [references/workflows.md](references/workflows.md).

## Troubleshooting

Error → cause → fix patterns for setup, runtime, A2A, MCP, sessions, and the 1.x→2.0 migration: see [references/troubleshooting.md](references/troubleshooting.md).
