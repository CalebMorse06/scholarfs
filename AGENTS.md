# AGENTS.md

This file guides contributors and coding agents working on the ScholarFS repository. The generated student-workspace rules live in `src/scholarfs/templates/agents.md.tpl` and are intentionally stricter about student privacy.

## Product contract

ScholarFS is a local-first workspace standard. The plain files must remain useful without the CLI. Do not introduce a hosted dependency, opaque state store, AI-provider requirement, telemetry, or network call into core.

## Read first

1. `README.md` for the user promise.
2. `ARCHITECTURE.md` for boundaries and trade-offs.
3. `docs/WORKSPACE_SPEC.md`, `docs/DEADLINES.md`, and `docs/CONNECTORS.md` for public contracts.
4. `src/scholarfs/` and `tests/` for behavior.

## Invariants

- Python 3.11+; keep runtime dependencies at zero except the documented Windows-only timezone-data package.
- Core makes no network requests and handles no credentials.
- Structured writes are atomic.
- Init, file capture, and calendar export do not overwrite silently.
- Connector preview is non-mutating; apply creates a backup; missing upstream records are never deleted.
- Context generation is deterministic, allowlisted, symlink-safe, and private-by-default.
- Timed deadlines require an offset; date-only precision is preserved.
- Published schemas and the realistic example must match the code.
- Do not add provider-specific memory as a canonical source.

## Changes

Update tests, schemas, examples, CLI reference, and changelog together when public behavior changes. Do not silently migrate user workspaces. Propose a migration command and document the rollback path.

Run before handing off:

```bash
python -m unittest discover -s tests -v
python -m scholarfs validate examples/fall-2026
python -m build
```

Use `PYTHONPATH=src` for source-tree runs if the package is not installed.

## Student safety

Never use real student records, course materials, credentials, or private chat exports as fixtures. Lakeview University and all example people are fictional. Tests may create sensitive-looking sentinel text only inside temporary directories.
