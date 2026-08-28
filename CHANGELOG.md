# Changelog

All notable user-visible changes are recorded here. ScholarFS uses semantic versioning after `0.1.0`; before `1.0`, schema changes may be breaking but are never applied silently.

## 0.1.0 - 2026-08-28

### Added

- Local-first workspace scaffold with provider-neutral `AGENTS.md`.
- Canonical course, deadline, notification, and workspace JSON models.
- Course and file-capture commands.
- Deadline add, list, complete, reopen, cancel, and connector-import commands.
- Date-only and offset-aware deadline precision.
- Deterministic, private-by-default context bundles.
- ICS calendar export with reminder alarms.
- Preview-first, idempotent connector imports with backups and no implicit deletes.
- Stale connector-observation rejection to prevent replayed snapshots from rolling deadlines backward.
- Structure, invariant, symlink, and privacy validation.
- Calendar exports that omit free-form notes unless explicitly requested.
- Published JSON Schemas and an offline reference connector.
- A realistic, completely fictional Fall 2026 semester.
- Full contributor, privacy, security, architecture, usage, and launch documentation.
