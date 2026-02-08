# A2A (Agent-to-Agent) Protocol with ADK

## Overview

The [Agent2Agent (A2A) Protocol](https://a2a-protocol.org/) is an open standard for inter-agent communication over HTTP. ADK provides built-in support for both **exposing** agents as A2A servers and **consuming** remote A2A agents as sub-agents.

**Status:** Supported in Python and Go (Experimental).

## When to Use A2A vs Local Sub-Agents

| Criteria | A2A (Remote) | Local Sub-Agents |
|----------|-------------|-----------------|
| Deployment | Separate services, different machines | Same process |
| Teams | Different teams/organizations | Same team |
| Languages | Cross-language (Python, Go, Java, etc.) | Same language |
| Contract | Formal A2A protocol | In-memory function calls |
| Performance | Network overhead | Direct memory access |
| State | Isolated state per agent | Shared session state |

**Use A2A when:**
- The agent runs as a separate, standalone service
- Different teams maintain different agents
- Agents are written in different languages/frameworks
- You need a microservices architecture for agents
- You want formal API contracts between components

**Use local sub-agents when:**
- Agents share the same process and state
- Performance is critical (no network overhead)
- Simple internal code organization
- Helper functions that don't need independent deployment

---

## Architecture

```text
Consuming Side:                              Exposing Side:
+--------------------+    +------------------+    +-------------------+
|   Root Agent       |    | RemoteA2aAgent   |    |   A2A Server      |
| (your application) |--->| (ADK client      |--->| (ADK component)   |
|                    |    |  proxy)           |    |                   |
+--------------------+    +------------------+    +-------------------+
                                                          |
                                                          v
                                                  +-------------------+
                                                  | Your Agent Code   |
                                                  | (Exposed Service) |
                                                  +-------------------+
```

---

## Python: Exposing an Agent via A2A

### Method 1: `to_a2a()` Function (Recommended)

Wraps any ADK agent as an A2A-compatible ASGI app. Auto-generates an agent card.

```python
# remote_agent/agent.py
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

root_agent = Agent(
    name="math_agent",
    model="gemini-2.5-flash",
    instruction="You solve math problems.",
    tools=[solve_equation],
)

# Wrap as A2A app — auto-generates agent card
a2a_app = to_a2a(root_agent, port=8001)
```

Run with uvicorn:

```bash
uvicorn remote_agent.agent:a2a_app --host localhost --port 8001
```

Verify the agent card:

```bash
curl http://localhost:8001/.well-known/agent-card.json
```

### Method 2: `adk api_server --a2a`

Exposes agents using the ADK CLI. Requires a manual `agent-card.json` file.

```bash
# Install A2A dependencies
pip install google-adk[a2a]

# Expose agent on port 8001
adk api_server --a2a --port 8001 path/to/agent_folder
```

### Agent Card (agent-card.json)

The A2A protocol requires each agent to publish a card describing its capabilities:

```json
{
  "name": "math_agent",
  "description": "An agent that solves math problems.",
  "version": "1.0.0",
  "url": "http://localhost:8001",
  "capabilities": {},
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [
    {
      "id": "math_solving",
      "name": "Math Problem Solving",
      "description": "Solve equations and math problems",
      "tags": ["math", "computation"]
    }
  ]
}
```

With `to_a2a()`, the card is auto-generated from your agent's name, description, instruction, and tools. You can override it:

```python
from a2a.types import AgentCard

# Custom card
card = AgentCard(
    name="math_agent",
    url="http://localhost:8001",
    description="Solves math problems",
    version="1.0.0",
    capabilities={},
    skills=[],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False,
)
a2a_app = to_a2a(root_agent, port=8001, agent_card=card)

# Or from a JSON file
a2a_app = to_a2a(root_agent, port=8001, agent_card="/path/to/agent-card.json")
```

---

## Python: Consuming a Remote A2A Agent

Use `RemoteA2aAgent` to connect to any A2A-compatible agent:

```python
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

# Connect to remote A2A agent
remote_math = RemoteA2aAgent(
    name="math_agent",
    description="Agent that solves math problems.",
    agent_card="http://localhost:8001/.well-known/agent-card.json",
)

# Use as a sub-agent in your root agent
root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    instruction="""You are a helpful assistant.
    Delegate math questions to math_agent.""",
    sub_agents=[remote_math],
)
```

The `RemoteA2aAgent` parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Name for the remote agent |
| `description` | `str` | What the agent does (used for routing) |
| `agent_card` | `str` | URL to the agent card endpoint |

---

## Go: Exposing an Agent via A2A

Use the A2A launcher for auto-generated agent cards:

```go
package main

import (
    "log"
    "strconv"

    "google.golang.org/adk/agent"
    "google.golang.org/adk/agent/llmagent"
    "google.golang.org/adk/launcher/a2a"
    "google.golang.org/adk/launcher/web"
    "google.golang.org/adk/model/gemini"
    "google.golang.org/genai"
)

func main() {
    port := 8001
    ctx := context.Background()

    model, _ := gemini.NewModel(ctx, "gemini-2.0-flash", &genai.ClientConfig{})
    myAgent, _ := llmagent.New(llmagent.Config{
        Name:        "math_agent",
        Model:       model,
        Instruction: "You solve math problems.",
        Tools:       []tool.Tool{solveTool},
    })

    webLauncher := web.NewLauncher(a2a.NewLauncher())
    webLauncher.Launch(ctx, myAgent,
        "a2a", "--a2a_agent_url", "http://localhost:"+strconv.Itoa(port),
        "--port", strconv.Itoa(port),
    )
}
```

## Go: Consuming a Remote A2A Agent

```go
import "google.golang.org/adk/agent/remoteagent"

remoteAgent, err := remoteagent.NewA2A(remoteagent.A2AConfig{
    Name:            "math_agent",
    Description:     "Agent that solves math problems.",
    AgentCardSource: "http://localhost:8001",
})

rootAgent, _ := llmagent.New(llmagent.Config{
    Name:      "root_agent",
    Model:     model,
    SubAgents: []agent.Agent{remoteAgent},
})
```

---

## Complete Example: Two-Agent A2A System (Python)

### Project Structure

```text
a2a_demo/
├── remote_agent/
│   ├── __init__.py
│   └── agent.py         # Exposed via A2A (port 8001)
├── main_agent/
│   ├── __init__.py
│   └── agent.py         # Consumes remote agent
├── pyproject.toml
└── .env
```

### Remote Agent (Exposed)

```python
# remote_agent/agent.py
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

def check_prime(nums: list[int]) -> str:
    """Check if numbers in a list are prime.

    Args:
        nums: The list of numbers to check.

    Returns:
        A string indicating which numbers are prime.
    """
    results = []
    for n in nums:
        if n < 2:
            results.append(f"{n} is not prime")
        elif all(n % i != 0 for i in range(2, int(n**0.5) + 1)):
            results.append(f"{n} is prime")
        else:
            results.append(f"{n} is not prime")
    return ", ".join(results)

root_agent = Agent(
    name="prime_checker",
    model="gemini-2.5-flash",
    instruction="You check if numbers are prime using the check_prime tool.",
    tools=[check_prime],
)

# Expose as A2A server
a2a_app = to_a2a(root_agent, port=8001)
```

### Main Agent (Consuming)

```python
# main_agent/agent.py
import random
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

def roll_die(sides: int) -> int:
    """Roll a die with the given number of sides.

    Args:
        sides: Number of sides on the die.

    Returns:
        The rolled result.
    """
    return random.randint(1, sides)

prime_agent = RemoteA2aAgent(
    name="prime_checker",
    description="Checks if numbers are prime.",
    agent_card="http://localhost:8001/.well-known/agent-card.json",
)

root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    instruction="""You can roll dice and check if numbers are prime.
    Delegate prime checking tasks to prime_checker.
    1. If asked to roll a die, use roll_die.
    2. If asked to check primes, delegate to prime_checker.
    3. If asked to roll and check, roll first then delegate the result.""",
    tools=[roll_die],
    sub_agents=[prime_agent],
)
```

### Running

```bash
# Terminal 1: Start the remote A2A agent
uvicorn remote_agent.agent:a2a_app --host localhost --port 8001

# Terminal 2: Start the main agent
adk web main_agent
```

---

## Programmatic Testing (A2A)

Test A2A communication programmatically using `InMemoryRunner` on the consuming side:

```python
import pytest
from google.adk.runners import InMemoryRunner
from google.genai import types
from main_agent.agent import root_agent

@pytest.mark.asyncio
async def test_a2a_prime_check():
    """Test that root agent delegates prime checking via A2A."""
    runner = InMemoryRunner(agent=root_agent, app_name="test")
    session = await runner.session_service.create_session(
        user_id="test_user", app_name="test",
    )
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text="Is 7 a prime number?")],
    )
    events = []
    async for event in runner.run_async(
        user_id="test_user",
        session_id=session.id,
        new_message=content,
    ):
        events.append(event)

    final_text = events[-1].content.parts[0].text.lower()
    assert "prime" in final_text
```

**Note:** The remote A2A server must be running before executing tests.

---

## A2A Metadata Propagation

ADK automatically propagates metadata across A2A boundaries via `custom_metadata` in `RunConfig`:

```python
from google.adk.agents.run_config import RunConfig

run_config = RunConfig(
    custom_metadata={"trace_id": "abc-123", "user_tier": "premium"}
)

# Metadata appears in remote agent events as:
# event.custom_metadata["a2a_metadata"]["trace_id"]
```

---

## Port Configuration

When running locally, use different ports for each agent:

| Agent | Default Port | Flag |
|-------|-------------|------|
| Main agent (`adk web`) | 8000 | `--port` |
| Remote A2A agent | 8001+ | `--port` or uvicorn `--port` |

---

## Important: Installation

The base `google-adk` package does **not** include A2A dependencies. You must install with the `a2a` extra:

```bash
pip install google-adk[a2a]
```

This installs the `a2a-sdk` package alongside ADK.

---

## Practical Notes (Validated by Testing)

**Agent card auto-generation:** `to_a2a()` generates a card with version `"0.0.1"` and auto-detects skills from agent tools and instructions. Each tool becomes a separate skill entry in the card.

**Agent identity propagation:** When a remote agent responds via A2A, the `event.author` field correctly reflects the remote agent's name (e.g., `"weather_service"`), not the root agent.

**Multi-turn sessions:** A2A works correctly across multiple turns within the same session. The remote agent maintains context through the A2A protocol's task/message system.

**Event loop requirement:** When testing A2A programmatically, run all A2A tests in a **single `asyncio.run()` call**. Calling `asyncio.run()` per test closes the event loop between tests, which breaks the A2A client's httpx async connections. Use a single async test runner:

```python
async def run_all_tests():
    await test_agent_card()
    await test_a2a_query()
    await test_multi_turn()

asyncio.run(run_all_tests())  # Single event loop for all A2A tests
```

**Experimental status:** ADK's A2A implementation emits `UserWarning` messages about experimental status. The A2A protocol and SDK themselves are stable; only ADK's integration layer is experimental. Suppress with `warnings.filterwarnings("ignore", category=UserWarning)` if needed.

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Connection refused | Verify remote agent is running and port is correct |
| Agent card not found | Check `/.well-known/agent-card.json` endpoint |
| Import error on `to_a2a` | Install with `pip install google-adk[a2a]` |
| `Event loop is closed` | Run all A2A tests in a single `asyncio.run()` call |
| Timeout on A2A calls | Check network, increase timeout, verify agent card URL |
| Agent not routing to remote | Check `description` field -- it drives LLM routing decisions |
| Experimental warnings | ADK A2A integration is experimental; protocol itself is stable |
