# Frequently asked questions

## Is ScholarFS an AI student planner?

No. It is a student-owned file standard plus a conservative CLI. An assistant can reason over the context, but ScholarFS does not ship a model, make plans autonomously, or complete coursework.

## Do I need an AI assistant?

No. The workspace, deadline list, validation, file capture, and calendar export are useful on their own.

## Which AI providers work?

Tools that can read local files or accept a Markdown context bundle can use the workspace. ScholarFS has no provider SDK and does not claim identical capabilities across tools.

## Why Markdown and JSON instead of a database?

Markdown is easy to inspect and maintain; JSON has unambiguous standard-library parsing and published schemas. A database would improve complex queries but become the real source of truth. ScholarFS optimizes for one student's portable semester.

## Why not YAML?

YAML is friendly for comments but requires a parser dependency and has more implicit typing behavior. ScholarFS keeps comments and explanation in Markdown and machine facts in JSON.

## Does ScholarFS sync Canvas, Blackboard, or Moodle?

Not in v0.1. It defines a normalized, preview-first import format so live connectors can remain separate from the trusted core. The checked-in connector is offline and uses a static fixture.

## Does it send telemetry?

No. Core contains no analytics client and makes no network request.

## Is a workspace safe to publish?

Assume no. Real workspaces can reveal schedules, instructor details, grades, private notes, and copyrighted materials. Use a private repository and follow [PRIVACY.md](../PRIVACY.md).

## Why are private preferences separate?

Semester and course memory are routinely included in context. Personal constraints need a stronger boundary. `.student/private/` is ignored and opt-in for context, which makes that choice visible.

## Can I edit the JSON by hand?

Yes. Run `scholarfs validate` afterward. The CLI preserves existing record fields during status changes, but published v1 schemas reject unknown extensions.

## Why must timed deadlines include an offset?

`2026-09-04T23:59:00` is ambiguous across machines and travel. `-05:00` or `Z` makes it one instant. A source with no time should use the date-only shape instead.

## What does “needs attention” mean?

It is a transparent rule: pending and overdue, due within three days, or marked high/critical priority. It is not a predicted grade or AI risk score.

## Will calendar export keep itself synchronized?

No. v0.1 writes an ICS file. Your calendar application controls import, updates, deduplication, and notifications.

## What happens if an imported LMS item disappears?

Nothing. Absence may mean pagination or permission failure. A connector must export explicit cancellation; ScholarFS never treats omission as permission to delete.

## Can ScholarFS parse a syllabus PDF?

No. `file add` copies and hashes a source; it does not parse it. Syllabus extraction is a possible future draft workflow, but extracted dates must never become confirmed deadlines silently.

## Can I use an existing directory?

`scholarfs init --merge` adds missing scaffold files but never overwrites. Review the created `.gitignore` and move existing material deliberately.

## How do I remove ScholarFS?

Uninstall the Python package. The workspace remains ordinary files. Remove `.student/` only if you also want to discard canonical course/deadline data and memory.

## Why ScholarFS?

The name describes the durable layer: a scholar-owned filesystem. Maintainers should recheck repository and package-name availability before each first publication to a new registry.
