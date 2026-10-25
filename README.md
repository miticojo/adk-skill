# ADK Skill

[![release](https://github.com/miticojo/adk-skill/actions/workflows/release.yml/badge.svg)](https://github.com/miticojo/adk-skill/actions/workflows/release.yml)

An [Agent Skill](https://agentskills.io) for building single-agent and multi-agent systems with **Google's Agent Development Kit (ADK)** in **Python, Java, Go, Kotlin, and TypeScript**. Skill **2.2.0**, verified against **ADK Python 2.13.0** on **2026-10-25**. Covers graph/dynamic workflows, collaboration, cancellation, approvals, tools, memory, evaluation and deployment. Python examples require **Python 3.11+**; API availability and experimental status are specific to each SDK.

This skill gives your coding agent deep knowledge of ADK architecture, patterns, and best practices — covering workflow types, tools, callbacks, state management, memory, artifacts, multi-agent orchestration, testing, evaluation, and deployment across all supported languages.

See [release notes](CHANGELOG.md) for the proposed 2.2.0 release, compatibility changes and verification limits. Contributor and agent instructions live in [AGENTS.md](AGENTS.md); the update's phase record is in [tasks.md](tasks.md).

## What's Included

```
adk-skill/
├── SKILL.md                          # Core instructions (under 500 lines)
└── references/
    ├── a2a-protocol.md               # A2A protocol: expose, consume, agent cards
    ├── advanced-patterns.md          # Multi-agent, App config, Agent Config, Visual Builder, AG-UI, streaming, multi-model
    ├── design-patterns.md            # Agent design patterns & best practices
    ├── evaluation.md                 # Quality/efficiency metrics, multi-turn evaluator, user simulation
    ├── memory-artifacts.md           # In-memory/SQLite/Vertex/MongoDB memory, versioned artifacts
    ├── multi-language.md             # Java, Go, Kotlin, TypeScript patterns
    ├── tools-reference.md            # FunctionTool, MCP, Toolbox, RAG, SkillToolset, OpenAPI, tool auth, confirmations
    ├── troubleshooting.md            # Common errors, debugging, 1.x→2.0 migration, performance tips
    └── workflows.md                  # Graph-based routing, dynamic workflows, HITL, parallel, custom IDs
```

**SKILL.md** covers project structure, all 4 workflow types (Graph-based `Workflow`, Dynamic `@node`, Collaborative with `mode`, Template `SequentialAgent`/`ParallelAgent`/`LoopAgent`), function tools, OpenAPI tools, AgentTool, MCP integration, agent-as-MCP-server (`to_mcp_server`), A2A remote agents, memory service, artifacts, callbacks, state management with Jinja2 instruction templating, structured output, testing with InMemoryRunner, YAML-based Agent Config, model selection (`gemini-3.5-flash` default), design patterns with key rules, decision guides, and links to external documentation.

**Reference files** provide advanced patterns loaded on demand:
- **a2a-protocol.md** — A2A (Agent-to-Agent) protocol: exposing agents via `to_a2a()` and `adk api_server`, consuming with `RemoteA2aAgent`, versioned cards, native task delegation, authentication, metadata propagation, testing, troubleshooting
- **advanced-patterns.md** — App object (compaction, resumability, context caching), plugins (BasePlugin + error hooks), AG-UI integration (CopilotKit), managed agents (Preview), ambient agents (Pub/Sub & Eventarc triggers), multi-model support (Claude, Ollama, LiteLLM, vLLM, OCI GenAI, OpenAI integrations), LiveKit/CascadeLive, OpenTelemetry migration, hierarchical workflows, deployment (Cloud Run, GKE, Vertex AI Agent Engine), Agent Config (YAML-based agents), Visual Builder, anti-patterns
- **design-patterns.md** — 15 agent design patterns (sequential pipeline, fan-out/fan-in, reflection, routing, planning, error handling, HITL, guardrails, resource optimization, reasoning, context engineering, prompting), universal anti-patterns table, multi-agent collaboration models, state management rules, memory architecture
- **evaluation.md** — eval data formats (EvalSet/EvalCase), quality and informational efficiency metrics, tool trajectory matching, rubric-based evaluation, `RubricBasedMultiTurnTrajectoryEvaluator` (2.2+), user simulation, `GEPARootAgentOptimizer` (2.3+), pytest integration, CLI and web UI
- **memory-artifacts.md** — Memory Service (InMemory, SQLite, VertexAiMemoryBank, VertexAiRag, experimental MongoDB), PreloadMemory/LoadMemory tools, auto-save via callback, multiple memory services; Artifact Service (InMemory, File, GCS backends), save/load/list artifacts, LoadArtifactsTool, user vs. session namespacing
- **multi-language.md** — per-language verified versions and capability boundaries; Java (builder pattern, @Schema annotations, ClassPathSkillSource), Go (v2 graph engine, JoinNode, collab modes, agent.Context), Kotlin (1.4 stable core, experimental graphs, JVM/Android), TypeScript (2.3 workflow engine, Zod schemas, RoutedAgent), cross-language comparison table
- **tools-reference.md** — FunctionTool, ToolboxToolset, MCP connections (stdio + streamable HTTP, elicitation), agent-as-MCP-server (`to_mcp_server`), Eventarc toolset, RAG retrieval, stable SkillToolset (opt-in lifecycle, discovery, script artifacts), ModelConsultTool, Agent Registry, OpenAPI tools, media in function responses, tool authentication (API keys, OAuth), tool action confirmations (HITL), LoadArtifactsTool, sandboxed code execution environments, long-running tools, best practices
- **troubleshooting.md** — setup errors, runtime issues, ADK 1.x→2.0 migration (6 breaking changes with fixes), Go v2 import path and `NewEvent` changes, 2.7→2.13 migration, event schema updates, performance tips
- **workflows.md** — Graph-based routing (conditional, multi-route, fan-out, `__DEFAULT__` fallback, edge syntax reference), dynamic workflows (loops, branching, parallel workers, custom execution IDs, retry/timeout node options), Human-in-the-Loop (graph and dynamic patterns, node/tool confirmation and authentication resumption), cancellation, failed-node replay, collaboration modes in workflows, known limitations

The skill also references the official [ADK documentation](https://adk.dev/llms.txt) and [ADK samples](https://github.com/google/adk-samples) for always up-to-date API details.

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

Use the skill for **Google ADK / google-adk projects** in Python, Java, Go, Kotlin or TypeScript:

- Build or migrate ADK agents, graph/dynamic workflows and collaborative teams.
- Add ADK tools, callbacks, MCP/A2A integrations, state, memory or artifacts.
- Evaluate, test, deploy or debug ADK applications, including approval and recovery flows.
- Configure ADK skills, models, streaming or optional integrations.

Standalone Gemini API tasks and LangChain, CrewAI or AutoGen projects are outside this skill's activation scope.

## Topics Covered

| Area | What You Get |
|------|-------------|
| Languages | Python, Java, Go, Kotlin, TypeScript with language-specific patterns |
| Project Setup | Directory structure, `__init__.py`, `root_agent`, `pyproject.toml`, YAML Agent Config |
| Workflow Types | Graph-based (`Workflow`), Dynamic (`@node` + `ctx.run_node()`), Collaborative (`mode`), Template (Sequential, Parallel, Loop) |
| Agent Modes | `chat`, `task`, `single_turn` collaboration modes with comparison table |
| Tools | Function tools, ToolContext, AgentTool, google_search, MCPToolset, OpenAPIToolset, SkillToolset, RemoteA2aAgent, tool auth, tool confirmations, LoadArtifactsTool |
| Memory | `MemoryService` (in-memory, SQLite, Vertex and experimental MongoDB), `PreloadMemoryTool`, `LoadMemory`, cross-session search, auto-save |
| Artifacts | `ArtifactService` (InMemory, File, GCS), `save_artifact`/`load_artifact`/`list_artifacts`, session vs. user scope |
| Callbacks & Plugins | Agent/tool/model lifecycle hooks; `BasePlugin` for global cross-cutting concerns |
| State & Sessions | Session state, scopes (`app:`, `user:`), context compaction, session rewind |
| Output | Pydantic `output_schema` + `output_key` for structured data |
| HITL | `RequestInput` events, `rerun_on_resume`, dynamic workflow patterns |
| Testing | ADK runner examples; maintained offline regressions with Python `unittest` |
| Evaluation | Quality + efficiency metrics, `RubricBasedMultiTurnTrajectoryEvaluator`, user simulation, `GEPARootAgentOptimizer`, CLI, web UI |
| Design Patterns | 9 patterns (graph, dynamic, collaborative, fan-out/fan-in, reflection, routing, fallback, guardrails, tiering) |
| A2A Protocol | Expose via `to_a2a()`, consume via `RemoteA2aAgent`, agent cards, Python + Go |
| Models | `gemini-3.5-flash` (default), rolling aliases (`gemini-flash-latest`), Gemini 3.1 Pro, Claude, Ollama, LiteLLM, vLLM, OCI GenAI, OpenAI (`integrations.openai`) |
| Agent Config | YAML-based agent definition, `adk create --type=config`, Visual Builder |
| Streaming | Gemini Live API, `LiveRequestQueue`, experimental LiveKit/CascadeLive; graph workflows do not support Live |
| UI Integration | AG-UI protocol, CopilotKit, shared state, generative UI |
| Deployment | `adk run/web/api_server`, Cloud Run, GKE, Vertex AI Agent Engine, FastAPI, sandboxed code execution (E2B, Daytona, Cloud Run) |
| Migration | ADK 1.x→2.0 and 2.7→2.13: Python version, resume, cancellation, confirmations, telemetry |
| External Docs | Links to official ADK docs and Google sample agents |

## Effectiveness

Historical benchmark from an earlier skill version; not rerun for ADK 2.13. Tested by asking the same ADK architecture question (multi-source parallel research with validation, error handling, and user review) under three conditions:

| Condition | Score | vs Baseline |
|-----------|-------|-------------|
| No skill | 33/100 | -- |
| Skill without design patterns | 60/100 | +82% |
| **Skill with design patterns** | **86/100** | **+161%** |

Largest improvements from design patterns: architecture correctness (4 → 9), anti-pattern avoidance (2 → 9), structured output (1 → 9). The design patterns reference transformed outputs from single "God Agent" implementations into properly composed multi-agent pipelines with fan-out/fan-in, layered fallback, model tiering, and structured data flow.

## Verification

Reference SDKs: Python **2.13.0**, Java **1.13.0**, Go **2.6.0**, Kotlin **1.4.0**, TypeScript **2.3.0**. Examples and source links use those versions, not unreleased upstream changes.

Offline Python regression tests execute documentation examples and check routing, parallel joins, approval/rejection, failed-node resumption, abort, artifacts, memory isolation/persistence, skill lifecycle, A2A startup/cards, model failover, callbacks and evaluation schemas. They make no model or cloud calls:

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python "google-adk[a2a,db,eval,openai,mcp]==2.13.0"
.venv/bin/python -m unittest discover -s validation -v
```

Native examples also passed local compilation/type checking with Go 1.26.6, JDK 17.0.21, Kotlin 2.3.21 and TypeScript 7.0.2. Kotlin 2.1.20 fails on transitive dependencies carrying 2.3 metadata; use 2.3.21 for the documented build. CI runs the Python regressions; the native checks were performed during this update.

Cloud deployment, real model conversations/evaluations, Live audio, Android and KSP generation require separate integration tests with authorized services and credentials. Offline checks do not establish model availability or production behavior.

## Quality Gates & Releases

Every skill/test PR and release runs through automated gates ([workflow](.github/workflows/release.yml)):

| Gate | Tool | Current result |
|------|------|----------------|
| Spec validation (schema, PII, license, Unicode, lint) | [SkillEvaluator](https://github.com/NVIDIA/SkillEvaluator) Tier-1 | 6/6 pass |
| Quality grade | SkillEvaluator | **A — 91.2/100** |
| Security scan (70 patterns, static) | [SkillSpector](https://github.com/NVIDIA/SkillSpector) | SAFE — 0 open issues |
| Executable Python examples and schemas | `unittest`, ADK 2.13.0 | 23 tests pass |

**Releases**: pushing a tag (`v*`) runs the same gates and publishes a GitHub Release with the scan/quality reports attached (see [v2.1.0](https://github.com/miticojo/adk-skill/releases/tag/v2.1.0)). Accepted scanner false positives are recorded in `.skillspector-baseline.yaml`.

Human-written release notes live in [CHANGELOG.md](CHANGELOG.md). Version 2.2.0 stays marked **Unreleased** until publication; a branch push or pull request does not publish it. The tag workflow generates GitHub release notes automatically. Merge and tag publication are separate maintainer actions.

**Verify a release yourself** — both tools are deterministic and keyless:

```bash
# Run from the checkout you want to verify.
uv tool install "skillspector @ git+https://github.com/NVIDIA/SkillSpector.git@v2.9.6"
uv tool install --python 3.13 "skillevaluator[all] @ git+https://github.com/NVIDIA/SkillEvaluator.git@v0.1.0"
skillspector scan adk-skill/ --no-llm --baseline .skillspector-baseline.yaml   # → SAFE, 0 open
skillevaluator quality-check adk-skill                                        # → A 91.2
```

## License

MIT
