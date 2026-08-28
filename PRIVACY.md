# Privacy model

ScholarFS is local-first, not magically private. Core does not transmit data, but a semester workspace can contain schedules, instructor information, grades, accommodations, copyrighted materials, and personal notes. Treat it as private by default.

## What core does

The ScholarFS CLI:

- reads and writes the workspace you select;
- creates no account;
- makes no network requests;
- contains no telemetry or analytics client;
- handles no LMS, calendar, or AI credentials;
- stores no hidden database;
- excludes `.student/private/` from context bundles unless you pass `--include-private`;
- refuses redirecting descendants such as symlinks and Windows directory junctions at workspace read/write boundaries;
- previews connector imports before applying them.

These statements describe the code in this repository at v0.1. Verify them again when installing a fork or future release.

## What core cannot guarantee

If you open the workspace with an external AI assistant, sync service, editor extension, connector, cloud backup, or calendar, that tool may read or transmit files under its own policy. ScholarFS does not sandbox other software.

`scholarfs context` makes a handoff visible, but it cannot control what happens after you paste or upload the bundle. A normal bundle contains the full canonical records for relevant pending deadlines, including their free-form notes and source URLs. Inspect it before sharing.

## Default data boundaries

Generated `.gitignore` rules exclude:

- `.student/private/`;
- connector state, backups, cache, generated context, and the filename-bearing file-import audit log;
- `.env` files and common key or credential filenames;
- raw inbox contents;
- common course attachment directories;
- virtual environments and operating-system metadata.

Git ignore rules prevent accidental tracking; they do not encrypt or delete a file. A file already committed remains in history even after it is ignored.

Calendar files are deliberate exports but may be uploaded by the calendar application. They include course codes, deadline titles and times, kinds, status, source URLs, and reminders. Free-form deadline notes are excluded unless `--include-notes` is explicit. Inspect an ICS file before importing or sharing it.

## Memory guidance

Tracked memory should contain only durable academic context the student expects to reuse. Do not store:

- passwords, API keys, session cookies, or recovery codes;
- government identifiers;
- health or financial records;
- inferred personal facts;
- grades, accommodations, or disciplinary information unless the student explicitly chooses to retain them and understands the exposure.

Personal preferences belong in `.student/private/`, but secrets still do not.

## Repository guidance

Use a private repository for a real semester. Before publishing any workspace:

1. Run `scholarfs validate` and resolve privacy warnings.
2. Inspect `git status --ignored`.
3. Search history, not only the working tree, for secrets and student data.
4. Remove copyrighted course files unless redistribution is allowed.
5. Replace names, URLs, IDs, schedules, and content with clearly fictional fixtures.

The public `examples/fall-2026` directory is invented from scratch for this reason.

## Connector guidance

Keep tokens in environment variables or the operating-system credential store. Keep local cursors in ignored `.student/connector-state/`. A normalized import must contain only fields defined by the schema, never raw LMS payloads, HTML pages, cookies, access tokens, or full API responses.

Core never executes a connector. Review the normalized JSON and preview counts before `--apply`.

## Deleting local data

ScholarFS has no cloud account to delete. Remove the workspace files and any copies you created in Git remotes, backups, sync tools, AI conversations, or calendar imports. Those external copies are outside ScholarFS.

## Reporting a privacy issue

Follow [SECURITY.md](./SECURITY.md). Do not attach a real workspace or include personal data in a public issue.
