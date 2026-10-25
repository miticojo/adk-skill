# Release Notes

## 2.2.0 — Unreleased

Updates the skill from ADK Python 2.7.1 coverage to **2.13.0**. APIs and package metadata were checked against official versioned sources on **2026-10-25**. This entry describes the proposed release; no tag or GitHub Release has been published.

### Compatibility and migration

- Python examples require **Python 3.11+**. Model credentials are required only for model calls; deterministic function-only workflows can run offline.
- Verified reference SDKs: Python **2.13.0**, Java **1.13.0**, Go **2.6.0**, Kotlin **1.4.0**, TypeScript **2.3.0**. Java and Kotlin graph support is experimental; Kotlin's core is generally available.
- Go 2.6 examples use **Go 1.26.6** and the `/v2` module path. Kotlin examples compile with **Kotlin 2.3.21**; 2.1.20 fails on transitive dependencies with 2.3 metadata.
- Document failed-node reexecution on resume, idempotency requirements, cancellation, node/tool confirmation, authentication resumption and nested task delegation. Add a persistent SQLite session setup with the `[db]` extra.
- Document OpenTelemetry's `otel_semconv_1_44` default, removal of `call_llm`, and the temporary legacy-schema override.

### Added and updated

- Stable `SkillToolset` guidance with experimental, opt-in lifecycle modes, discovery, load/unload APIs and script output artifacts.
- MCP SDK 2.x compatibility and its separate modern-protocol opt-in; native A2A task delegation, authentication and version-specific Agent Cards.
- Experimental model failover, bounded advisor consultation, classifier routing and explicit application error recovery.
- SQLite memory, experimental MongoDB sessions/memory and backend-specific memory mutation support.
- OpenAI integration imports, LiveKit/CascadeLive, deployment identity and informational efficiency metrics.
- Native SDK examples, toolchains and capability boundaries; a maintained offline Python suite and CI gate for documented examples.

### Corrected

- Await artifact save/load/list operations and validate their results.
- Use `AuthenticatedFunctionTool` for authenticated functions, valid callback return types and actual SDK constructors/imports.
- Replace unrestricted `eval` with validated arithmetic inputs.
- Correct state interpolation, response-event extraction, asynchronous waiting, graph validation rules and task completion naming.
- Replace exception-blind sequential fallback guidance with explicit recovery and model failover contracts.
- Narrow activation to ADK work; retain details in references and keep the entrypoint below 500 lines.

### Verification

- **23 offline Python tests passed**, including routing, joins, dynamic dispatch, approval/rejection, persistent-session restart, abort, artifacts, memory isolation, skill lifecycle, A2A startup/cards, callbacks and failover.
- All documented Python fences parse; **12 evaluation JSON examples** validate against ADK schemas; **29 versioned source links** resolve.
- Native checks passed: Go example with Go 1.26.6; six TypeScript examples with TypeScript 7.0.2; five Java examples with JDK 17.0.21; three Kotlin source examples with Kotlin 2.3.21.
- An independent cross-process SQLite check confirmed that approval increments the acceptance counter and rejection leaves it unchanged after restart.
- SkillEvaluator: **6/6 checks passed, A — 91.2/100**. SkillSpector: **SAFE, zero open findings**, with **12 individually reviewed documentation suppressions** and no wildcard rules.

### Test limits

Cloud deployment, real model conversations/evaluations, Live audio, Android and KSP generation were not exercised. Native compilation was local; CI runs Python checks. The historical effectiveness benchmark was not rerun. Offline tests do not establish model availability or production behavior.

The bundled skill-creator quick validator rejects the supported `compatibility` frontmatter field; repository schema and structural gates validate it. The field is retained.

See [README.md](README.md#verification) for repeatable verification commands and [tasks.md](tasks.md) for phase-level evidence. Official upstream baseline: [ADK Python 2.13.0](https://github.com/google/adk-python/releases/tag/v2.13.0).
