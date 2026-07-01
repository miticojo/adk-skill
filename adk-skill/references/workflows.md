# ADK Workflows Reference (2.0+)

## Graph-based Workflows: Routing Patterns

### Conditional Routing

Route to different handlers based on node output using `Event(route=...)`:

```python
from google.adk import Workflow, Event
from google.adk.agents import LlmAgent

classifier = LlmAgent(
    name="classifier", model="gemini-3-flash-preview",
    instruction="Classify input as 'BUG', 'SUPPORT', or 'LOGISTICS'.",
    output_schema=str,
)

def router(node_input: str):
    routes = [r.strip() for r in node_input.split(",")]
    return Event(route=routes)

def handle_bug():       return Event(message="Handling bug...")
def handle_support():   return Event(message="Handling support...")
def handle_logistics(): return Event(message="Handling logistics...")

root_agent = Workflow(
    name="routing_workflow",
    edges=[
        ("START", classifier, router),
        (router, {
            "BUG": handle_bug,
            "SUPPORT": handle_support,
            "LOGISTICS": handle_logistics,
        }),
    ],
)
```

### Multi-Route (Fan-out to multiple handlers)

When a node outputs multiple routes, the message is delivered to all matching handlers:

```python
def router(node_input: str):
    return Event(route=["BUG", "SUPPORT"])  # Routes to both handlers
```

### Data Flow Between Nodes

Nodes pass data via typed return values. Agent nodes use `input_schema`/`output_schema` (Pydantic):

```python
from pydantic import BaseModel

class CityTime(BaseModel):
    time_info: str
    city: str

city_agent = LlmAgent(
    name="city_lookup", model="gemini-3-flash-preview",
    instruction="Return a random city name.", output_schema=str,
)

def lookup_time(city: str) -> CityTime:
    return CityTime(time_info="10:10 AM", city=city)

reporter = LlmAgent(
    name="reporter", model="gemini-3-flash-preview",
    input_schema=CityTime,
    instruction="Report: It is {time_info} in {city} right now.",
)

root_agent = Workflow(
    name="time_workflow",
    edges=[("START", city_agent, lookup_time, reporter)],
)
```

---

## Dynamic Workflows

### Loops and Conditional Branching

Use standard Python control flow inside a `@node(rerun_on_resume=True)` orchestrator:

```python
from google.adk import Context
from google.adk.workflow import node

@node(name="lint_check")
def lint(code: str) -> str:
    # Simulate: return findings or empty string if clean
    return "" if len(code) > 100 else "Code too short; add error handling."

@node(name="fix_code")
def fix(code: str) -> str:
    return code + "\n# error handling added"

@node(rerun_on_resume=True)
async def code_workflow(ctx: Context, user_request: str) -> str:
    code = await ctx.run_node(coder_agent, user_request)
    findings = await ctx.run_node(lint, code)

    while findings:
        code = await ctx.run_node(fix, code)
        findings = await ctx.run_node(lint, code)

    return code
```

### Parallel Execution

Use `asyncio.gather` to run nodes in parallel:

```python
import asyncio
from google.adk import Context
from google.adk.workflow import node

@node(rerun_on_resume=True)
async def parallel_supervisor(ctx: Context, items: list[str]) -> list[str]:
    tasks = [ctx.run_node(worker_node, item) for item in items]
    results = await asyncio.gather(*tasks)
    return results
```

**Resume behavior:** On workflow resume after interruption, only failed/incomplete workers are re-executed.

### Custom Execution IDs

For stable, deterministic identifiers (e.g., per-item processing):

```python
@node(rerun_on_resume=True)
async def process_orders(ctx: Context, orders: list[str]) -> list[str]:
    tasks = [
        ctx.run_node(process_order, order, run_id=f"order-{order.id}")
        for order in orders
    ]
    return await asyncio.gather(*tasks)
```

Custom `run_id` must contain at least one non-numeric character to avoid collision with auto-generated sequential IDs.

---

## Human-in-the-Loop (HITL)

### Graph-based HITL

Use `RequestInput` events to pause the workflow:

```python
from google.adk.events import RequestInput

def get_approval(node_input: str):
    yield RequestInput(message="Please approve this request (Yes/No)")
```

### Dynamic Workflow HITL

Yield `RequestInput` from a node, await the human response in the orchestrator:

```python
from google.adk.events import RequestInput

@node(rerun_on_resume=False)  # Handoff: resume payload goes to successor
async def get_user_approval(ctx: Context, node_input: str):
    yield RequestInput(message="Please approve this request (Yes/No)")

@node(rerun_on_resume=True)   # Re-entry: node body re-runs on resume
async def handle_process(ctx: Context, node_input: str) -> str:
    user_response = await ctx.run_node(get_user_approval)
    return "Approved" if user_response.lower() == "yes" else "Denied"
```

**Key rules for HITL:**
- Parent orchestrator nodes MUST set `rerun_on_resume=True` to handle interruptions.
- Leaf nodes requesting input typically use `rerun_on_resume=False` (handoff mode).
- Never catch `BaseException` in tools — it traps `NodeInterruptedError`, breaking HITL.

---

## Known Limitations

- **Live streaming** is not supported in graph-based workflows.
- Some third-party integrations may not be compatible with graph-based workflows.
- `task` collaboration mode is disabled in graph-based workflows (Python v2.0; expected to be re-enabled in a future release).
