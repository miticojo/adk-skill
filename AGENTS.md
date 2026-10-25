# Working on ADK Skill

This repository distributes a Markdown skill for Google's Agent Development Kit. `adk-skill/` is the installable package; project documentation and `validation/` are development resources. Read `README.md` for setup, supported SDK versions and verification commands, `CHANGELOG.md` for release notes, and `tasks.md` for the active update status.

## Editing

- Keep the complete `adk-skill/SKILL.md` below 500 lines. Its frontmatter name must match the directory; description and compatibility limits are 1024 and 500 characters.
- Keep essential decisions in the entrypoint and detailed guidance in its nine `references/*.md` files. Link references directly from the entrypoint; do not introduce chained local reference links. These are repository gates.
- Keep Python examples in the entrypoint; native SDK examples belong in `references/multi-language.md`. Identify application fragments and provide imports for complete examples.
- Check APIs against the official tag/package version being documented. Record the version and verification date; distinguish stable, preview and experimental APIs. Do not infer cross-language parity from version numbers.
- Update existing documentation in place. Maintain human-facing instructions in `README.md`, release notes in `CHANGELOG.md`, and progress in `tasks.md`; avoid duplicate reports inside the installable skill.
- Keep the historical effectiveness benchmark labeled as historical until it is rerun.

## Validation

- Follow the offline test commands in `README.md`. Tests execute Markdown examples with the target ADK; `python -m unittest discover -s validation -v` must not call models, cloud services or use real credentials.
- Run the schema/quality and static security checks pinned in `.github/workflows/release.yml`, plus its structural checks and `git diff --check`.
- Review scanner findings individually before changing `.skillspector-baseline.yaml`; preserve explicit reasons and avoid wildcard suppressions.
- Compile/type-check native examples when changed. Report toolchain versions, failed attempts and checks that need external services. Python CI does not validate Android, KSP generation, Live audio or production deployment.
- The artifact is Markdown; there is no application build. `validation/` contains the maintained regression suite. Existing ignored `tests/`, `doc/` and `reports/` may contain local fixtures or history; do not treat them as release inputs or inspect credential files.

## Git and Releases

Use a dedicated branch and small phase commits. Push, merge and publish tags/releases only when the user has authorized that action. Creating a pull request does not authorize a merge or release.

The release workflow runs Python examples, structural checks, SkillEvaluator and SkillSpector. A `v*` tag publishes a GitHub Release only after the examples and validation jobs succeed. Keep unreleased notes marked unreleased until publication.

Remove task-created environments, downloaded runtimes, reports, databases and scratch files after verification. Preserve shared caches and unmerged work, and state what remains.
