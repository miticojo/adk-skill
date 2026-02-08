# ADK Multi-Language Reference

ADK supports Python, Java, Go, and TypeScript. Core concepts (agents, tools, state, callbacks) are the same across languages. This reference covers language-specific patterns.

## Language Overview

| | Python | Java | Go | TypeScript |
|--|--------|------|----|------------|
| **Package** | `google-adk` | `com.google.adk:google-adk` | `google.golang.org/adk` | `@google/adk` |
| **Min version** | Python 3.10+ | Java 17+ | Go 1.24+ | Node.js 24+ |
| **Install** | `pip install google-adk` | Maven/Gradle | `go get` | `npm install @google/adk` |
| **Agent pattern** | Constructor kwargs | Builder pattern | Struct config | Constructor object |
| **Tool pattern** | Function + docstring | `@Schema` annotations | Struct types | Zod schemas |
| **Runner** | `InMemoryRunner` (async) | `InMemoryRunner` (RxJava) | Launcher | `InMemoryRunner` |
| **Entry point** | `root_agent` variable | `ROOT_AGENT` static field | `main()` func | `export rootAgent` |
| **CLI** | `adk run` / `adk web` | `mvn exec:java` | `go run` | `npx adk run` / `npx adk web` |

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
        <version>0.5.0</version>
    </dependency>
    <dependency>
        <groupId>com.google.adk</groupId>
        <artifactId>google-adk-dev</artifactId>
        <version>0.5.0</version>
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
            .model("gemini-2.5-flash")
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
    .name("researcher").model("gemini-2.5-flash")
    .instruction("Research the topic.").outputKey("research")
    .build();

LlmAgent writer = LlmAgent.builder()
    .name("writer").model("gemini-2.5-flash")
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

```bash
go mod init my-agent/main
go get google.golang.org/adk
go mod tidy
```

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

    model, err := gemini.NewModel(ctx, "gemini-2.5-flash",
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
    model: 'gemini-2.5-flash',
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
    name: 'researcher', model: 'gemini-2.5-flash',
    instruction: 'Research the topic.', outputKey: 'research',
});

const writer = new LlmAgent({
    name: 'writer', model: 'gemini-2.5-flash',
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
    model: 'gemini-2.5-flash',
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

---

## Official Examples

Browse complete working examples for each language:
- **Python**: https://github.com/google/adk-samples/tree/main/python/agents
- **Java**: https://github.com/google/adk-samples/tree/main/java/agents
- **TypeScript**: https://github.com/google/adk-samples/tree/main/typescript/agents
