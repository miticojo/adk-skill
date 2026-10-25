# ADK 2.13 update

Goal: verify the skill against ADK Python 2.13.0 and refresh the supported language references. Official tagged sources and package metadata checked on 2026-10-25. Work on `codex/adk-2.13-update`; local commits only.

1. [x] P0: fix runtime requirements, artifact awaits, authentication, callbacks and unsafe examples. Gate: 3 executable documentation tests pass on 2.13.0; the same tests fail against the original examples.
2. [x] P0: update workflow resumption, cancellation, confirmation and task delegation. Gate: 9 offline tests cover routing, join, dynamic dispatch, approval/rejection, failed-node resume, abort and the phase-1 examples.
3. [x] P1: update tools, skills, A2A and composition guidance. Gate: 13 offline tests pass, including skill load/unload, A2A app startup/task proxy, advisor budgets and failover preserving a mutated request.
4. [x] P1: update runtime, memory, evaluation and observability. Gate: 20 offline tests pass, including SQLite persistence/user isolation, runtime constructors, callbacks and all 12 evaluation JSON examples validated against real schemas. Deployment CLI flags checked with --help.
5. [ ] P1: refresh Java, Go, Kotlin and TypeScript references. Gate: minimal compilation where available; record source-only checks explicitly.
6. [ ] P1: synchronize README, run structural/quality/security checks, inspect diff and clean task resources. Gate: all available checks pass; limitations recorded.

Progress: phases 1–4 verified in an isolated Python 3.13 environment. Language updates are compiled and ready for integration review. Existing ignored fixtures and credentials are untouched. Cloud, live-audio and model-backed evaluations are not exercised by offline tests.
