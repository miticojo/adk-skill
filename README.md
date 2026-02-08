# ADK Skill

An [Agent Skill](https://agentskills.io) for building single-agent and multi-agent systems with **Google's Agent Development Kit (ADK)** in **Python, Java, Go, and TypeScript**.

This skill gives your coding agent deep knowledge of ADK architecture, patterns, and best practices -- covering agent types, tools, callbacks, state management, multi-agent orchestration, testing, and deployment across all supported languages.

## What's Included

```
adk-skill/
├── SKILL.md                          # Core instructions (478 lines)
└── references/
    ├── tools-reference.md            # FunctionTool, MCP, Toolbox, RAG patterns
    ├── advanced-patterns.md          # Multi-agent, deployment, safety, config
    ├── evaluation.md                 # Eval data formats, 8 metrics, user simulation
    └── multi-language.md             # Java, Go, TypeScript patterns
```

**SKILL.md** covers project structure, all 4 agent types (LlmAgent, SequentialAgent, ParallelAgent, LoopAgent), function tools, AgentTool, MCP integration, callbacks, state management, structured output, testing with InMemoryRunner, decision guides, and links to external documentation.

**Reference files** provide advanced patterns loaded on demand:
- **tools-reference.md** -- FunctionTool, ToolboxToolset, MCP connections, RAG retrieval, long-running tools, best practices
- **advanced-patterns.md** -- hierarchical workflows, parallel writers with judge, agent transfer, rate limiting, guardrails, Cloud Run/Vertex AI deployment, FastAPI, configuration, anti-patterns
- **evaluation.md** -- eval data formats (EvalSet/EvalCase), all 8 built-in metrics, tool trajectory matching, rubric-based evaluation, user simulation, pytest integration, CLI and web UI, TypeScript support
- **multi-language.md** -- Java (builder pattern, @Schema annotations, Maven), Go (struct config, launcher), TypeScript (Zod schemas, npm), cross-language tool comparison

The skill also references the official [ADK documentation](https://google.github.io/adk-docs/llms.txt) and [ADK samples](https://github.com/google/adk-samples) for always up-to-date API details.

## Install

### Claude Code

```bash
claude mcp add-skill https://github.com/miticojo/adk-skill/tree/main/adk-skill
```

Or manually copy the folder:

```bash
# Clone the repo
git clone https://github.com/miticojo/adk-skill.git

# Copy the skill to your Claude Code skills directory
cp -r adk-skill/adk-skill ~/.claude/skills/
```

### Google Antigravity

```bash
# Copy to Antigravity global skills directory
cp -r adk-skill/adk-skill ~/.gemini/antigravity/skills/
```

Or for workspace-only scope, copy to `<your-project>/.agent/skills/`. See the [Antigravity skills docs](https://antigravity.google/docs/skills) for details.

### Gemini CLI

```bash
# Copy to Gemini CLI skills directory
cp -r adk-skill/adk-skill ~/.gemini/skills/
```

### OpenCode

```bash
# Copy to OpenCode skills directory
cp -r adk-skill/adk-skill ~/.config/opencode/skills/
```

### OpenAI Codex

```bash
# Copy to Codex skills directory
cp -r adk-skill/adk-skill ~/.codex/skills/
```

### Cursor / Windsurf / Other Agents

Copy the `adk-skill/` folder into your project's `.cursor/skills/`, `.windsurf/skills/`, or equivalent agent skills directory. The skill follows the open [Agent Skills specification](https://agentskills.io/specification) and works with any compatible agent.

### Manual (any agent)

Just copy the `adk-skill/` folder wherever your agent reads skills from. The only required file is `SKILL.md` -- the `references/` folder provides additional context loaded on demand.

## When Does It Activate?

The skill activates when you mention:
- **ADK**, **google-adk**, **Google Agent Development Kit**
- Building **AI agents** with **Gemini** in **Python, Java, Go, or TypeScript**
- **Multi-agent** architectures or **agent orchestration**
- **Sequential**, **parallel**, or **loop** agent workflows
- Agent **tools**, **callbacks**, **state management**
- **Deploying agents**, **writing agent tests**
- Integrating **MCP tools** with ADK

## Topics Covered

| Area | What You Get |
|------|-------------|
| Languages | Python, Java, Go, TypeScript with language-specific patterns |
| Project Setup | Directory structure, `__init__.py`, `root_agent`, `pyproject.toml` |
| Agent Types | LlmAgent, SequentialAgent, ParallelAgent, LoopAgent, composition |
| Tools | Function tools, ToolContext, AgentTool, google_search, MCPToolset |
| Callbacks | before/after agent, tool, and model hooks |
| State | Session state, scopes (`app:`, `user:`, `temp:`), data flow between agents |
| Output | Pydantic `output_schema` + `output_key` for structured data |
| Testing | `InMemoryRunner` with pytest |
| Evaluation | 8 metrics, `adk eval` CLI, pytest, web UI, user simulation |
| Patterns | Pipeline+validation, coordinator+specialists, parallel research, guardrails |
| Deployment | `adk run/web`, Cloud Run, Vertex AI, FastAPI |
| Safety | before_model guardrails, LlmAsAJudge, ModelArmor |
| External Docs | Links to official ADK docs and Google sample agents |

## License

MIT
