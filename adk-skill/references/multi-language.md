# ADK Multi-Language Reference

ADK supports Python, Java, Go, and TypeScript. Core concepts (agents, tools, state, callbacks) are the same across languages. This reference covers language-specific patterns.

## Language Overview

| | Python | Java | Go | Kotlin | TypeScript |
|--|--------|------|----|--------|------------|
| **Package** | `google-adk` | `com.google.adk:google-adk` | `google.golang.org/adk/v2` | `com.google.adk:google-adk-kotlin-core` | `@google/adk` |
| **Min version** | Python 3.10+ | Java 17+ | Go 1.25+ (v2) | Kotlin 1.9+ | Node.js 24+ |
| **Latest** | 2.7.x | 1.8.0 | v2.2.0 (+1.x LTS) | 0.8.0 pre-GA | 2.0.0 (+1.x LTS) |
| **Install** | `pip install google-adk` | Maven/Gradle | `go get google.golang.org/adk/v2` | Gradle | `npm install @google/adk` |
| **ADK 2.x** | Reference impl | No 2.x yet | Yes | No | Yes (experimental) |
| **Agent pattern** | Constructor kwargs | Builder pattern | Struct config | Constructor kwargs | Constructor object |
| **Tool pattern** | Function + docstring | `@Schema` annotations | Struct types | Function + annotations | Zod schemas |
| **Runner** | `InMemoryRunner` (async) | `InMemoryRunner` (RxJava) | Launcher | `InMemoryRunner` | `InMemoryRunner` |
| **Entry point** | `root_agent` variable | `ROOT_AGENT` static field | `main()` func | `root_agent` variable | `export rootAgent` |
| **CLI** | `adk run` / `adk web` | `mvn exec:java` | `go run` | `gradle run` | `npx adk run` / `npx adk web` |

### 2.x Feature Parity (verified Aug 2026)

| Capability | Python 2.7 | Go v2.2 | TS 2.0 | Java 1.8 | Kotlin 0.8 |
|------------|:---:|:---:|:---:|:---:|:---:|
| Graph-based Workflow | ✅ | ✅ | ✅ @experimental | ❌ | ❌ |
| Dynamic nodes | ✅ | ✅ | ✅ `ctx.runNode()` | ❌ | ❌ |
| Collab modes (`chat`/`task`/`single_turn`) | ✅ all | ✅ all | ◐ no `chat` | ❌ | ❌ |
| Plugins | ✅ | ✅ | ✅ incl. node callbacks | ✅ | ✅ |
| Session rewind | ✅ | UNVERIFIED | ❌ | groundwork only | UNVERIFIED |

Java/Kotlin remain on the 1.x-style template-agent model; Python features land there later or not at all.

---

## Java

### Project Structure

```
my_agent/
├── src/main/java/com/example/agent/
│   ├── MyAgent.java            # Agent definition + ROOT_AGENT
│   └── AgentCliRunner.java     # CLI runner (optional)
├── pom.xml
└── .env
```

### Dependencies (Maven)

```xml
<dependencies>
    <dependency>
        <groupId>com.google.adk</groupId>
        <artifactId>google-adk</artifactId>
        <version>1.8.0</version>
    </dependency>
    <dependency>
        <groupId>com.google.adk</groupId>
        <artifactId>google-adk-dev</artifactId>
        <version>1.8.0</version>
    </dependency>
</dependencies>
```

### Agent Creation (Builder Pattern)

```java
import com.google.adk.agents.LlmAgent;
import com.google.adk.agents.BaseAgent;
import com.google.adk.tools.FunctionTool;
import io.swagger.v3.oas.annotations.media.Schema;

public class MyAgent {
    public static final BaseAgent ROOT_AGENT = initAgent();

    private static BaseAgent initAgent() {
        return LlmAgent.builder()
            .name("my_agent")
            .model("gemini-flash-latest")
            .description("Agent description for routing")
            .instruction("Detailed system prompt...")
            .tools(FunctionTool.create(MyAgent.class, "getWeather"))
            .build();
    }

    @Schema(description = "Get current weather for a city")
    public static Map<String, String> getWeather(
        @Schema(name = "city", description = "City name") String city
    ) {
        return Map.of("city", city, "temperature", "22C", "conditions", "sunny");
    }
}
```

### Tools with @Schema Annotations

Java tools are static methods with `@Schema` annotations on both the method and parameters:

```java
@Schema(description = "Add item to shopping cart")
public static Map<String, Object> addToCart(
    @Schema(name = "item", description = "Item name") String item,
    @Schema(name = "quantity", description = "Number of items") int quantity
) {
    return Map.of("status", "added", "item", item, "quantity", quantity);
}

// Register: FunctionTool.create(MyClass.class, "addToCart")
```

### Multi-Agent (Builder Composition)

```java
LlmAgent researcher = LlmAgent.builder()
    .name("researcher").model("gemini-flash-latest")
    .instruction("Research the topic.").outputKey("research")
    .build();

LlmAgent writer = LlmAgent.builder()
    .name("writer").model("gemini-flash-latest")
    .instruction("Write report based on research.")
    .build();

SequentialAgent pipeline = SequentialAgent.builder()
    .name("pipeline").subAgents(researcher, writer)
    .build();
```

### Runner and Testing

```java
import com.google.adk.runner.InMemoryRunner;
import com.google.adk.events.Event;
import io.reactivex.rxjava3.core.Flowable;

InMemoryRunner runner = new InMemoryRunner(ROOT_AGENT);
Session session = runner.sessionService()
    .createSession("app_name", "user_id").blockingGet();

Content userMsg = Content.fromParts(Part.fromText("Hello"));
Flowable<Event> events = runner.runAsync("user_id", session.id(), userMsg);
events.blockingForEach(event -> System.out.println(event.stringifyContent()));
```

### Running

```bash
source .env
# CLI
mvn compile exec:java -Dexec.mainClass="com.example.agent.AgentCliRunner"
# Web UI
mvn compile exec:java -Dexec.mainClass="com.google.adk.web.AdkWebServer" \
    -Dexec.args="--adk.agents.source-dir=target --server.port=8000"
```

### MCP Tools (Java)

```java
import com.google.adk.tools.mcp.McpToolset;
import com.google.adk.tools.mcp.SseServerParameters;

SseServerParameters params = SseServerParameters.builder()
    .url("http://127.0.0.1:5000/mcp/").build();
McpToolset.McpToolsAndToolsetResult result =
    McpToolset.fromServer(params, new ObjectMapper()).get();
List<BaseTool> mcpTools = result.getTools().stream()
    .map(t -> (BaseTool) t).collect(Collectors.toList());
```

### Recent Java Additions (1.6.0–1.8.0)

- `ClassPathSkillSource` — load Agent Skills from the classpath (1.6+)
- `RunConfig.groupFunctionResponsesInHistory` (1.6+)
- `SequentialAgent` advances to later sub-agents after HITL resume when resumability is enabled (1.6+)
- Plugin + Runner `onRunErrorCallback` hook (1.8+)
- Forced function-call reordering for gemini-3 models; A2A request metadata propagated into `RunConfig` (1.7+)

---

## Go

### Project Structure

```
my_agent/
├── agent.go        # Main package with agent + launcher
├── go.mod          # Module definition
└── .env            # GOOGLE_API_KEY
```

### Setup

Go ships dual lines: v1 (`google.golang.org/adk`) and the current v2 line (requires **Go 1.25+**):

```bash
go mod init my-agent/main
go get google.golang.org/adk/v2
go mod tidy
```

Key v2 packages: `agent`, `workflow`, `runner`, `plugin`, `model`, `tool`, `session`, `memory`, `artifact`, `auth`, `server`, `agentregistry`, `platform`.

### Agent Creation (Struct Config)

```go
package main

import (
    "context"
    "log"
    "os"

    "google.golang.org/adk/agent"
    "google.golang.org/adk/agent/llmagent"
    "google.golang.org/adk/cmd/launcher"
    "google.golang.org/adk/cmd/launcher/full"
    "google.golang.org/adk/model/gemini"
    "google.golang.org/genai"
)

func main() {
    ctx := context.Background()

    model, err := gemini.NewModel(ctx, "gemini-flash-latest",
        &genai.ClientConfig{
            APIKey: os.Getenv("GOOGLE_API_KEY"),
        })
    if err != nil {
        log.Fatalf("Failed to create model: %v", err)
    }

    myAgent, err := llmagent.New(llmagent.Config{
        Name:        "my_agent",
        Model:       model,
        Description: "Agent description",
        Instruction: "Detailed system prompt...",
        Tools:       []tool.Tool{geminitool.GoogleSearch{}},
    })
    if err != nil {
        log.Fatalf("Failed to create agent: %v", err)
    }

    l := full.NewLauncher()
    l.Start(ctx, launcher.Config{Agent: myAgent})
}
```

### Running

```bash
source .env
go run agent.go                    # CLI mode
go run agent.go web api webui      # Web UI on localhost:8080
```

### Go 2.x Highlights (v2.0.0–v2.2.0)

- **Graph workflows**: static + dynamic graphs, conditional routing, fan-out/fan-in `JoinNode`, parallel workers, per-node retries/timeouts, HITL pause/resume.
- **Collaboration**: `LlmAgent` gains `chat`, `task`, `single_turn` modes with isolation-scoped history.
- **Context unification**: `ToolContext`+`CallbackContext` merged into a single `agent.Context` (`agent.StrictContextMock` in tests).
- **v2.1+**: platform `TaskRunner` seam; name-based model registry (`Register`/`NewLLM`); `PackTool`; `runner.NewInMemory`; `agentregistry` package (REST + discovery); `RemoteAgent`/`McpToolset` factories; auth credential providers; MCP per-request auth via `Config.Auth`.

---

## TypeScript

### Project Structure

```
my-agent/
├── agent.ts        # Agent definition (exports rootAgent)
├── tools.ts        # Tool definitions (optional)
├── package.json
└── .env            # GEMINI_API_KEY
```

### Setup

```bash
mkdir my-agent && cd my-agent
npm init --yes
npm pkg set type="module"
npm pkg set main="agent.ts"
npm install @google/adk
npm install -D @google/adk-devtools
```

### Agent Creation (Constructor)

```typescript
import { LlmAgent } from '@google/adk';

export const rootAgent = new LlmAgent({
    name: 'my_agent',
    model: 'gemini-flash-latest',
    description: 'Agent description',
    instruction: 'Detailed system prompt...',
    tools: [getWeather],
});
```

### Tools (Zod Schemas)

TypeScript tools use `FunctionTool` with Zod for parameter validation:

```typescript
import { FunctionTool } from '@google/adk';
import { z } from 'zod';

const getWeather = new FunctionTool({
    name: 'get_weather',
    description: 'Get current weather for a city.',
    parameters: z.object({
        city: z.string().describe('The city name to look up weather for.'),
        units: z.enum(['celsius', 'fahrenheit']).default('celsius'),
    }),
    execute: ({ city, units }) => {
        return { temperature: 22, conditions: 'sunny', city };
    },
});
```

### Multi-Agent Composition

```typescript
import { LlmAgent, SequentialAgent, ParallelAgent } from '@google/adk';

const researcher = new LlmAgent({
    name: 'researcher', model: 'gemini-flash-latest',
    instruction: 'Research the topic.', outputKey: 'research',
});

const writer = new LlmAgent({
    name: 'writer', model: 'gemini-flash-latest',
    instruction: 'Write report based on research.',
});

export const rootAgent = new SequentialAgent({
    name: 'pipeline',
    subAgents: [researcher, writer],
});
```

### Callbacks (TypeScript)

```typescript
export const rootAgent = new LlmAgent({
    name: 'guarded_agent',
    model: 'gemini-flash-latest',
    instruction: '...',
    tools: [myTool],
    beforeToolCallback: (tool, args, toolContext) => {
        if (tool.name === 'dangerous_tool') {
            return { error: 'Tool blocked by policy' };
        }
        return undefined; // proceed
    },
    beforeModelCallback: (callbackContext, llmRequest) => {
        // Rate limiting, safety checks
        return undefined;
    },
});
```

### Runner and Testing

```typescript
import { InMemoryRunner, isFinalResponse } from '@google/adk';
import { createUserContent } from '@google/genai';

const runner = new InMemoryRunner({ agent: rootAgent, appName: 'test' });
const session = await runner.sessionService.createSession({
    userId: 'test_user', appName: 'test',
});

const content = createUserContent('Hello');
for await (const event of runner.runAsync({
    userId: 'test_user', sessionId: session.id, newMessage: content,
})) {
    if (isFinalResponse(event)) {
        console.log(event.content?.parts?.[0]?.text);
    }
}
```

### Running

```bash
npx adk run agent.ts        # CLI mode
npx adk web                 # Web UI on localhost:8000
```

### TypeScript 2.0 Changes (Aug 2026)

- **Workflow engine core** (`@experimental`): graphs, node registry, dynamic scheduling via `ctx.runNode()`, `JoinNode`, HITL utils, retry configs.
- **Breaking:** `BaseAgent extends BaseNode` — agents carry `rerunOnResume`, `waitForOutput`, `retryConfig`, `timeout`, `inputSchema`/`outputSchema`. `InvocationContext.agent` is optional; use `requireAgent(ctx)`.
- **Deprecated:** `SequentialAgent`/`ParallelAgent`/`LoopAgent` (graph workflows replace them); `LLMAgentWrapper` removed.
- **Collaboration:** node config `mode: 'single_turn' | 'task'` — no `chat` mode yet.
- Also: plugins with before/after-node callbacks, security/logging plugins, `RoutedAgent`/`RoutedLlm` routing (graduated from experimental), `Runner.runLive`, `require_confirmation` on tools, skills subsystem (`SkillToolset`, `loadSkillFromDir`).

---

## Cross-Language Comparison: Tool Definition

The same tool defined in each language:

**Python:**
```python
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city.
    Args:
        city: The city name.
        units: Temperature units.
    """
    return {"temperature": 22, "city": city}
```

**Java:**
```java
@Schema(description = "Get current weather for a city")
public static Map<String, Object> getWeather(
    @Schema(name = "city", description = "The city name") String city,
    @Schema(name = "units", description = "Temperature units") String units
) {
    return Map.of("temperature", 22, "city", city);
}
// FunctionTool.create(MyClass.class, "getWeather")
```

**TypeScript:**
```typescript
const getWeather = new FunctionTool({
    name: 'get_weather',
    description: 'Get current weather for a city.',
    parameters: z.object({
        city: z.string().describe('The city name'),
        units: z.string().default('celsius').describe('Temperature units'),
    }),
    execute: ({ city }) => ({ temperature: 22, city }),
});
```

**Go:** Tools in Go use struct-based types (e.g., `geminitool.GoogleSearch{}`) or custom tool implementations satisfying the `tool.Tool` interface.

**Go 2.0:** Use `workflow.NewFunctionNode` and `workflow.NewAgentNode` for nodes, `workflow.Chain` or `workflow.Concat` with `[]workflow.Edge` for edges, and `workflowagent.New` to wrap as a runnable agent. Import from `google.golang.org/adk/v2`.

---

## Kotlin

Kotlin ADK is a separate, Android/on-device-first implementation (LiteRT-LM on-device chat, ML Kit, Firebase model streaming) — pre-GA at 0.x. Build agents using Java-interop builders or Kotlin-idiomatic APIs.

### Installation

```kotlin
// build.gradle.kts
dependencies {
    implementation("com.google.adk:google-adk-kotlin-core:0.8.0")
}
```

Sibling artifacts: `-core-jvm`, `-core-android`, `-a2a`, `-webserver`, `-integrations`, `-litertlm-{jvm,android}`, `-mlkit-android`, `-processor`. 0.8.0 adds BigQuery agent-analytics plugin and Java-friendly builders.

### Agent Creation

```kotlin
import com.google.adk.agents.llmagent.LlmAgent
import com.google.adk.models.gemini.Gemini

val agent = LlmAgent(
    name = "kotlin_agent",
    model = Gemini(name = "gemini-flash-latest"),
    instruction = Instruction("You are a helpful assistant."),
)
```

### Tool Creation

```kotlin
import com.google.adk.tools.functiontool.FunctionTool

val weatherTool = FunctionTool(
    name = "get_weather",
    description = "Get current weather for a city.",
    function = { args: Map<String, Any?> ->
        val city = args["city"] as String
        mapOf("temperature" to 22, "city" to city)
    }
)
```

### Memory and Artifacts

```kotlin
val memoryService = InMemoryMemoryService()
val artifactService = InMemoryArtifactService()

// In tools: context.loadArtifact(filename), context.listArtifacts()
```

---

## Official Examples

Browse complete working examples for each language:
- **Python**: https://github.com/google/adk-samples/tree/main/python/agents
- **Java**: https://github.com/google/adk-samples/tree/main/java/agents
- **TypeScript**: https://github.com/google/adk-samples/tree/main/typescript/agents
