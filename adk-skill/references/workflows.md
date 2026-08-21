# ADK Workflows Reference (2.0+)

## Graph-based Workflows: Routing Patterns

### Conditional Routing

Route to different handlers based on node output using `Event(route=...)`:

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

Fan-out can also be declared in the edge dict itself — a tuple value triggers both targets:

```python
(classifier, {"BUG": (handle_bug, audit_log), "SUPPORT": handle_support})
```

### Edge Syntax Reference

| Form | Meaning |
|------|---------|
| `("START", a)` | Entry edge |
| `("START", a, b, c)` | Chain shorthand — expands to `a→b→c` |
| `(a, {"r1": x, "r2": y})` | Dict routing on emitted route values |
| `(a, x, "r1")` | Three-tuple routed edge (single route per edge) |
| `(a, {"__DEFAULT__": x})` | Fallback when no explicit route matches |

Rules enforced by graph validation:
- Edges leaving `START` cannot declare routes.
- Only one `__DEFAULT__` target per source node (`DEFAULT_ROUTE = "__DEFAULT__"`).
- Duplicate edges between the same pair of nodes are rejected.
- All nodes must be reachable from `START`; cycles are rejected.

### Data Flow Between Nodes

Nodes pass data via typed return values. Agent nodes use `input_schema`/`output_schema` (Pydantic):

```python
from pydantic import BaseModel

class CityTime(BaseModel):
    time_info: str
    city: str

city_agent = LlmAgent(
    name="city_lookup", model="gemini-flash-latest",
    instruction="Return a random city name.", output_schema=str,
)

def lookup_time(city: str) -> CityTime:
    return CityTime(time_info="10:10 AM", city=city)

reporter = LlmAgent(
    name="reporter", model="gemini-flash-latest",
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

### Node Options and Retries

The `@node` decorator accepts execution controls (2.4+):

```python
from google.adk.workflow import node, RetryConfig

@node(
    retry_config=RetryConfig(max_attempts=3, initial_delay=1.0,
                             backoff_factor=2.0, exceptions=["ValueError"]),
    timeout=30.0,
    parallel_worker=True, max_parallel_workers=8,  # run many items concurrently
)
def fetch(url: str) -> str: ...
```

`RetryConfig` fields: `max_attempts`, `initial_delay` (default 1.0s), `max_delay` (60.0s), `backoff_factor` (2.0), `jitter` (1.0; 0.0 disables), `exceptions` (names or classes). For fan-in synchronization after parallel branches, use `JoinNode`, which fires only after all its predecessors have triggered.

### Strict Edge Schemas

As of 2.5, graph validation fails fast when a source's `output_schema` does not equal the target's `input_schema` on an edge ("Schema mismatch on edge X -> Y"). Align Pydantic models or drop the schemas to rely on plain values.

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
- 2.5+ adds HITL resumption for standalone nodes and `NodeTool` — a paused tool/node resumes without re-running its parent graph.

---

## Collaboration Modes in Workflows

| Mode | User Interaction | Control Flow | Parallel | Return to Parent |
|------|-----------------|-------------|----------|-----------------|
| `chat` (default as sub-agent) | Full interaction | Agent controls until handoff | No | Manual (transfer) |
| `task` | Clarification only | Agent controls until complete | No | Automatic (`complete_task`) |
| `single_turn` (default as node) | Disallowed | Returns immediately after task | Yes | Automatic (with result) |

**Note:** Do NOT set `mode` on the root agent. Task-mode agents cannot have sub-agents.

---

## Known Limitations

- **Live streaming** is not supported in graph-based workflows.
- Some third-party integrations may not be compatible with graph-based workflows.
- **chat-mode agents in graphs**: only reachable directly from `START` (they need conversational history, not node inputs). Incoming edges from other nodes raise a validation error telling you to use `mode="single_turn"`.
- **task-mode nodes** were disabled at 2.0; 2.5 re-enables them with state-based resumption, so task agents survive pause/resume inside graphs.
- Legacy orchestrators (`SequentialAgent`/`ParallelAgent`/`LoopAgent`) are rejected if embedded as Workflow nodes (2.5 validation) — compose graphs from agents, functions, and dynamic nodes instead.
