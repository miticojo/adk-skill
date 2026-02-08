# Agent Design Patterns

Best practices for designing, building, and operating ADK agents. Patterns are organized by concern, with ADK-specific implementation guidance.

## Pattern Selection Guide

| Situation | Pattern | ADK Implementation |
|-----------|---------|-------------------|
| Task has multiple dependent steps | Sequential pipeline | `SequentialAgent` with ordered sub-agents |
| Sub-tasks are independent | Fan-out / Fan-in | `ParallelAgent` → merger `Agent` |
| Output quality must be high | Reflection loop | `LoopAgent` with producer + critic |
| Diverse inputs need different handling | Dynamic routing | Parent `Agent` with `sub_agents` (Auto-Flow) |
| Procedure is unknown at design time | Dynamic planning | Planning agent writes plan to state; executor agents follow it |
| Tool calls may fail | Layered fallback | `SequentialAgent`: primary → fallback → response |
| Safety/compliance is required | Guardrails | `before_model_callback` + `before_tool_callback` |
| Budget constraints exist | Resource tiering | Different `model` per agent (Pro vs Flash) |
| Agent must recall across sessions | Long-term memory | `MemoryService` (search + store) |
| Humans must approve critical actions | Human-in-the-loop | Escalation tools + callback gates |
| Complex reasoning required | Structured reasoning | CoT/ReAct directives in agent instructions |

### Fixed Workflow vs Dynamic Planning

| Condition | Approach |
|-----------|----------|
| The "how" is already known | Fixed workflow (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) |
| The "how" must be discovered | Planning agent (LLM generates plan at runtime) |
| High predictability required | Fixed workflow -- limits autonomy, reduces risk |
| High adaptability required | Planning agent -- can re-plan when obstacles arise |

---

## Core Execution Patterns

### Sequential Pipeline (Prompt Chaining)

Break a complex task into a sequence of focused sub-tasks. Each step has ONE responsibility.

**Rules:**
- Use structured output (JSON/Pydantic via `output_key`) between steps -- never free text
- Insert validation between steps via callbacks (`after_agent_callback`)
- Combine with `ParallelAgent` for independent sub-tasks within the pipeline
- Each agent reads upstream results from `state["key"]` and writes via `output_key`

**Why single prompts fail:**

| Failure Mode | Cause |
|--------------|-------|
| Instruction neglect | Model overlooks parts of complex prompts |
| Contextual drift | Model loses track of initial context mid-generation |
| Error propagation | Early errors compound through later reasoning |
| Hallucination risk | Higher cognitive load increases fabrication |

**Architecture:**
```
root (SequentialAgent)
  +-- extract_agent (Agent, output_key="extracted")
  +-- validate_agent (Agent, reads state["extracted"])
  +-- synthesize_agent (Agent, output_key="result")
```

### Dynamic Routing

Direct flow to specialized sub-agents based on input classification.

**Rules:**
- The coordinator's `instruction` must explicitly list routing rules and sub-agent names
- Each sub-agent's `description` is the primary signal for Auto-Flow delegation -- write it carefully
- Keep the coordinator focused: classify → delegate → return. It should NOT answer directly
- Always include a fallback/unclear handler for ambiguous inputs
- Use tool-based routing for deterministic dispatch; LLM-based routing for nuanced inputs

**Routing mechanisms:**

| Method | Best For |
|--------|----------|
| LLM-based (Auto-Flow) | Nuanced natural-language inputs |
| Rule-based (callbacks) | Deterministic, fast classification |
| Embedding similarity | Semantic routing by meaning |

**Architecture:**
```
coordinator (Agent)
  instruction="Analyze and delegate. Do NOT answer directly."
  sub_agents=[
    billing_agent (description="Handles billing questions")
    tech_agent (description="Handles technical issues")
    general_agent (description="Handles unclear or general queries")
  ]
```

### Parallelization (Fan-out / Fan-in)

Run independent sub-tasks concurrently, then synthesize results.

**Rules:**
- Each parallel sub-agent MUST write to its own unique `output_key` -- shared keys cause conflicts
- Place a synthesis agent AFTER the parallel stage in a `SequentialAgent`
- The merger instruction MUST ground output exclusively on state values -- no external knowledge
- Only parallelize truly independent tasks -- data dependencies require sequential execution

**Architecture:**
```
root (SequentialAgent)
  +-- parallel_stage (ParallelAgent)
  |     +-- agent_a (output_key="result_a")
  |     +-- agent_b (output_key="result_b")
  +-- merger (Agent, reads state["result_a"] and state["result_b"])
```

**Anti-patterns:** False parallelism (dependent tasks marked parallel), no synthesis step, parallel agents writing to same state key.

### Reflection (Producer-Critic Loop)

An agent generates output, a separate agent evaluates it, then the producer refines based on feedback.

**Rules:**
- Always use a SEPARATE critic agent -- same-agent self-review suffers from cognitive bias
- Give the critic specific evaluation criteria (accuracy, completeness, style), not "review this"
- Set `max_iterations` (typically 2-5) as safety bound on the `LoopAgent`
- Use `output_key` to pass data between producer and critic via state
- The critic should output structured feedback OR a sentinel value signaling completion

**Architecture:**
```
# Single-pass review
review (SequentialAgent)
  +-- producer (Agent, output_key="draft")
  +-- critic (Agent, reads state["draft"], output_key="critique")

# Iterative refinement
loop (LoopAgent, max_iterations=3)
  +-- producer (Agent, output_key="draft")
  +-- critic (Agent, signals escalate=True when quality met)
```

**When to skip reflection:** Time-sensitive tasks, simple queries, cost-constrained environments. Reflection adds latency and cost per cycle.

### Planning

Enable agents to decompose goals into executable steps at runtime.

**Rules:**
- Store the plan in `session.state["plan"]` so all agents can reference it
- Present the plan to the user before execution for high-stakes tasks
- Allow plans to be modified mid-execution based on new information
- Set clear completion criteria for each plan step
- Use a dedicated synthesis agent that reads all step outputs from state

**Deep Research pattern (iterative plan-search-evaluate):**
1. Decompose query into multi-point research plan
2. Present plan for user review
3. Execute iteratively: formulate queries based on gathered information
4. Evaluate: identify gaps, corroborate data
5. Re-search to fill gaps
6. Synthesize with citations

---

## Robustness Patterns

### Error Handling & Recovery

Three-phase pipeline: **Detect → Handle → Recover**.

**Rules:**

| Phase | Do | Don't |
|-------|-----|-------|
| Detect | Validate tool outputs, check response codes, enforce timeouts | Assume tool calls always succeed |
| Handle | Retry with adjusted params, fall back to alternatives, degrade gracefully | Retry exact same failing call in tight loop |
| Recover | Roll back state to last checkpoint, diagnose root cause | Leave corrupted state in place |

**ADK fallback pattern:**
```python
robust_agent = SequentialAgent(
    name="robust_agent",
    sub_agents=[
        primary_handler,    # Attempts main approach
        fallback_handler,   # Checks state["primary_failed"], tries alternative
        response_agent,     # Synthesizes result or apologizes
    ]
)
```

Communicate failure via state flags: `state["primary_failed"] = True`. Downstream agents read flags to decide behavior.

### Human-in-the-Loop (HITL)

AI augments human capabilities. Define explicit escalation rules -- do not let agents decide ad hoc.

**Escalation triggers:**
- Agent confidence below threshold
- Tool failure after retry exhaustion
- Financial transactions above a limit
- Content flagged as ambiguous
- Task requires ethical/legal judgment

**Rules:**
- Provide an `escalate_to_human` tool the agent can call
- Include context/history when escalating (what was tried, what failed)
- Use `before_model_callback` to inject personalization from state
- "Human-on-the-loop" variant: humans set policy, agent executes within boundaries

### Guardrails & Safety

Layered defense -- never rely on a single mechanism.

**Implementation stages:**

| Stage | ADK Mechanism | Purpose |
|-------|--------------|---------|
| Input validation | `before_model_callback` | Block prompt injection, jailbreaks |
| Output filtering | `after_model_callback` | Catch toxicity, policy violations |
| Tool parameter check | `before_tool_callback` | Prevent unauthorized actions |
| Tool output check | `after_tool_callback` | Validate tool results |
| Behavioral constraints | Agent `instruction` | Define role boundaries |

**Rules:**
- Use a fast, cheap model (Gemini Flash) for guardrail evaluation, temperature=0
- Return guardrail results as structured JSON (compliance_status, triggered_policies)
- Set `allow_delegation=False` on guardrail agents
- Default to "compliant" on ambiguity -- only block on demonstrable violations
- Log all guardrail decisions for audit

**Safety policy categories to cover:**
1. Instruction subversion / jailbreaking
2. Prohibited content (hate speech, hazardous activities)
3. Off-domain discussions
4. Proprietary / competitive information leakage

---

## Optimization Patterns

### Resource-Aware Model Selection

Route tasks to models matching their complexity.

| Task Type | Model Tier | Example |
|-----------|-----------|---------|
| Simple factual queries | Fast/cheap (Gemini Flash) | "What is the capital of France?" |
| Complex reasoning | Powerful/expensive (Gemini Pro) | Multi-step analysis, code review |
| Current events | Medium + search tool | "What happened today in markets?" |

**Architecture:** Router agent (cheap model) classifies query → delegates to tiered worker agents → Critique agent evaluates response quality.

**Fallback chain:** Define prioritized model list. If model 1 fails (rate-limit, unavailable), auto-route to model 2.

### Context Engineering

Design the complete informational environment for the model before token generation.

**Context layers:**
1. **System prompt** (`instruction`): Foundational rules, persona, boundaries
2. **Retrieved data**: Tool outputs, RAG results, API responses
3. **Implicit data**: User identity, interaction history, environment state (injected via `before_model_callback`)

**Rules:**
- Use XML tags or delimiters to separate instructions from data in prompts
- Summarize older conversation segments to manage context window
- Use `temp:` prefix state keys for data needed only in current turn
- Inject dynamic context via `before_model_callback`, not by bloating the static instruction

### Reasoning Directives

Embed structured reasoning in agent instructions for complex tasks.

| Technique | How to Implement in ADK |
|-----------|------------------------|
| Chain-of-Thought | Add to instruction: "Before answering, reason through each step." |
| Self-Correction | `LoopAgent` with critic sub-agent that evaluates and triggers re-generation |
| ReAct | Default ADK agent behavior -- agents reason, call tools, observe, continue |
| Tree-of-Thought | `ParallelAgent` to explore paths + evaluator agent to select best |
| Self-Consistency | `ParallelAgent` running same agent N times + voting/aggregation agent |
| Step-Back | `SequentialAgent`: principle-extraction agent → task-execution agent |

**Rule of thumb:** Use reasoning techniques when a problem requires decomposition, multi-step logic, tool interaction, or strategic planning. Skip for simple factual queries.

---

## Agent Instruction Design

### Prompting Best Practices

| Principle | Rule |
|-----------|------|
| Clarity | Define task, output format, limitations unambiguously |
| Action verbs | Use: Analyze, Classify, Compare, Extract, Generate, List, Summarize |
| Positive framing | Specify what TO DO, not what to avoid |
| Role definition | "You are a senior data engineer..." sets knowledge scope and tone |
| Structured output | Request JSON/Pydantic for machine-readable results between pipeline stages |
| Delimiters | Use XML tags or `---` to separate instructions from injected context |

### Few-Shot Examples in Instructions

| Technique | When to Use |
|-----------|------------|
| Zero-shot | Tasks the model knows well -- try first |
| One-shot | Specific output format or uncommon style |
| Few-shot (3-5 examples) | Strict format adherence, nuanced classification |

**Few-shot rules:** Examples must be error-free. Mix class order for classification. Provide diverse examples.

### Technique Selection Matrix

| Scenario | Technique | ADK Implementation |
|----------|-----------|-------------------|
| Simple task | Zero-shot | `Agent` with clear `instruction` |
| Specific format needed | Few-shot | Examples embedded in `instruction` |
| Multi-step reasoning | Chain of Thought | CoT directive in `instruction` |
| High-reliability reasoning | Self-Consistency | `ParallelAgent` + aggregation agent |
| Dynamic external knowledge | RAG | Tool querying knowledge base |
| Tool-using agent | ReAct | Default `Agent` with `tools` list |
| Complex multi-step task | Factored Cognition | `SequentialAgent` with sub-agents |

---

## Evaluation & Monitoring

### What to Measure

| Metric | How |
|--------|-----|
| Response accuracy | Eval sets + LLM-as-judge (semantic similarity, not exact match) |
| Trajectory quality | Compare tool selection and step ordering against ground truth |
| Latency | Time per request, per tool call, end-to-end |
| Token usage | Input/output tokens per session for cost tracking |
| Multi-agent cooperation | Data passing correctness, routing accuracy, plan adherence |

### Evaluation Rules

- Evaluate BOTH the final output AND the trajectory (sequence of decisions)
- Use semantic similarity (embeddings) rather than exact string matching
- Combine human evaluation, LLM-as-judge, and automated metrics
- For multi-agent systems, assess individual agent AND team-level performance
- Build eval sets: JSON files with user queries, expected tool use, and expected output

### Trajectory Evaluation Methods

| Method | When to Use |
|--------|------------|
| Exact match | Safety-critical, high-stakes |
| In-order match | Standard quality checks |
| Any-order match | Flexible task completion |
| Precision/Recall | Minimize wasted actions / ensure completeness |

---

## Universal Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| God Agent | Single agent with 10+ tools spanning domains | Split into focused specialists |
| Self-review bias | Same agent generates and evaluates output | Separate producer and critic agents |
| Monolithic prompt | All instructions crammed into one prompt | Decompose into `SequentialAgent` pipeline |
| Unstructured handoff | Free-text between pipeline stages | Structured JSON via `output_key` |
| No validation gates | Errors cascade through pipeline | `after_agent_callback` checks between steps |
| Unbounded loops | `LoopAgent` without termination | Always set `max_iterations` |
| Missing fallback | Ambiguous inputs silently misrouted | Include unclear/fallback handler |
| Context overload | Full history stuffed into every prompt | Summarize older segments, use state |
| One-model-fits-all | Expensive model for every query | Route by complexity (Pro vs Flash) |
| Silent tool failure | Agent proceeds as if tool succeeded | Return structured error dicts, check in callbacks |
| Direct state mutation | Modifying `session.state` directly | Use `output_key` or `EventActions.state_delta` |
| Stateless reflection | Each iteration starts fresh | Preserve history via state across loop cycles |

---

## Multi-Agent Collaboration Models

| Model | Structure | ADK Mapping |
|-------|-----------|-------------|
| Supervisor | Coordinator delegates to workers | Parent `Agent` with `sub_agents` |
| Supervisor (as tools) | Coordinator calls agents like functions | `AgentTool` wrapping sub-agents |
| Hierarchical | Multi-level tree of supervisors | Nested agent trees |
| Sequential | Pipeline A → B → C | `SequentialAgent` |
| Parallel | Concurrent fan-out | `ParallelAgent` |
| Network | Peers communicate directly | Custom with `sub_agents` + transfer |

**Rule of thumb:** If an agent needs more than 5-7 tools or handles unrelated domains, split into multiple agents.

### State Management Across Agents

| Prefix | Scope | Persistence |
|--------|-------|-------------|
| (none) | Current session only | Session-scoped |
| `user:` | Tied to user ID | Cross-session for that user |
| `app:` | Shared across all users | Application-wide |
| `temp:` | Current turn only | Not persisted |

**Rules:**
- Use `output_key` on agents to auto-save responses to state
- Use `tool_context.state` for complex updates within tools
- State changes only persist when appended as events via `session_service.append_event()`
- Use serializable types only (strings, numbers, bools, lists, dicts)
- Never modify `session.state` directly after retrieving a session -- bypasses event processing

### Memory Architecture

| Type | Scope | ADK Service |
|------|-------|-------------|
| Short-term (chat history) | Current session | `session.events` via `SessionService` |
| Short-term (working data) | Current session | `session.state` key-value dict |
| Long-term (persistent) | Cross-session | `MemoryService` (semantic search) |

- Use `InMemorySessionService` / `InMemoryMemoryService` for dev/test
- Use `DatabaseSessionService` or `VertexAiSessionService` for production
- Use `VertexAiRagMemoryService` for persistent, scalable semantic memory
- Manage context window actively: summarize older segments, prune irrelevant history
