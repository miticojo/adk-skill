# ADK Skill

An [Agent Skill](https://agentskills.io) for building single-agent and multi-agent systems with **Google's Agent Development Kit (ADK)** in **Python, Java, Go, Kotlin, and TypeScript**. Updated for **ADK 2.0+** with graph-based workflows, dynamic workflows, collaborative agents, memory service, and artifacts.

This skill gives your coding agent deep knowledge of ADK architecture, patterns, and best practices — covering workflow types, tools, callbacks, state management, memory, artifacts, multi-agent orchestration, testing, evaluation, and deployment across all supported languages.

## What's Included

```
adk-skill/
├── SKILL.md                          # Core instructions (500 lines)
└── references/
    ├── a2a-protocol.md               # A2A protocol: expose, consume, agent cards
    ├── advanced-patterns.md          # Multi-agent, App config, Agent Config, Visual Builder, AG-UI, streaming, multi-model
    ├── design-patterns.md            # Agent design patterns & best practices
    ├── evaluation.md                 # Eval data formats, 8 metrics, multi-turn evaluator, user simulation
    ├── memory-artifacts.md           # Memory Service (3 backends), Artifact Service (binary data persistence)
    ├── multi-language.md             # Java, Go, Kotlin, TypeScript patterns
    ├── tools-reference.md            # FunctionTool, MCP, Toolbox, RAG, SkillToolset, OpenAPI, tool auth, confirmations
    ├── troubleshooting.md            # Common errors, debugging, 1.x→2.0 migration, performance tips
    └── workflows.md                  # Graph-based routing, dynamic workflows, HITL, parallel, custom IDs
```

**SKILL.md** covers project structure, all 4 workflow types (Graph-based `Workflow`, Dynamic `@node`, Collaborative with `mode`, Template `SequentialAgent`/`ParallelAgent`/`LoopAgent`), function tools, OpenAPI tools, AgentTool, MCP integration, A2A remote agents, memory service, artifacts, callbacks, state management, structured output, testing with InMemoryRunner, YAML-based Agent Config, model selection (Gemini 3 Flash default), design patterns with key rules, decision guides, and links to external documentation.

**Reference files** provide advanced patterns loaded on demand:
- **a2a-protocol.md** — A2A (Agent-to-Agent) protocol: exposing agents via `to_a2a()` and `adk api_server`, consuming with `RemoteA2aAgent`, agent cards, Go patterns, metadata propagation, testing, troubleshooting
- **advanced-patterns.md** — App object, plugins (BasePlugin), AG-UI integration (CopilotKit), multi-model support (Claude, Ollama, LiteLLM, vLLM), hierarchical workflows, deployment, Agent Config (YAML-based agents), Visual Builder, anti-patterns
- **design-patterns.md** — 15 agent design patterns (sequential pipeline, fan-out/fan-in, reflection, routing, planning, error handling, HITL, guardrails, resource optimization, reasoning, context engineering, prompting), universal anti-patterns table, multi-agent collaboration models, state management rules, memory architecture
- **evaluation.md** — eval data formats (EvalSet/EvalCase), all 8 built-in metrics, tool trajectory matching, rubric-based evaluation, `RubricBasedMultiTurnTrajectoryEvaluator` (2.2+), user simulation, `GEPARootAgentOptimizer` (2.3+), pytest integration, CLI and web UI
- **memory-artifacts.md** — Memory Service (InMemory, VertexAiMemoryBank, VertexAiRag backends), PreloadMemory/LoadMemory tools, auto-save via callback, multiple memory services; Artifact Service (InMemory, GCS backends), save/load/list artifacts, LoadArtifactsTool, user vs. session namespacing
- **multi-language.md** — Java (builder pattern, @Schema annotations), Go (v2 graph engine, `workflow.NewFunctionNode`), Kotlin (constructor kwargs, `FunctionTool`), TypeScript (Zod schemas), cross-language comparison table
- **tools-reference.md** — FunctionTool, ToolboxToolset, MCP connections (stdio + streamable HTTP), RAG retrieval, SkillToolset, APIRegistryToolset, OpenAPI tools, tool authentication (API keys, OAuth), tool action confirmations (HITL), LoadArtifactsTool, long-running tools, best practices
- **troubleshooting.md** — setup errors, runtime issues, ADK 1.x→2.0 migration (6 breaking changes with fixes), Go v2 import path and `NewEvent` changes, event schema updates, performance tips
- **workflows.md** — Graph-based routing (conditional, multi-route, data flow), dynamic workflows (loops, branching, parallel execution, custom execution IDs), Human-in-the-Loop (graph and dynamic patterns), known limitations

The skill also references the official [ADK documentation](https://google.github.io/adk-docs/llms.txt) and [ADK samples](https://github.com/google/adk-samples) for always up-to-date API details.

## Install

### Quick Install (recommended)

Install across all your agents with a single command using the [Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add miticojo/adk-skill
```

The CLI auto-detects installed agents (Claude Code, Cursor, Windsurf, OpenCode, etc.) and installs the skill to each one.

### Claude Code

```bash
claude mcp add-skill https://github.com/miticojo/adk-skill/tree/main/adk-skill
```

Or manually:

```bash
git clone https://github.com/miticojo/adk-skill.git
cp -r adk-skill/adk-skill ~/.claude/skills/
```

### Google Antigravity

```bash
cp -r adk-skill/adk-skill ~/.gemini/antigravity/skills/
```

Or for workspace-only scope, copy to `<your-project>/.agent/skills/`. See the [Antigravity skills docs](https://antigravity.google/docs/skills) for details.

### Gemini CLI

```bash
cp -r adk-skill/adk-skill ~/.gemini/skills/
```

### OpenCode

```bash
cp -r adk-skill/adk-skill ~/.config/opencode/skills/
```

### OpenAI Codex

```bash
cp -r adk-skill/adk-skill ~/.codex/skills/
```

### Cursor / Windsurf / Other Agents

Copy the `adk-skill/` folder into your project's `.cursor/skills/`, `.windsurf/skills/`, or equivalent agent skills directory. The skill follows the open [Agent Skills specification](https://agentskills.io/specification) and works with any compatible agent.

### Manual (any agent)

Just copy the `adk-skill/` folder wherever your agent reads skills from. The only required file is `SKILL.md` — the `references/` folder provides additional context loaded on demand.

## When Does It Activate?

The skill activates when you mention:
- **ADK**, **google-adk**, **Google Agent Development Kit**
- Building **AI agents** with **Gemini** in **Python, Java, Go, Kotlin, or TypeScript**
- **Graph-based workflows**, **dynamic workflows**, **collaborative agents**
- **Multi-agent** architectures or **agent orchestration**
- **Sequential**, **parallel**, or **loop** workflows
- Agent **tools**, **callbacks**, **state management**
- **Agent memory**, **cross-session memory**, **memory service**
- **Artifacts**, **binary data persistence**, **LoadArtifactsTool**
- **OpenAPI tools**, **tool authentication**, **tool confirmations**
- **Agent Config**, **YAML-based agents**, **Visual Builder**
- **Deploying agents**, **writing agent tests**, **agent evaluation**
- **A2A protocol**, **remote agents**, **agent-to-agent** communication
- Integrating **MCP tools** or **Agent Skills** with ADK
- **Streaming**, **Live API**, **AG-UI**, **plugins**
- **ADK 1.x to 2.0 migration**

## Topics Covered

| Area | What You Get |
|------|-------------|
| Languages | Python, Java, Go, Kotlin, TypeScript with language-specific patterns |
| Project Setup | Directory structure, `__init__.py`, `root_agent`, `pyproject.toml`, YAML Agent Config |
| Workflow Types | Graph-based (`Workflow`), Dynamic (`@node` + `ctx.run_node()`), Collaborative (`mode`), Template (Sequential, Parallel, Loop) |
| Agent Modes | `chat`, `task`, `single_turn` collaboration modes with comparison table |
| Tools | Function tools, ToolContext, AgentTool, google_search, MCPToolset, OpenAPIToolset, SkillToolset, RemoteA2aAgent, tool auth, tool confirmations, LoadArtifactsTool |
| Memory | `MemoryService` (3 backends), `PreloadMemoryTool`, `LoadMemory`, cross-session search, auto-save |
| Artifacts | `ArtifactService` (InMemory, GCS), `save_artifact`/`load_artifact`/`list_artifacts`, session vs. user scope |
| Callbacks & Plugins | Agent/tool/model lifecycle hooks; `BasePlugin` for global cross-cutting concerns |
| State & Sessions | Session state, scopes (`app:`, `user:`), context compaction, session rewind |
| Output | Pydantic `output_schema` + `output_key` for structured data |
| HITL | `RequestInput` events, `rerun_on_resume`, dynamic workflow patterns |
| Testing | `InMemoryRunner` with pytest |
| Evaluation | 8 metrics, `RubricBasedMultiTurnTrajectoryEvaluator`, user simulation, `GEPARootAgentOptimizer`, CLI, web UI |
| Design Patterns | 9 patterns (graph, dynamic, collaborative, fan-out/fan-in, reflection, routing, fallback, guardrails, tiering) |
| A2A Protocol | Expose via `to_a2a()`, consume via `RemoteA2aAgent`, agent cards, Python + Go |
| Models | Gemini 3 Flash (default), Gemini 3 Pro, Claude, Ollama, LiteLLM, vLLM |
| Agent Config | YAML-based agent definition, `adk create --type=config`, Visual Builder |
| Streaming | Gemini Live API, `LiveRequestQueue`, bidirectional audio/video |
| UI Integration | AG-UI protocol, CopilotKit, shared state, generative UI |
| Deployment | `adk run/web/api_server`, Cloud Run, Vertex AI, FastAPI |
| Migration | ADK 1.x→2.0 breaking changes (6 areas) with fix code examples |
| External Docs | Links to official ADK docs and Google sample agents |

## Effectiveness

Tested by asking the same ADK architecture question (multi-source parallel research with validation, error handling, and user review) under three conditions:

| Condition | Score | vs Baseline |
|-----------|-------|-------------|
| No skill | 33/100 | -- |
| Skill without design patterns | 60/100 | +82% |
| **Skill with design patterns** | **86/100** | **+161%** |

Largest improvements from design patterns: architecture correctness (4 → 9), anti-pattern avoidance (2 → 9), structured output (1 → 9). The design patterns reference transformed outputs from single "God Agent" implementations into properly composed multi-agent pipelines with fan-out/fan-in, layered fallback, model tiering, and structured data flow.

## License

MIT
