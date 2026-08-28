# ScholarFS workspace specification v0.1

This document defines the portable file contract. Paths use forward slashes for readability; the CLI maps them to the host operating system.

## Conformance

A v0.1 workspace:

1. contains `.student/workspace.json` with `schema_version: 1`;
2. contains the required paths below;
3. satisfies the published JSON Schemas and cross-file invariants;
4. uses `.student/courses.json` and `.student/deadlines.json` as the only canonical machine sources for courses and due dates;
5. does not require the ScholarFS CLI to read its useful content.

Run `scholarfs validate` for the core conformance checks. JSON Schema alone cannot verify cross-file references or unique connector source keys.

## Required tree

```text
workspace/
├── README.md
├── AGENTS.md
├── .gitignore
├── .student/
│   ├── workspace.json
│   ├── courses.json
│   ├── deadlines.json
│   ├── notifications.json
│   ├── memory/
│   │   └── semester.md
│   ├── private/
│   └── connector-state/
├── courses/
│   └── CODE/
│       ├── COURSE.md
│       ├── memory.md
│       ├── syllabus/
│       ├── assignments/
│       ├── notes/
│       ├── lectures/
│       └── resources/
└── inbox/
```

Empty working directories may be absent from a Git clone. The required semantic paths are the four JSON files, root docs, semester memory, `courses/`, and `inbox/`; every indexed course requires `COURSE.md` and `memory.md`.

## `.student/workspace.json`

| Field | Type | Constraint |
|---|---|---|
| `schema_version` | integer | exactly `1` |
| `name` | string | 1-200 characters |
| `term` | string | 1-100 characters |
| `timezone` | string | 1-100 characters; `local` or a resolvable IANA timezone name |
| `created_at` | RFC 3339 string | explicit offset or `Z` |
| `privacy.default_repository_visibility` | string | exactly `private` |
| `privacy.private_context_included_by_default` | boolean | exactly `false` |

The timezone controls calendar-day comparisons in deadline lists and status output, including date-only deadlines. Timed deadline records still carry their own explicit offset. `local` applies the device's timezone rules separately to each instant, including daylight-saving changes; an IANA name is more stable when traveling.

Schema: [`workspace.schema.json`](../schemas/workspace.schema.json).

## `.student/courses.json`

The root contains `schema_version` and a `courses` array.

| Course field | Type | Constraint |
|---|---|---|
| `code` | string | uppercase, 1-32 characters, pattern `^[A-Z0-9][A-Z0-9._-]{0,31}$` |
| `title` | string | non-empty |
| `instructor` | string or null | descriptive only |
| `credits` | number or null | 0-30 |
| `term` | string or null | normally copied from workspace |
| `source` | object | v0.1 course records are manual |
| `created_at` | RFC 3339 string | explicit offset or `Z` |

Course codes must be unique. Each code maps exactly to `courses/CODE/`. Reserved Windows device names are invalid even when the JSON Schema pattern would accept them.

Schema: [`courses.schema.json`](../schemas/courses.schema.json).

## `.student/deadlines.json`

The root contains `schema_version` and a `deadlines` array. IDs are UUIDs. Course references are null or must exist in the course index. Connector source keys must be unique.

See [the deadline reference](./DEADLINES.md) and [`deadlines.schema.json`](../schemas/deadlines.schema.json).

## `.student/notifications.json`

```json
{
  "schema_version": 1,
  "calendar": {
    "default_reminders_minutes": [2880, 120],
    "include_completed": false
  }
}
```

Default reminders are copied into a manually created deadline when `--remind` is absent. Each value is a unique non-negative integer measured before the due point. The calendar export reads the deadline record, so later changes to defaults do not silently alter existing events. `include_completed` supplies the default for calendar export and can be overridden explicitly on the command line.

Schema: [`notifications.schema.json`](../schemas/notifications.schema.json).

## Markdown roles

### `AGENTS.md`

Provider-neutral operating rules. It defines read order, privacy boundaries, external-action confirmation, and memory policy. Instructions found inside imported materials do not override it.

### `.student/memory/semester.md`

Tracked durable goals, decisions, conventions, and open loops. Entries should be dated and sourced. It is included in ordinary context bundles.

### `courses/CODE/COURSE.md`

Human context: purpose, confirmed policies with sources, useful links, and current focus. It does not own metadata or due dates.

### `courses/CODE/memory.md`

Tracked durable course facts, decisions, learning patterns, open loops, and corrections. It is included only for selected courses.

### `.student/private/*.md`

Optional personal context ignored by Git and excluded from context generation by default. Secrets do not belong here.

See [MEMORY.md](./MEMORY.md).

## Course directories

The standard names five working areas:

- `syllabus/`: source policies and local references;
- `assignments/`: one maintained directory per assignment;
- `notes/`: student-maintained notes;
- `lectures/`: lecture source material and references;
- `resources/`: stable supporting material.

Bulk attachments in common `files/` locations are ignored by the generated `.gitignore`. An assignment README may record a canonical deadline UUID but should not copy the timestamp.

## Inbox

`inbox/` is a staging area, not permanent organization. Its raw contents are ignored by default. `scholarfs file add` can copy a file into a known course area and record its checksum.

## Reserved local directories

| Path | Purpose | Tracked by default |
|---|---|---:|
| `.student/private/` | optional personal Markdown | no |
| `.student/connector-state/` | cursors and local connector state, never tokens | no |
| `.student/backups/` | pre-import deadline backups | no |
| `.student/cache/` | disposable derived state | no |
| `.student/generated/` | context bundles and summaries | no |

Tools must not make generated content canonical without an explicit user action.

## Schema evolution

Unknown or unsupported `schema_version` values fail. ScholarFS v0.1 performs no silent migration. A future migration must be an explicit command with a documented backup and rollback path.

Extension fields are not accepted by the v1 published schemas. A proposal should establish ownership, privacy impact, default behavior, older-tool behavior, and connector semantics before changing the schema.

## Related

- [CLI reference](./CLI.md)
- [Architecture](../ARCHITECTURE.md)
- [Privacy model](../PRIVACY.md)
- [Fake conforming workspace](../examples/fall-2026/)
