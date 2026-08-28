# Lakeview University, Fall 2026

This is a completely fictional semester for exploring ScholarFS. The university, people, course policies, URLs, notes, and deadlines were invented for this repository.

From the repository root:

```bash
python -m pip install -e .
cd examples/fall-2026
scholarfs status --as-of 2026-08-28T12:00:00-05:00
scholarfs context CS-241
scholarfs validate
```

The example intentionally includes:

- two contrasting courses;
- timed and date-only deadlines;
- open, completed, and cancelled items;
- explicit semester and course memory;
- a normalized connector import;
- a private-memory convention using fake `.example.md` files.

Nothing in this directory should be treated as a real syllabus or university policy.

