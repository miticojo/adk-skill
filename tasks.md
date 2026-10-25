# ADK 2.13 update

Goal: verify the skill against ADK Python 2.13.0 and refresh the supported language references. Official tagged sources and package metadata checked on 2026-10-25. Work on `codex/adk-2.13-update`; local commits only.

1. [x] P0: fix runtime requirements, artifact awaits, authentication, callbacks and unsafe examples. Gate: 3 executable documentation tests pass on 2.13.0; the same tests fail against the original examples.
2. [ ] P0: update workflow resumption, cancellation, confirmation and task delegation. Gate: deterministic runner tests.
3. [ ] P1: update tools, skills, A2A and composition guidance. Gate: API construction and behavior checks against 2.13.0.
4. [ ] P1: update runtime, memory, evaluation and observability. Gate: tagged API checks and focused tests.
5. [ ] P1: refresh Java, Go, Kotlin and TypeScript references. Gate: minimal compilation where available; record source-only checks explicitly.
6. [ ] P1: synchronize README, run structural/quality/security checks, inspect diff and clean task resources. Gate: all available checks pass; limitations recorded.

Progress: phase 1 verified in an isolated Python 3.13 environment. Stages 4 and 5 run independently; workflow behavior tests are next. No files from existing ignored test fixtures will be read for credentials or removed.
