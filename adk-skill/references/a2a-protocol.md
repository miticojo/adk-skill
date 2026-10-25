# A2A (Agent-to-Agent) Protocol with ADK 2.13

## Choosing A2A

Use A2A for independently deployed agents, cross-language services or team boundaries. Use local sub-agents for same-process work with shared session services. A remote agent has its own state and credentials; sharing an HTTP task/context ID does not make state global.

Install `pip install "google-adk[a2a]==2.13.0"`. ADK supports A2A SDK 0.3 and 1.x through compatibility code; pin your selected dependency set when deploying.

## Expose an Agent

Save this complete example as `remote_agent/agent.py`, with `remote_agent/__init__.py` importing `.agent`:

```python
import math
from google.adk.agents import LlmAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

def add(left: float, right: float) -> dict[str, float]:
    """Add two finite numbers.

    Args:
        left: First operand.
        right: Second operand.
    """
    if not all(math.isfinite(value) for value in (left, right, left + right)):
        raise ValueError("Operands and result must be finite")
    return {"result": left + right}

root_agent = LlmAgent(
    name="math_agent", model="gemini-flash-latest",
    description="Add numbers using the add tool.",
    instruction="Use add for arithmetic.", tools=[add],
)
a2a_app = to_a2a(root_agent, port=8001)
```

```bash
uvicorn remote_agent.agent:a2a_app --host localhost --port 8001
curl http://localhost:8001/.well-known/agent-card.json
```

`to_a2a()` generates an Agent Card. For persistent operation, supply a runner factory and persistent services through its documented options; default in-memory services lose state on restart. `adk api_server --a2a --port 8001 path/to/agents` is another serving option, using an agent's `agent-card.json`.

## Consume a Remote Agent

```python
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

remote_math = RemoteA2aAgent(
    name="math_agent", description="Adds numbers.",
    agent_card="http://localhost:8001/.well-known/agent-card.json",
)
root_agent = LlmAgent(
    name="coordinator", model="gemini-flash-latest",
    instruction="Delegate arithmetic to math_agent.", sub_agents=[remote_math],
)
```

The card can be a URL, a path or an SDK `AgentCard`. Keep descriptions useful for routing. A caller-supplied `httpx.AsyncClient` must remain open for the runner's lifetime and close on the same event loop.

## Native Task Delegation (2.8+)

```python
from pydantic import BaseModel
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

class MathResult(BaseModel):
    result: float

remote_math = RemoteA2aAgent(
    name="math_task", mode="task", output_schema=MathResult,
    description="Complete an arithmetic task and return its result.",
    agent_card="http://localhost:8001/.well-known/agent-card.json",
)
```

Attach this proxy to a coordinator's `sub_agents`. The remote server must implement task completion: ADK task agents use `finish_task`. Its result schema must match the proxy's `output_schema`; an arbitrary text-only A2A server does not gain typed task semantics from the client's `mode` setting. `use_legacy=False` additionally requests ADK's new integration extension; it is a separate compatibility choice, not a requirement for setting task mode.

Task completion is different from authentication or approval. Resume the exact pending request on its original invocation/branch. Credentials requested by a local tool must not be forwarded to an untrusted remote peer.

## Agent Cards and Protocol Versions

A2A 1.x uses protobuf messages rather than the Pydantic objects of SDK 0.3. RPC URLs and protocol versions live in `supportedInterfaces`; legacy top-level `url` cards belong to 0.3. Prefer auto-generation or a version-matched JSON file over mixing constructor fields from different SDKs.

Example A2A 1.0 card (customize the URL and advertised capabilities to the actual server):

```json
{
  "name": "math_agent",
  "description": "Adds numbers",
  "version": "1.0.0",
  "supportedInterfaces": [
    {"url": "http://localhost:8001", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
  ],
  "capabilities": {"streaming": false},
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [{"id": "add", "name": "Add", "description": "Add numbers", "tags": ["math"]}]
}
```

Pass the file path through `to_a2a(..., agent_card="/absolute/path/agent-card.json")`. Card description and security settings are public discovery metadata; do not put credentials or private instructions in them. Since 2.12, card generation supports skill-level security. A fetched card's RPC targets are validated against its origin; fix a mismatched published URL instead of bypassing validation.

## Authentication and Forwarded Context

`RemoteA2aAgent` accepts `auth_scheme`, `auth_credential` and `credential_key` (2.8+). Credentials resolve for each invocation and authenticate both card discovery and requests. Use secret-backed configuration; never embed tokens in the card URL or logs.

`RunConfig.custom_metadata` propagates A2A metadata, but is not an authorization mechanism. `context_builder` (2.10+) controls which caller context is sent. Forward only the state/history the remote service needs. Namespaced forwarded `context_id` mode (2.12+) helps separate callers; use the tagged config contract instead of constructing IDs ad hoc.

## Verification and Troubleshooting

Test server discovery, task completion, multi-turn continuity, cancellation, and any approval/authentication resume your integration needs. For offline tests, construct the server/proxy and validate the card without a model call. A real conversation test also needs a running remote endpoint and model access.

| Failure | Fix |
|---------|-----|
| Missing A2A imports | Install the `[a2a]` extra |
| Card not found | Check `/.well-known/agent-card.json`, path prefix and port |
| Card validates but calls fail | Verify protocol version, binding, RPC URL and remote authentication |
| Protobuf/Pydantic constructor errors | Use fields and JSON parsing for the installed A2A SDK major version |
| Task never completes | Implement `finish_task` remotely and match the result schema |
| `Event loop is closed` | Scope clients/runners to their event loop and close them before teardown |
| Lost state after restart | Configure persistent services on the server and retain task context |
| Empty final event | Filter `event.is_final_response()` and non-thought text parts rather than indexing the last event |

ADK's integration remains experimental. Suppress only the relevant feature warning if necessary, not all `UserWarning` messages. ADK 2.8–2.12 fixed auth forwarding, duplicate tool/resume handling and cancellation; use current fixes rather than adding workarounds that replay tool calls blindly.

Go A2A examples and APIs are maintained in the [tagged Go samples](https://github.com/google/adk-go/tree/v2.6.0/examples); use the `/v2` module path when targeting Go ADK 2.6.

## Versioned Sources

- [Remote proxy and task completion](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/a2a/agent/_remote_a2a_agent.py)
- [Serving and runner factories](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/a2a/utils/agent_to_a2a.py)
- [Card construction and security](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/a2a/utils/agent_card_builder.py)
- [0.3/1.x wire compatibility](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/a2a/_compat.py)
