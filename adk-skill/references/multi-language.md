# ADK Multi-Language Reference

ADK supports Python, Java, Go, Kotlin, and TypeScript. Core concepts (agents, tools, state, callbacks) are the same across languages. This reference covers language-specific patterns.

## Language Overview

Versions below are the verified reference targets, not a promise of identical APIs.

| | Python | Java | Go | Kotlin | TypeScript |
|--|--------|------|----|--------|------------|
| **Package** | `google-adk` | `com.google.adk:google-adk` | `google.golang.org/adk/v2` | `com.google.adk:google-adk-kotlin-core` | `@google/adk` |
| **Toolchain** | Python 3.11+ | JDK 17+ | Go 1.26.6+ | Kotlin 2.3.21, JDK 17+ | Node.js 24+ for these examples |
| **Verified version** | 2.13.0 | 1.13.0 | v2.6.0 | 1.4.0 | 2.3.0 |
| **Agent pattern** | Constructor kwargs | Builder | Struct config | Constructor kwargs / Java builder | Constructor object |
| **Tools** | Typed functions | `FunctionTool.create` | `functiontool.New` / `tool.Tool` | `@Tool` + KSP-generated tools | `FunctionTool` + Zod |
| **Entry point** | `root_agent` | `ROOT_AGENT` static field | `main()` + agent loader | `rootAgent` in an app/loader | `export rootAgent` |

### Capabilities by Implementation

- **Python 2.13 / Go v2.6:** graph and dynamic workflows, collaboration modes, retries, timeouts and human-input resumption.
- **TypeScript 2.3:** experimental graph/dynamic workflow engine; sub-agent modes are `single_turn` and `task`. Do not add Python's `chat` mode to the TypeScript config.
- **Java 1.13:** experimental `Node`, `Workflow`, graph-edge builder and execution of a graph/node as an invocation root; these features do not require a Java 2.x version. Pause/resume support arrived in 1.11; context caching in 1.12.
- **Kotlin 1.4:** generally available core (since 1.0), plus experimental graphs, typed function nodes, dynamic `Context.runNode`, fan-out, retries and human-input resumption. Workflow APIs require `@OptIn(ExperimentalWorkflowApi::class)`.

[Toolchain declarations](https://github.com/google/adk-kotlin/blob/v1.4.0/build.gradle.kts) target Kotlin 2.1 metadata for the SDK itself, but the resolved Ktor 3.6 dependencies carry Kotlin 2.3 metadata. Use Kotlin 2.3.21 for the JVM examples; compiling this dependency graph with 2.1.20 fails metadata checks.

Go also maintains a v1 module (`google.golang.org/adk`); all Go examples here target `/v2`. LiteRT-LM requires JDK 21+; ML Kit remains a separate beta Android module.

Source targets: [Python 2.13.0](https://github.com/google/adk-python/releases/tag/v2.13.0), [Java 1.13.0](https://github.com/google/adk-java/releases/tag/v1.13.0), [Go v2.6.0](https://github.com/google/adk-go/releases/tag/v2.6.0), [Kotlin 1.4.0](https://github.com/google/adk-kotlin/releases/tag/v1.4.0), [TypeScript 2.3.0](https://github.com/google/adk-js/releases/tag/main-v2.3.0). Verify the target SDK before porting Python-specific options.

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
        <version>1.13.0</version>
    </dependency>
    <dependency>
        <groupId>com.google.adk</groupId>
        <artifactId>google-adk-dev</artifactId>
        <version>1.13.0</version>
    </dependency>
</dependencies>
```

### Agent Creation (Builder Pattern)

```java
package com.example.agent;

import java.util.Map;
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
        if (city == null || city.isBlank()) {
            throw new IllegalArgumentException("city must not be blank");
        }
        return Map.of("city", city, "temperature", "22C", "conditions", "sunny");
    }
}
```

### Tools with @Schema Annotations

The following is a method fragment to place inside a class. Java tools are static methods with `@Schema` annotations on both the method and parameters:

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

Construction fragment; import `LlmAgent` and `SequentialAgent` from `com.google.adk.agents`:

```java
LlmAgent researcher = LlmAgent.builder()
    .name("researcher").model("gemini-flash-latest")
    .instruction("Research the topic.").outputKey("research")
    .build();

LlmAgent writer = LlmAgent.builder()
    .name("writer").model("gemini-flash-latest")
    .instruction("Write a report using {research}.")
    .build();

SequentialAgent pipeline = SequentialAgent.builder()
    .name("pipeline").subAgents(researcher, writer)
    .build();
```

### Runner and Testing

Save as `AgentCliRunner.java` alongside `MyAgent.java`; this runs a real model and needs credentials.

```java
package com.example.agent;

import com.google.adk.runner.InMemoryRunner;
import com.google.adk.sessions.Session;
import com.google.genai.types.Content;
import com.google.genai.types.Part;

public class AgentCliRunner {
    public static void main(String[] args) {
        InMemoryRunner runner = new InMemoryRunner(MyAgent.ROOT_AGENT, "test");
        Session session = runner.sessionService()
            .createSession("test", "test_user").blockingGet();
        Content message = Content.fromParts(Part.fromText("Hello"));
        runner.runAsync("test_user", session.id(), message)
            .blockingForEach(event -> System.out.println(event.stringifyContent()));
    }
}
```

### Running

```bash
set -a
source .env
set +a
# CLI
mvn compile exec:java -Dexec.mainClass="com.example.agent.AgentCliRunner"
# Web UI
mvn compile exec:java -Dexec.mainClass="com.google.adk.web.AdkWebServer" \
    -Dexec.args="--adk.agents.source-dir=target --server.port=8000"
```

### MCP Tools (Java)

Connection construction fragment; attach the toolset to an agent and close it with the application's other resources. Prefer Streamable HTTP for new servers:

```java
import com.google.adk.tools.mcp.McpToolset;
import com.google.adk.tools.mcp.StreamableHttpServerParameters;

McpToolset toolset = new McpToolset(
    StreamableHttpServerParameters.builder()
        .url("http://127.0.0.1:5000/mcp").build());
```

### Java 1.9–1.13 Changes

- User-scoped in-memory artifacts now honor `user:` correctly (1.9).
- `google-adk-tokt` provides an opt-in bridge to the Kotlin engine; it is distinct from native Java graph execution (1.10+).
- Pause/resume overloads and branch-scoped tool confirmations (1.11+); resumed calls need the invocation ID and matching session.
- Context caching (`ContextCacheConfig`) and experimental graph types (1.12+); graph execution and edge builders (1.13).
- Dev server rejects cross-origin/loopback DNS-rebinding requests by default (1.13). Configure deployment authentication separately.

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

Go ships dual lines: v1 (`google.golang.org/adk`) and the v2.6 line (requires **Go 1.26.6+**, as declared in its `go.mod`):

```bash
go mod init my-agent/main
go get google.golang.org/adk/v2@v2.6.0
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

    "google.golang.org/adk/v2/agent"
    "google.golang.org/adk/v2/agent/llmagent"
    "google.golang.org/adk/v2/cmd/launcher"
    "google.golang.org/adk/v2/cmd/launcher/full"
    "google.golang.org/adk/v2/model/gemini"
    "google.golang.org/adk/v2/tool"
    "google.golang.org/adk/v2/tool/geminitool"
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
    config := &launcher.Config{AgentLoader: agent.NewSingleLoader(myAgent)}
    if err := l.Execute(ctx, config, os.Args[1:]); err != nil {
        log.Fatalf("Run failed: %v", err)
    }
}
```

### Running

```bash
set -a
source .env
set +a
go run agent.go                    # CLI mode
go run agent.go web api webui      # Web UI on localhost:8080
```

### Go 2.x Highlights (through v2.6.0)

- **Graph workflows**: static + dynamic graphs, conditional routing, fan-out/fan-in `JoinNode`, parallel workers, per-node retries/timeouts, HITL pause/resume.
- **Collaboration**: `LlmAgent` gains `chat`, `task`, `single_turn` modes with isolation-scoped history.
- **Context unification**: `ToolContext`+`CallbackContext` merged into a single `agent.Context` (`agent.StrictContextMock` in tests).
- **v2.1+**: platform `TaskRunner` seam; name-based model registry (`Register`/`NewLLM`); `PackTool`; `runner.NewInMemory`; `agentregistry` package (REST + discovery); `RemoteAgent`/`McpToolset` factories; auth credential providers; MCP per-request auth via `Config.Auth`.
- **v2.3+**: context compaction between and within invocations; nested workflow human-input resume fixes.
- **v2.4–v2.6**: REST authentication/authorization, loopback host protections, per-request A2A authentication, MCP metadata forwarding, and single-flight dynamic-node idempotency caching.
- **v2.5 migration**: `gcp.Client.RetrieveCredential` returns `*gcp.Retrieval`; read `.Credential` for the previous credential value. Callers using `gcp.NewProvider` are unaffected.

---

## TypeScript

### Project Structure

```
my-agent/
├── agent.ts        # Agent definition (exports rootAgent)
├── tools.ts        # Tool definitions (optional)
├── package.json
└── .env            # GOOGLE_API_KEY
```

### Setup

```bash
mkdir my-agent && cd my-agent
npm init --yes
npm pkg set type="module"
npm pkg set main="agent.ts"
npm install @google/adk@2.3.0 @google/genai@2.31.0 zod@4.6.7
npm install -D @google/adk-devtools@2.3.0
```

### Agent Creation (Constructor)

Save as `agent.ts`; the next example defines its imported `tools.ts`:

```typescript
import { LlmAgent } from '@google/adk';
import { getWeather } from './tools.js';

export const rootAgent = new LlmAgent({
    name: 'my_agent',
    model: 'gemini-flash-latest',
    description: 'Agent description',
    instruction: 'Detailed system prompt...',
    tools: [getWeather],
});
```

### Tools (Zod Schemas)

Save as `tools.ts`. TypeScript tools use `FunctionTool` with Zod for parameter validation:

```typescript
import { FunctionTool } from '@google/adk';
import { z } from 'zod';

export const getWeather = new FunctionTool({
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

Alternative `agent.ts` using template agents (supported but deprecated in 2.x):

```typescript
import { LlmAgent, SequentialAgent } from '@google/adk';

const researcher = new LlmAgent({
    name: 'researcher', model: 'gemini-flash-latest',
    instruction: 'Research the topic.', outputKey: 'research',
});

const writer = new LlmAgent({
    name: 'writer', model: 'gemini-flash-latest',
    instruction: 'Write a report using {research}.',
});

export const rootAgent = new SequentialAgent({
    name: 'pipeline',
    subAgents: [researcher, writer],
});
```

### Callbacks (TypeScript)

Alternative `agent.ts`. Callbacks receive a single parameter object, not Python-style positional arguments:

```typescript
import { LlmAgent } from '@google/adk';
import { getWeather } from './tools.js';

export const rootAgent = new LlmAgent({
    name: 'guarded_agent',
    model: 'gemini-flash-latest',
    instruction: '...',
    tools: [getWeather],
    beforeToolCallback: ({ tool, args, context }) => {
        if (tool.name === 'dangerous_tool') {
            return { error: 'Tool blocked by policy' };
        }
        return undefined; // proceed
    },
    beforeModelCallback: ({ context, request }) => {
        // Rate limiting, safety checks
        return undefined;
    },
});
```

### Runner and Testing

Save as `run.ts` beside `agent.ts`; this calls a real model and needs credentials. Compile with TypeScript using `module` and `moduleResolution` set to `NodeNext`:

```typescript
import { InMemoryRunner, isFinalResponse } from '@google/adk';
import { createUserContent } from '@google/genai';
import { rootAgent } from './agent.js';

const runner = new InMemoryRunner({ agent: rootAgent, appName: 'test' });
const session = await runner.sessionService.createSession({
    userId: 'test_user', appName: 'test',
});

const content = createUserContent('Hello');
for await (const event of runner.runAsync({
    userId: 'test_user', sessionId: session.id, newMessage: content,
})) {
    if (isFinalResponse(event)) {
        console.log((event.content?.parts ?? [])
            .filter(part => !part.thought)
            .map(part => part.text ?? '').join(''));
    }
}
```

### Running

```bash
npx adk run agent.ts        # CLI mode
npx adk web                 # Web UI on localhost:8000
```

### TypeScript 2.0–2.3 Changes

- **Workflow engine core** (`@experimental`): graphs, node registry, dynamic scheduling via `ctx.runNode()`, `JoinNode`, HITL utils, retry configs.
- **Breaking:** `BaseAgent extends BaseNode` — agents carry `rerunOnResume`, `waitForOutput`, `retryConfig`, `timeout`, `inputSchema`/`outputSchema`. `InvocationContext.agent` is optional; use `requireAgent(ctx)`.
- **Deprecated:** `SequentialAgent`/`ParallelAgent`/`LoopAgent` (graph workflows replace them); `LLMAgentWrapper` removed.
- **Collaboration:** node config `mode: 'single_turn' | 'task'` — no `chat` mode yet.
- Plugins with before/after-node callbacks, `RoutedAgent`/`RoutedLlm`, `Runner.runLive`, tool confirmations and `SkillToolset` are available; use each TypeScript symbol rather than Python keyword names.
- 2.1–2.3 fixes confirmation resolution across runtimes, OAuth PKCE, literal escaped instruction braces, abort propagation in routed models and history sealing after cancellation. 2.3 callbacks use `{context, request}` / `{tool, args, context}` objects.

---

## Cross-Language Comparison: Tool Definition

Tool-definition fragments (place Java methods inside a class; import `FunctionTool` and `z` for the TypeScript fragment):

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

**Go:** Use `tool/functiontool.New` with typed input/output structs for functions, built-in `geminitool.GoogleSearch{}`, or implement `tool.Tool`. Import all ADK packages from `google.golang.org/adk/v2`.

**Go v2:** Graph construction differs from Python; use the tagged `workflow` and `agent/workflowagent` samples instead of translating Python constructor names verbatim.

---

## Kotlin

ADK Kotlin 1.4.0 supports JVM and Android agents and is generally available at the core level. Experimental APIs (workflow, live, auth and some integrations) retain their own opt-in annotations. Import Kotlin SDK types from `com.google.adk.kt`, not the Java SDK's `com.google.adk` namespace.

### Installation

```kotlin
// build.gradle.kts: Kotlin/JVM project, JDK 17+, Kotlin 2.3.21
dependencies {
    implementation("com.google.adk:google-adk-kotlin-core:1.4.0")
}
```

For Maven/JVM use `google-adk-kotlin-core-jvm`. Add `google-adk-kotlin-webserver` for HTTP serving and `google-adk-kotlin-processor` via KSP for generated function tools. Android model backends are separate artifacts: Firebase AI (cloud), LiteRT-LM (on-device, JDK 21+), and ML Kit (beta, no tool calling).

### Agent Creation

```kotlin
import com.google.adk.kt.agents.Instruction
import com.google.adk.kt.agents.LlmAgent
import com.google.adk.kt.models.Gemini

val rootAgent = LlmAgent(
    name = "kotlin_agent",
    model = Gemini(name = "gemini-flash-latest"),
    instruction = Instruction("You are a helpful assistant."),
)
```

### Function Tools with KSP

The following is a service-class fragment. Configure the KSP plugin and `ksp("com.google.adk:google-adk-kotlin-processor:1.4.0")` in the build first:

```kotlin
import com.google.adk.kt.annotations.Param
import com.google.adk.kt.annotations.Tool

class WeatherService {
    @Tool
    fun getWeather(@Param("City to look up") city: String): Map<String, String> {
        require(city.isNotBlank()) { "city must not be blank" }
        return mapOf("city" to city, "conditions" to "sunny")
    }
}
```

KSP generates `WeatherService().generatedTools()` in the service's package; pass it as the `tools` argument to `LlmAgent`. `FunctionTool` is abstract in Kotlin: do not construct it with a Python-style `function=` lambda. For plain Java, `ReflectiveTools` is an alternative to KSP.

### Workflow Construction (Experimental)

Standalone construction fragment adapted from the tagged workflow samples; attach `rootNode` to `App(appName = "messages", rootNode = rootNode)` when running:

```kotlin
@file:OptIn(com.google.adk.kt.annotations.ExperimentalWorkflowApi::class)

import com.google.adk.kt.types.Content
import com.google.adk.kt.types.Role
import com.google.adk.kt.workflow.Start
import com.google.adk.kt.workflow.node
import com.google.adk.kt.workflow.workflow

val greet = node<Any?, Content>("greet") { _, _ ->
    Content.fromText(Role.MODEL, "Hello")
}
val rootNode = workflow("messages") {
    chain(Start, greet)
}
```

Kotlin 1.4 also adds `Context.runNode`, `parallelNode`, retries/timeouts, resumable human-input workflows, `EnvironmentToolset`, MCP shared across JVM/Android, and Claude/Chat Completions integrations. Use `AdkApiServer` for headless serving or `AdkDevServer` for the development UI; `AdkWebServer` was removed in 1.0. Session services that buffer writes expose `flush`; the runner flushes before final responses and at run completion.

[Tagged Kotlin examples](https://github.com/google/adk-kotlin/tree/v1.4.0/examples) include the complete build and imports for generated tools, memory, artifacts, workflow graphs, live interactions and Java interoperability.

---

## Official Examples

Browse complete examples for each language; pinned SDK repositories are the API reference for the versions above:
- **Python**: https://github.com/google/adk-samples/tree/main/python/agents
- **Java**: https://github.com/google/adk-java/tree/v1.13.0/examples
- **Go**: https://github.com/google/adk-go/tree/v2.6.0/examples
- **TypeScript**: https://github.com/google/adk-js/tree/main-v2.3.0/samples
- **Kotlin**: https://github.com/google/adk-kotlin/tree/v1.4.0/examples
