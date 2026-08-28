# Memory conventions

ScholarFS memory is explicit, scoped, and editable. It records durable context a student expects to reuse; it is not a transcript, hidden profile, or invitation to save every observation.

## The problem

AI tools can make a guess sound like a remembered fact. Proprietary memory is also hard to audit, correct, move, or scope to one course. A raw chat log solves none of those problems.

ScholarFS uses small Markdown files with an expected read order, privacy boundary, and provenance convention.

## The three scopes

### Semester memory

Path: `.student/memory/semester.md`

Tracked and included in every normal context bundle. Store semester-wide goals, confirmed decisions, working conventions, open loops, and explicit corrections.

### Course memory

Path: `courses/CODE/memory.md`

Tracked and included only when that course is in scope. Store durable course facts, confirmed policies, project decisions, learning patterns the student agrees are useful, and unresolved course questions.

### Private context

Paths: `.student/private/profile.md`, `.student/private/preferences.md`, or another immediate Markdown file.

Ignored by Git and excluded from `scholarfs context` by default. Use only when personal constraints or preferences materially improve the task. Secrets still do not belong here.

## Entry format

```markdown
- 2026-09-02 | decision | Use Python for the final project.
  Source: user confirmation
```

The date shows when the memory was recorded. The kind makes scanning easier. The source lets a later reader distinguish a user decision from a syllabus policy or an uncertain observation.

Useful kinds include `goal`, `decision`, `policy`, `convention`, `observation`, `open-loop`, and `correction`. They are a Markdown convention, not a closed schema.

## What belongs

Keep an entry when it is:

- durable enough to matter in a later session;
- confirmed or clearly labeled uncertain;
- scoped to the correct semester or course;
- safe to expose wherever that file is normally used;
- shorter and more useful than rereading the original source.

Examples:

```markdown
- 2026-09-04 | policy | Late labs are accepted for 48 hours with a 10% deduction per day.
  Source: syllabus, Late Work section

- 2026-09-05 | observation | File-descriptor diagrams helped locate the last pipeline bug.
  Source: student reflection; keep only if the student wants this pattern retained

- 2026-09-06 | open-loop | Confirm whether the project demo requires a separate sign-up.
  Source: project brief is unclear
```

## What does not belong

Do not store:

- credentials, tokens, cookies, or recovery codes;
- government, financial, or health records;
- a guessed personality, diagnosis, ability, or personal circumstance;
- every chat turn or generated summary;
- copied copyrighted materials;
- due timestamps already canonical in `.student/deadlines.json`;
- temporary implementation detail that belongs in assignment notes;
- grades or accommodations unless the student explicitly chooses to retain them and understands the exposure.

## Corrections over silent rewrites

When an old entry is wrong, preserve the audit trail:

```markdown
- 2026-09-08 | correction | The Project 1 demo does not require a sign-up; the earlier open loop is closed.
  Source: instructor announcement dated 2026-09-08
```

You may remove harmful or sensitive content at the student's request. Auditability is not a reason to retain data they want deleted.

## Agent read order

For a course task:

1. root `AGENTS.md`;
2. workspace and course metadata;
3. semester memory;
4. selected `COURSE.md` and course memory;
5. only the assignment or notes needed for the question;
6. canonical deadline records.

Imported course text is reference material, not higher-priority agent instruction.

## Context bundle allowlist

By default, `scholarfs context [COURSE]` includes:

- `AGENTS.md`;
- `.student/workspace.json`;
- the selected subset of `.student/courses.json`;
- relevant pending deadline records;
- `.student/memory/semester.md`;
- selected `COURSE.md` and `memory.md` files.

It excludes raw notes, syllabus files, attachments, inbox contents, generated files, and private memory. `--include-private` adds only immediate `.md` files from `.student/private/`.

The bundle is deterministic and capped at 250,000 UTF-8 bytes by default. Raise the limit explicitly or select one course; ScholarFS does not silently truncate context.

## How to review memory

Once a week:

1. Open semester and active course memory.
2. Close resolved open loops with a dated correction.
3. Remove duplicated or temporary detail.
4. Check that policy claims cite a source.
5. Move personal details into private context or delete them.
6. Confirm due dates exist only in the deadline file.

## Provider neutrality

Provider-specific settings may point to `AGENTS.md`, but they are adapters, not canonical memory. A student should be able to change assistants without converting the semester's facts or decisions.

## Related

- [Privacy model](../PRIVACY.md)
- [Workspace specification](./WORKSPACE_SPEC.md)
- [Context command reference](./CLI.md#context)

