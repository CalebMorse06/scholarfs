# How to move an existing semester into ScholarFS

This guide turns an existing folder, syllabus collection, and calendar list into a clean workspace without asking ScholarFS to parse or upload anything.

## Prerequisites

- ScholarFS installed
- your current files available locally
- authoritative due dates visible in the LMS, syllabus, or calendar
- enough time to verify conflicts instead of bulk-copying guesses

## Steps

1. Create an empty workspace.

   ```bash
   scholarfs init fall-2026 --term "Fall 2026" --timezone America/Chicago
   cd fall-2026
   ```

2. Add courses from the official enrollment list.

   ```bash
   scholarfs course add CS-241 --title "Systems Programming"
   scholarfs course add STAT-210 --title "Applied Statistics"
   ```

   Open each `COURSE.md` and summarize only confirmed purpose, policies, and useful links. Cite the source section for policies that affect grades or deadlines.

3. Copy source files conservatively.

   ```bash
   scholarfs file add ../old-files/cs241-syllabus.pdf --course CS-241 --kind syllabus
   scholarfs file add ../old-files/stat-notes.txt --course STAT-210 --kind note
   ```

   `file add` copies, hashes, and logs the destination. It does not parse the content or remove the source. Common attachment directories are ignored by Git.

4. Normalize deadlines from authoritative sources.

   ```bash
   scholarfs deadline add "Project 1" \
     --course CS-241 \
     --at 2026-09-03T23:59:00-05:00 \
     --kind project \
     --weight 12

   scholarfs deadline add "Homework 2" \
     --course STAT-210 \
     --on 2026-08-31 \
     --kind assignment
   ```

   Preserve date-only deadlines. If the LMS and syllabus disagree, do not choose silently: record the conflict in the assignment README and confirm it.

5. Create assignment context.

   Make `courses/CODE/assignments/assignment-name/README.md`. Record the deadline UUID printed by the CLI, deliverable, constraints, source, and checklist. Do not copy the due timestamp into Markdown.

6. Add only durable memory.

   Use `.student/memory/semester.md` for semester goals and `courses/CODE/memory.md` for course decisions or confirmed policies. Date and source every durable entry. Keep personal schedule constraints in `.student/private/` only if they are useful.

7. Export calendar reminders.

   ```bash
   scholarfs calendar export deadlines.ics
   ```

   Import the file into the calendar you already trust. ScholarFS does not create a remote subscription or remove old events, so check for duplicates if you previously added the same deadlines manually.

8. Validate and review privacy.

   ```bash
   scholarfs validate --strict
   ```

   Inspect `.gitignore`, `git status --ignored`, and the files you plan to provide to an AI assistant. Keep the real workspace in a private repository if you use Git.

## Verification

```bash
scholarfs course list
scholarfs deadline list --all
scholarfs context CS-241 --output .student/generated/review-context.md
scholarfs validate
```

Open `.student/generated/review-context.md`. It should contain only the selected course, open deadlines, and explicit memory. Delete the generated bundle when you no longer need it.

## Troubleshooting

### There are too many files

Leave raw material in the ignored inbox and migrate active courses first. ScholarFS is not a mandate to classify every historical download.

### A due date has no time

Use `--on`. Do not infer 23:59 from habit.

### A PDF contains the only policy source

Keep the PDF private and write a short, cited policy summary in `COURSE.md`. ScholarFS v0.1 does not extract PDFs.

### The calendar already contains deadlines

Import into a temporary calendar first or inspect the ICS before merging. v0.1 does not reconcile remote event IDs.

## Related

- [Getting started](./GETTING_STARTED.md)
- [Deadline reference](./DEADLINES.md)
- [Memory conventions](./MEMORY.md)
- [Privacy model](../PRIVACY.md)
