# ADK 2.13 update

Goal: verify the skill against ADK Python 2.13.0 and refresh the supported language references. Official tagged sources and package metadata checked on 2026-10-25. Work on `codex/adk-2.13-update`; local commits only.

1. [x] P0: fix runtime requirements, artifact awaits, authentication, callbacks and unsafe examples. Gate: 3 executable documentation tests pass on 2.13.0; the same tests fail against the original examples.
2. [x] P0: update workflow resumption, cancellation, confirmation and task delegation. Gate: 9 offline tests cover routing, join, dynamic dispatch, approval/rejection, failed-node resume, abort and the phase-1 examples.
3. [x] P1: update tools, skills, A2A and composition guidance. Gate: 13 offline tests pass, including skill load/unload, A2A app startup/task proxy, advisor budgets and failover preserving a mutated request.
4. [x] P1: update runtime, memory, evaluation and observability. Gate: 20 offline tests pass, including SQLite persistence/user isolation, runtime constructors, callbacks and all 12 evaluation JSON examples validated against real schemas. Deployment CLI flags checked with --help.
5. [x] P1: refresh Java, Go, Kotlin and TypeScript references. Gate: Go example builds with Go 1.26.6/ADK 2.6; 6 TypeScript fences type-check with TypeScript 7.0.2/ADK 2.3; 5 Java examples compile with JDK 17.0.21/ADK 1.13; 3 Kotlin source examples compile with Kotlin 2.3.21/ADK 1.4. Kotlin 2.1.20 fails transitive 2.3 metadata checks; the reference documents the fix. KSP generation and Android are not tested.
6. [ ] P1: synchronize README, run structural/quality/security checks, inspect diff and clean task resources. Gate: all available checks pass; limitations recorded.

Progress: phases 1–5 complete. Final README/coverage synchronization and CI quality/security gates remain. Language-agent runtimes/caches removed (about 2.3 GB). Existing ignored fixtures and credentials are untouched. Cloud, live-audio, model-backed evaluations, Android and KSP generation remain outside the offline checks.
