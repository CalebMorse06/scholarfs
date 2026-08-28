# Build your first ScholarFS semester

You will create a local semester, add one course and deadline, export calendar reminders, and produce a context bundle an AI assistant can read. The ScholarFS CLI makes no network requests; installing Python packages may use your configured package index.

## What you need

- Python 3.11 or newer
- a terminal: PowerShell, Terminal, or any ordinary shell
- this repository cloned or downloaded

## Step 1: Install the CLI

From the ScholarFS repository:

```bash
python -m pip install .
scholarfs --version
```

Expected result:

```text
ScholarFS 0.1.0
```

Use `pipx install .` or `uv tool install .` if you prefer an isolated command-line installation.
On Windows, installation includes Python's `tzdata` package for portable IANA timezone handling.

## Step 2: Create a semester

```bash
scholarfs init my-semester --name "My Fall Semester" --term "Fall 2026" --timezone America/Chicago
cd my-semester
```

You now have visible Markdown and JSON files. Open `README.md`, `AGENTS.md`, and `.student/workspace.json` in any editor. ScholarFS refuses a non-empty destination; `--merge` adds only missing files and still never overwrites.

## Step 3: Add a course and a real deadline shape

```bash
scholarfs course add CS-101 --title "Introduction to Computer Science" --credits 3
scholarfs deadline add "Problem set 1" --course CS-101 --at 2026-09-04T23:59:00-05:00 --weight 5 --estimate-minutes 180 --remind 2880 --remind 120
```

The commands work unchanged in PowerShell and ordinary shells. The timestamp includes `-05:00`; ScholarFS rejects timed deadlines without an explicit offset.

Open `courses/CS-101/COURSE.md` and add the course purpose and any policy worth remembering. Put due dates only in `.student/deadlines.json` so they cannot drift between copies.

## Step 4: See the next two weeks

```bash
scholarfs status --days 14
scholarfs deadline list --days 14
```

The first eight characters of each ID are a usable unique prefix. Mark an item complete with the prefix shown:

```bash
scholarfs deadline done 12ab34cd
```

Use the actual prefix from your output.

## Step 5: Export reminders

```bash
scholarfs calendar export deadlines.ics
```

Inspect `deadlines.ics`, then import it into your calendar application. The file includes course codes, titles, due values, kinds, status, source URLs, and reminder offsets. Free-form deadline notes are omitted unless you explicitly pass `--include-notes`. ScholarFS does not run a scheduler or modify a remote calendar.

The export refuses to replace an existing file unless you pass `--force` for that exact path.

## Step 6: Create AI-readable context

```bash
scholarfs context CS-101 --output .student/generated/cs-101-context.md
```

Inspect `.student/generated/cs-101-context.md` before providing it to an assistant. It contains:

- workspace and course metadata;
- full open CS-101 deadline records, including deadline notes and source URLs;
- root agent rules;
- semester and CS-101 memory.

It omits private memory, attachments, inbox files, bulk notes, and other courses. Add `--include-private` only when the task truly needs personal context and you understand the external tool's policy.

## Step 7: Validate the workspace

```bash
scholarfs validate
```

Expected result ends with zero errors. Warnings identify privacy footguns such as a credential-looking file or missing ignore rule.

## What you built

You now have a portable semester workspace whose useful state is readable without ScholarFS. The CLI adds safe mutations, validation, context generation, and calendar export.

Next:

- [move an existing semester into the structure](./HOW_TO_IMPORT_A_SEMESTER.md);
- [understand the memory conventions](./MEMORY.md);
- [review every command and option](./CLI.md);
- [explore the fake semester](../examples/fall-2026/).

## Troubleshooting

### `scholarfs` is not recognized

Your Python scripts directory is not on `PATH`, or you installed into a different environment. Activate that environment, use `pipx install .`, or run:

```bash
python -m scholarfs --help
```

### No workspace found

Run the command inside the semester, pass `--workspace PATH` before the command, or set `SCHOLARFS_WORKSPACE`.

```bash
scholarfs --workspace /path/to/my-semester status
```

### The timestamp was rejected

Use a date-only value with `--on YYYY-MM-DD`, or include an offset with `--at`, such as `2026-09-04T23:59:00-05:00` or `2026-09-05T04:59:00Z`.
