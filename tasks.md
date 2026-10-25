# ADK 2.13 update

Goal: verify the skill against ADK Python 2.13.0 and refresh the supported language references. Official tagged sources and package metadata checked on 2026-10-25. The user has authorized merging PR #4 into `main`, publishing `v2.2.0`, and deleting the local and remote feature branches after merge.

1. [x] P0: fix runtime requirements, artifact awaits, authentication, callbacks and unsafe examples. Gate: 3 executable documentation tests pass on 2.13.0; the same tests fail against the original examples.
2. [x] P0: update workflow resumption, cancellation, confirmation and task delegation. Gate: 9 offline tests cover routing, join, dynamic dispatch, approval/rejection, failed-node resume, abort and the phase-1 examples.
3. [x] P1: update tools, skills, A2A and composition guidance. Gate: 13 offline tests pass, including skill load/unload, A2A app startup/task proxy, advisor budgets and failover preserving a mutated request.
4. [x] P1: update runtime, memory, evaluation and observability. Gate: 20 offline tests pass, including SQLite persistence/user isolation, runtime constructors, callbacks and all 12 evaluation JSON examples validated against real schemas. Deployment CLI flags checked with --help.
5. [x] P1: refresh Java, Go, Kotlin and TypeScript references. Gate: Go example builds with Go 1.26.6/ADK 2.6; 6 TypeScript fences type-check with TypeScript 7.0.2/ADK 2.3; 5 Java examples compile with JDK 17.0.21/ADK 1.13; 3 Kotlin source examples compile with Kotlin 2.3.21/ADK 1.4. Kotlin 2.1.20 fails transitive 2.3 metadata checks; the reference documents the fix. KSP generation and Android are not tested.
6. [x] P1: synchronize README and skill version 2.2.0, add offline tests to CI and inspect the diff. Gates: 23 offline tests pass; all Python fences parse; 29 tagged source links resolve; repository structural/workflow checks pass; SkillEvaluator 6/6, A 91.2; SkillSpector SAFE with 0 open findings and 12 individually reviewed documentation suppressions. Temporary resources cleaned before the phase commit.

Progress: all six implementation phases complete. Independent forward testing also accepted/rejected a report across separate Python processes using SQLite: approval incremented 7 to 8; rejection retained 7. This exposed missing `[db]` setup and an unconditional credential requirement; both are corrected.

Publication follow-up: project instructions consolidated into tracked `AGENTS.md` with a `CLAUDE.md` import, README activation and release guidance aligned, and dated 2.2.0 notes added to `CHANGELOG.md`. Documentation checks pass: seven local links, version metadata, import routing and 89 Python fences. The branch is published in [PR #4](https://github.com/miticojo/adk-skill/pull/4); its examples and validation CI jobs pass.

Release closeout: merge PR #4 preserving phase commits, tag the merged `main` commit as `v2.2.0`, wait for both tag validation jobs and the publication job, then align the GitHub Release body with `CHANGELOG.md`. Verify the release and report attachments before deleting the merged local/remote branches. The canonical release is [v2.2.0](https://github.com/miticojo/adk-skill/releases/tag/v2.2.0).

Validation limits: cloud deployment, real model conversations/evaluations, live audio, Android and KSP generation need separate authorized integration tests in the target environment. Native compilation was local; CI runs Python checks. The bundled skill-creator quick validator rejects the supported `compatibility` field; the repository's spec-aware schema and structural gates validate it, so the field is retained.

Cleanup: task-created Python/tool environments, downloaded language runtimes/caches, reports, databases and scratch files were removed. Existing ignored fixtures/credentials and shared package-manager caches are retained; no task server/process remains. Phase commits are preserved in merge history; only merged feature branches are eligible for removal.
