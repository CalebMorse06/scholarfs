# Architecture

ScholarFS turns a fragmented semester into an inspectable context layer. The filesystem is the durable interface; the CLI is a conservative editor around it.

## The problem

An LMS is good at publishing course state, but it is not a student-owned working environment. Notes, assignments, calendar events, chat history, and decisions land in separate systems. An assistant then lacks reliable context, while a proprietary memory feature is hard to inspect or move.

The failure mode is not merely inconvenience. Duplicate due dates drift, guesses become “memory,” connector credentials leak into workspaces, and a tool change can strand the useful context.

## The approach

```text
                      optional external tools
                   ┌───────────────────────────┐
                   │ LMS connector   AI agent  │
                   └───────┬────────────┬──────┘
                           │ JSON file  │ allowlisted context
                           v            v
┌────────────────────────────────────────────────────────────┐
│                    ScholarFS workspace                     │
│                                                            │
│  Markdown: human context     JSON: canonical machine facts │
│  COURSE.md, memory.md         courses, deadlines, settings │
│                                                            │
│             ^ conservative reads and atomic writes         │
│             │                                              │
│        ScholarFS CLI: scaffold, validate, export            │
└────────────────────────────────────────────────────────────┘
```

The boundary has four layers:

1. **Workspace standard.** Stable paths and plain-file conventions remain useful without Python.
2. **Deterministic core.** A small Python CLI scaffolds, validates, updates, and exports local files.
3. **Explicit context.** `scholarfs context` reads a small allowlist rather than sweeping the directory.
4. **External connector interchange.** Connectors are separate processes that produce normalized JSON; core never imports their code or credentials.

## Canonical data and human context

ScholarFS avoids two writable copies of the same fact.

| Fact | Canonical location | Human companion |
|---|---|---|
| Workspace settings | `.student/workspace.json` | root `README.md` |
| Course metadata | `.student/courses.json` | `courses/CODE/COURSE.md` |
| Due dates and status | `.student/deadlines.json` | assignment README references a deadline ID |
| Reminder defaults | `.student/notifications.json` | deadline and calendar documentation |
| Semester memory | `.student/memory/semester.md` | same file; Markdown is canonical |
| Course memory | `courses/CODE/memory.md` | same file; Markdown is canonical |

Course Markdown may explain a policy or assignment, but it should reference a deadline ID instead of copying the due timestamp.

## Mutation model

Core mutations follow three rules:

- structured JSON uses a same-directory temporary file and atomic replace;
- initialization and file capture never overwrite by default;
- connector application creates a timestamped backup before the atomic replace.

Connector imports upsert by `(connector, external_id)`. A missing upstream item causes no deletion. Cancellation must be explicit. Locally completed items remain completed when a connector re-observes them as pending.

## Context model

The default context bundle includes only:

- root agent instructions;
- workspace metadata and the course index;
- relevant open deadlines;
- semester memory;
- selected `COURSE.md` and course memory files.

It excludes `.student/private/`, attachments, inbox contents, bulk notes, and unrelated courses. Symlinks are refused. Private Markdown requires `--include-private`.

This is an allowlist, not a claim that Markdown is safe. Imported text may still contain prompt injection, so every generated bundle labels imported material as reference, not instructions.

## Why Python and JSON

Python 3.11 provides the CLI, path handling, dates, UUIDs, atomic file operations, and package resources. On Windows, ScholarFS installs Python's first-party `tzdata` package because the operating system does not expose the IANA timezone database through `zoneinfo`; other platforms need no third-party runtime package. JSON is less pleasant than YAML for comments, but it has unambiguous parsing in the standard library and published schemas. Markdown remains the comment-friendly human layer.

Trade-off: users cannot annotate JSON freely. In return, the core has a small supply-chain footprint and predictable cross-platform behavior.

## Why no database

SQLite would improve queries and transactional updates, but it would make the database the real product. ScholarFS chooses grep-able, diff-able, portable files. This limits scale, which is acceptable for one student's semester.

## Why no in-process plugins

Loading connector code into core would mix credentials, network access, vendor SDKs, and failure modes into the trusted path. File interchange costs one preview/apply step, but makes the data crossing the boundary inspectable and permits connectors in any language.

## Why no built-in AI

Provider SDKs would make model choice and data transmission part of the architecture. ScholarFS instead produces stable context that works with direct filesystem agents or a Markdown handoff. The model remains replaceable.

## Failure boundaries

- Corrupt or unknown schema versions fail validation; there is no silent migration.
- Timed deadlines without an explicit UTC offset are rejected.
- Date-only deadlines remain date-only.
- Course codes that can traverse paths or collide with Windows device names are rejected.
- Imports reject unknown courses, duplicate external IDs, stale observations, unsupported fields, and raw payload-shaped envelopes.
- Calendar export refuses to replace its target unless `--force` names that exact file.

## Deferred architecture

Live OAuth connectors, syllabus extraction, a GUI, cloud sync, vector search, multi-user collaboration, and background scheduling are out of v0.1. Each would widen the trusted boundary before the workspace standard has earned stability.
