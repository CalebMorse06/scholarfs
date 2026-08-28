# ScholarFS

**Your semester, organized for humans and AI.**

ScholarFS is an open-source, local-first workspace standard and CLI for course files, deadlines, notes, and durable AI context. Everything stays in ordinary Markdown and JSON files on your computer, so you can inspect it, edit it, version it, and use it with an assistant that can read local files or accept a Markdown bundle. Or no assistant at all.

> A local-first workspace standard for AI-native students.

[Quick start](#quick-start) · [Explore the fake semester](./examples/fall-2026/) · [Read the workspace specification](./docs/WORKSPACE_SPEC.md) · [How privacy works](./PRIVACY.md)

## Trust, by default

- **No telemetry.** ScholarFS records no analytics.
- **No network access.** The core CLI makes no network requests.
- **No hidden database.** Markdown and JSON are the durable interface.
- **No credentials.** Core does not authenticate to an LMS or AI provider.
- **No silent overwrite.** Initialization refuses non-empty directories unless `--merge` is explicit, and merge never replaces files.
- **No silent connector changes.** Imports are preview-first, create a backup, and never delete missing records.
- **Private context stays out.** `.student/private/` is ignored by Git and excluded from context bundles unless explicitly included.

An external AI assistant or connector may transmit data under its own policy. ScholarFS cannot make another tool local-first; it makes the files and the boundary visible.

## Quick start

Requires Python 3.11 or newer. Clone and install:

```bash
git clone https://github.com/CalebMorse06/scholarfs.git
cd scholarfs
python -m pip install .
scholarfs init my-semester --term "Fall 2026" --timezone America/Chicago
cd my-semester
scholarfs course add CS-101 --title "Introduction to Computer Science"
scholarfs deadline add "Problem set 1" --course CS-101 --on 2026-09-04
scholarfs status
scholarfs validate
```

That creates a usable workspace immediately. There is no account, API key, setup wizard, or service to start.
On Windows, installation also pulls Python's `tzdata` package so named timezones such as `America/Chicago` behave consistently.

To keep ScholarFS isolated, install it with [`pipx`](https://pipx.pypa.io/) or [`uv`](https://docs.astral.sh/uv/) instead:

```bash
pipx install .
# or
uv tool install .
```

## See it with realistic data

The repository includes a completely fictional Lakeview University semester:

```bash
cd examples/fall-2026
scholarfs status --as-of 2026-08-28T12:00:00-05:00
```

```text
Next 14 days
3 open, 0 overdue, 1 need attention
  CS-241       1
  SEMESTER     1
  STAT-210     1
```

Generate an allowlisted context bundle for any chat or coding agent:

```bash
scholarfs context CS-241 --output .student/generated/cs-241-context.md
```

The output contains course context, durable memory, and full open-deadline records, including deadline notes and source URLs. It excludes private memory, attachments, bulk course notes, and unrelated courses by default. Inspect the bundle before sharing it.

## Your LMS publishes the semester. You should own the context.

Course information usually ends up scattered across an LMS, syllabus PDFs, calendar events, folders, notes, and temporary chat history. ScholarFS gives it a consistent, student-owned home.

The CLI helps create and validate the workspace, but **the files are the product**. If the CLI disappeared tomorrow, the semester would still be readable.

ScholarFS is:

- a plain-file workspace convention;
- a small Python CLI for safe scaffolding and validation;
- a structured deadline and reminder model;
- explicit, editable memory conventions;
- a safe interchange boundary for future LMS and calendar connectors.

ScholarFS is not:

- a hosted service or student portal;
- an autonomous agent;
- a homework-answering tool;
- a replacement for an LMS;
- locked to one model or provider.

## Workspace at a glance

```text
my-semester/
├── AGENTS.md
├── README.md
├── .gitignore
├── .student/
│   ├── workspace.json
│   ├── courses.json
│   ├── deadlines.json
│   ├── notifications.json
│   ├── memory/
│   │   └── semester.md
│   ├── private/               # ignored; excluded from context by default
│   ├── connector-state/       # ignored; never credentials
│   ├── backups/               # ignored; created before connector imports
│   └── generated/             # ignored
├── courses/
│   └── CS-101/
│       ├── COURSE.md
│       ├── memory.md
│       ├── syllabus/
│       ├── assignments/
│       ├── notes/
│       ├── lectures/
│       └── resources/
└── inbox/                     # ignored until you sort it
```

Machine-readable facts have one canonical location:

- course metadata: `.student/courses.json`;
- deadlines: `.student/deadlines.json`;
- notification defaults: `.student/notifications.json`.

Markdown explains human context. It does not duplicate canonical due dates.

## Use it with file-aware assistants

`AGENTS.md` gives provider-neutral safety and memory rules. `scholarfs context` creates a deterministic handoff when a tool cannot read the workspace directly.

Useful questions include:

- “What should I work on tonight, given the open deadlines and estimated effort?”
- “Read Project 1 and help me make a plan without writing the submission for me.”
- “What course policies affect this deadline?”
- “What facts are confirmed, and what is still uncertain?”
- “Summarize the last two weeks without reading private memory.”

The assistant supplies reasoning. ScholarFS supplies visible, durable context.

## Deadlines and notifications

A deadline keeps source precision:

```json
{
  "title": "Project proposal",
  "course": "CS-101",
  "due": { "at": "2026-09-18T23:59:00-05:00" },
  "status": "pending",
  "reminders_minutes": [2880, 120]
}
```

A date-only deadline uses `{ "on": "2026-09-18" }`; ScholarFS does not invent a time. Export an ICS calendar with reminder alarms:

```bash
scholarfs calendar export deadlines.ics
```

The export includes titles, course codes, due values, kinds, status, source URLs, and reminder offsets. Free-form notes stay local unless you explicitly add `--include-notes`. v0.1 does not run a background notification daemon. Your calendar remains the notification delivery system.

## Connector boundary

There are no live LMS connectors in v0.1. External connectors may emit a normalized deadline-import JSON file. ScholarFS validates and previews it before any write:

```bash
scholarfs deadline import canvas-export.json
scholarfs deadline import canvas-export.json --apply
```

Imports are idempotent by connector and external ID, preserve locally completed items, back up the deadline file, and never delete records merely because they disappeared upstream. See [CONNECTORS.md](./docs/CONNECTORS.md).

## Documentation

- [Getting started tutorial](./docs/GETTING_STARTED.md)
- [CLI reference](./docs/CLI.md)
- [Workspace specification](./docs/WORKSPACE_SPEC.md)
- [Deadline model](./docs/DEADLINES.md)
- [Memory conventions](./docs/MEMORY.md)
- [Connector contract](./docs/CONNECTORS.md)
- [How to move an existing semester](./docs/HOW_TO_IMPORT_A_SEMESTER.md)
- [Architecture and design trade-offs](./ARCHITECTURE.md)
- [Privacy model](./PRIVACY.md)
- [Security policy](./SECURITY.md)
- [Frequently asked questions](./docs/FAQ.md)
- [Roadmap and explicit non-goals](./docs/ROADMAP.md)
- [Publishing checklist](./docs/PUBLISHING.md)
- [Changelog](./CHANGELOG.md)
- [Launch drafts](./launch/README.md)

## Project status

v0.1 is deliberately small: the standard, CLI, schemas, examples, deadline model, memory conventions, calendar export, and connector interchange. Schema changes before v1 may be breaking, but ScholarFS will never migrate a workspace silently.

## Contributing

Start with [CONTRIBUTING.md](./CONTRIBUTING.md). The test suite uses the standard library:

```bash
python -m unittest discover -s tests -v
```

## License

[MIT](./LICENSE) © 2026 ScholarFS contributors.
