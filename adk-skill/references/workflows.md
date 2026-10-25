# ADK Workflows Reference (Python 2.13.0)

## Graph-based Workflows: Routing Patterns

### Conditional Routing

Functions can emit `Event(route=...)` to choose outgoing edges. This complete, deterministic example can run without a model:

```python
from google.adk import Event, Workflow
from google.adk.workflow import DEFAULT_ROUTE

def router(node_input: str):
    return Event(route=node_input.strip().upper())

def handle_bug():
    return Event(message="Handling bug", output="bug")

def handle_support():
    return Event(message="Handling support", output="support")

def handle_unknown():
    return Event(message="Please clarify the request", output="unknown")

root_agent = Workflow(
    name="routing_workflow",
    edges=[("START", router, {
        "BUG": handle_bug,
        "SUPPORT": handle_support,
        DEFAULT_ROUTE: handle_unknown,
    })],
)
```

For semantic classification, replace `router` with an agent or an experimental `ClassifierNode` (`google.adk.labs.classifiers`). The classifiers include `LlmClassifier`; `TypesafeClassifier` is a separate integration. Check their typed question/answer contracts before choosing one.

### Fan-out and Fan-in

Use a `JoinNode` before producing one final result. Multiple terminal nodes producing outputs cause an error; yielding only messages does not produce node output.

```python
from typing import Any
from google.adk import Workflow
from google.adk.workflow import JoinNode

def word_count(node_input: str) -> int:
    return len(node_input.split())

def shout(node_input: str) -> str:
    return node_input.upper()

join = JoinNode(name="join")

def report(node_input: dict[str, Any]) -> str:
    return f"{node_input['shout']} ({node_input['word_count']} words)"

root_agent = Workflow(
    name="fan_out_workflow",
    edges=[("START", (word_count, shout), join, report)],
)
```

Routing maps also accept tuples of targets, including `{DEFAULT_ROUTE: (a, b)}` since 2.10. A node may have several default edges; all matching fallback targets fire.

### Edge Syntax and Validation

| Form | Meaning |
|------|---------|
| `("START", a, b, c)` | Sequential chain |
| `("START", (a, b), join)` | Parallel branches followed by a join |
| `(a, {"success": b, DEFAULT_ROUTE: fallback})` | Conditional routing |
| `Edge(from_node=a, to_node=b, route="success")` | Explicit routed edge; requires node objects |

Import `Edge`, `START`, `DEFAULT_ROUTE`, `JoinNode`, and `node` from `google.adk.workflow`. `START` is not exported by `google.adk`. Plain functions work in chain tuples; wrap them with `@node()` or `FunctionNode(func=...)` for explicit `Edge` objects.

Graph construction validates reachable/unique nodes, compatible edge schemas and valid routing. Unconditional cycles fail; conditional cycles are allowed. Bound loop iterations in your state or orchestration logic. Duplicate edges with overlapping routes fail; disjoint routes between the same two nodes are valid.

### Data Binding and Output

- `ctx: Context` receives the workflow context; `node_input` receives the predecessor's value.
- Other function parameters read same-named `ctx.state` keys by default. Use `@node(parameter_binding="node_input")` to bind them from an input dict instead.
- Type hints drive validation and coercion. A missing required state key fails before the function body executes.
- `Event(output=value)` passes data downstream; `Event(message="...")` displays text. Use both when needed. Plain returned values become node output.
- Agent nodes can declare `input_schema` and `output_schema`; function-node schemas are inferred from annotations. Align source and destination schemas when both are declared.

## Dynamic Workflows

### Bounded Loops and Stable Execution IDs

```python
from google.adk import Context, Workflow
from google.adk.workflow import node

@node()
def revise(node_input: str) -> str:
    return node_input + "!"

@node(rerun_on_resume=True)
async def orchestrator(ctx: Context, node_input: str) -> str:
    result = node_input
    for index in range(3):
        result = await ctx.run_node(revise, result, run_id=f"revision-{index}")
    return result

root_agent = Workflow(name="revision_workflow", edges=[("START", orchestrator)])
```

An orchestrator replays its body on resume. Keep node order and `run_id` assignments deterministic so completed children can be replayed from history. Custom IDs must contain a non-numeric character. Avoid non-deterministic branching or external effects outside recorded child nodes.

Parallel dispatch uses `asyncio.gather(ctx.run_node(...), ...)`; bound concurrency for large inputs with parallel-worker options or a semaphore.

### Retry, Timeout and Failed-Node Resume

```python
from google.adk.workflow import node, RetryConfig

@node(
    retry_config=RetryConfig(max_attempts=3, initial_delay=1.0,
                             backoff_factor=2.0, exceptions=[TimeoutError]),
    timeout=30.0,
    parallel_worker=True, max_parallel_workers=8,
)
async def fetch(node_input: str) -> str:
    # Replace with an async HTTP client with its own request timeout.
    return node_input
```

`RetryConfig` also accepts `max_delay` and `jitter`. Retry only transient failures; return structured domain errors when retrying cannot help. Since 2.9, a failed node executes again on workflow resume instead of being replayed as completed. Successful child executions can be replayed; incomplete work can run again. Persist an idempotency key with external writes because a write followed by a failure may be repeated.

Synchronous functions/generator steps can use `RunConfig.tool_thread_pool_config`. Canceling a run or timing out a node cannot stop an already running worker thread or undo an external write.

## Human-in-the-Loop (HITL)

### Node Confirmation

Since 2.12, `@node` and `FunctionNode` support `require_confirmation`. The decorator enables re-entry automatically when it is not explicitly configured; explicit `FunctionNode(...)` requires `rerun_on_resume=True`.

```python
from google.adk import Context, Workflow
from google.adk.workflow import node

@node(require_confirmation=True)
def record_approval(ctx: Context, node_input: str) -> str:
    ctx.state["approved_count"] = ctx.state.get("approved_count", 0) + 1
    return f"Approved: {node_input}"

root_agent = Workflow(name="approval_workflow", edges=[("START", record_approval)])
```

The function body does not execute before approval. An `adk_request_input` event carries the interrupt ID. Resume with `{"confirmed": True}` to execute it; `{"confirmed": False}` skips the body and produces `{"error": "This tool call is rejected."}`. A callable predicate can decide whether confirmation is needed from the bound arguments.

Tool nodes also pause for confirmation (2.11+) and support authentication request/resume (2.12+). An authenticated function node uses `auth_config` and `rerun_on_resume=True`; resume the matching auth request, not a new invocation.

### Custom Requests

```python
from google.adk.events import RequestInput

def ask_name(node_input: str):
    yield RequestInput(
        interrupt_id="name-request", message="What is your name?",
        response_schema=dict[str, str],
    )
```

A leaf with default `rerun_on_resume=False` hands the validated response to its successor. A dynamic parent that awaits a child should use `rerun_on_resume=True`. For a node that needs to inspect its own resumed response, set re-entry and read `ctx.resume_inputs[interrupt_id]`.

### Resuming a RequestInput

Use the emitted `interruptId` as the function-response ID and retain the paused invocation ID. This helper assumes the `user` user ID used by the example runner:

```python
from google.genai import types

async def resume_input(runner, session_id, invocation_id, interrupt_id, response):
    message = types.Content(role="user", parts=[types.Part(
        function_response=types.FunctionResponse(
            id=interrupt_id, name="adk_request_input", response=response,
        ),
    )])
    return [event async for event in runner.run_async(
        user_id="user", session_id=session_id,
        invocation_id=invocation_id, new_message=message,
    )]
```

Enable `App(..., resumability_config=ResumabilityConfig(is_resumable=True))` and persistent session storage for recovery across process restarts. In-memory sessions only survive while their process does. Never swallow `BaseException`: interrupts and cancellation must propagate.

## Cooperative Cancellation (2.11+)

Pass an `asyncio.Event` as `abort_signal` to `Runner.run_async`. Set it from the request owner to cancel in-flight work. The `/run_sse` endpoint sets it when the client disconnects. Async tools must propagate `asyncio.CancelledError` after cleanup; sync threads and external side effects need their own cancellation/idempotency strategy.

```python
import asyncio

async def run_with_abort(runner, session_id, message, abort_signal: asyncio.Event):
    return [event async for event in runner.run_async(
        user_id="user", session_id=session_id, new_message=message,
        abort_signal=abort_signal,
    )]
```

## Collaboration Modes

| Mode | User Interaction | Return to Parent |
|------|-----------------|------------------|
| `chat` | Conversation until handoff | Transfer |
| `task` | May ask for clarification while working | `finish_task` with validated output |
| `single_turn` | No user interaction | Automatic result |

Set modes on sub-agents to control delegation. The root runs as a conversation entry point; do not use its mode to request delegation behavior. Task wrappers support nested sub-agent delegation and resumption in 2.12+. For an inline specialist that may pause/resume, prefer `mode="single_turn"` under `sub_agents` over `AgentTool`, whose separate nested session cannot resume unresolved long-running tools.

## Known Limitations

- Graph workflows do not support Live streaming.
- Explicit `chat`-mode nodes may only follow `START`; use `single_turn` to consume predecessor output.
- Template orchestrators (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) cannot be embedded as graph nodes. Use functions, agent nodes or nested `Workflow` objects.
- Recovery needs retained session events; rewound invocations are filtered during rehydration. Rewind cannot undo external effects.

## Versioned Sources

- [Graph validation and routing](https://github.com/google/adk-python/blob/v2.13.0/docs/guides/workflow/graph/index.md)
- [Function binding, confirmation and authentication](https://github.com/google/adk-python/blob/v2.13.0/docs/guides/workflow/function_node/index.md)
- [2.9 failed-node resume changes](https://github.com/google/adk-python/releases/tag/v2.9.0)
- [2.11 cancellation and tool confirmation](https://github.com/google/adk-python/releases/tag/v2.11.0)
- [2.12 node confirmation and nested task resumption](https://github.com/google/adk-python/releases/tag/v2.12.0)
