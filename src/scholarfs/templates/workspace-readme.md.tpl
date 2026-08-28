# $workspace_name

This is a ScholarFS workspace for **$term**. The files are the source of truth; the CLI only helps create, validate, summarize, and export them.

## Start here

```text
.student/workspace.json       Workspace settings
.student/courses.json         Canonical course index
.student/deadlines.json       Canonical deadlines
.student/memory/semester.md   Durable semester context
courses/                      Course context and materials
inbox/                        Unsorted files and notes
AGENTS.md                     Rules for file-aware AI assistants
```

Useful commands:

```bash
scholarfs course add CS-101 --title "Introduction to Computer Science"
scholarfs deadline add "Problem set 1" --course CS-101 --on 2026-09-04
scholarfs deadline list --days 14
scholarfs context CS-101 --output .student/generated/cs-101-context.md
scholarfs validate
```

## Privacy

Treat this workspace as private. The generated `.gitignore` excludes personal memory, connector state, backups, generated context, file-import audit logs, common attachments, caches, and common credential files. Review [AGENTS.md](./AGENTS.md) before giving an AI assistant access.

ScholarFS itself makes no network requests and has no telemetry. External AI tools and future connectors have their own policies.
