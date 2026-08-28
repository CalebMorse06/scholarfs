# CLI reference

ScholarFS 0.1 exposes the `scholarfs` command and `python -m scholarfs`. Both use the same implementation and make no network requests.

## Global interface

```text
scholarfs [--workspace PATH] [--version] COMMAND ...
```

| Option | Type | Default | Effect |
|---|---|---|---|
| `--workspace PATH` | path | search upward | Starts workspace discovery at `PATH`. Must appear before the command. |
| `--version` | flag | off | Prints the installed version and exits. |

Without `--workspace`, commands walk upward from the current directory until `.student/workspace.json` is found. `SCHOLARFS_WORKSPACE` sets the discovery start when the flag is absent.

Expected user errors print one line to standard error and exit `1`. Argument syntax errors exit `2`. Ctrl+C exits `130`.

## `init`

```text
scholarfs init [PATH] [--name TEXT] [--term TEXT] [--timezone TEXT] [--merge]
```

Creates a workspace. `PATH` defaults to the current directory. `--term` defaults to `My semester`; `--timezone` defaults to `local` and otherwise requires a resolvable IANA name. A name such as `America/Chicago` keeps calendar-day deadline comparisons stable when the device travels.

The target must be missing or empty. `--merge` permits a non-empty target but creates only missing files; it never replaces existing files or reconciles their content. There is intentionally no force-overwrite option.

## `course add`

```text
scholarfs course add CODE [--title TEXT] [--instructor TEXT] [--credits NUMBER]
```

Adds canonical metadata to `.student/courses.json` and creates `courses/CODE/`. Codes are normalized to uppercase and must contain 1-32 letters, digits, dots, underscores, or hyphens. Path separators, spaces, trailing dots, traversal segments, duplicate codes, and Windows device names are rejected.

`--title` defaults to the normalized code. `--instructor` and `--credits` default to `null`; credits must be between 0 and 30.

## `course list`

```text
scholarfs course list [--json]
```

Lists canonical course records in code order. `--json` prints a machine-readable object.

## `file add`

```text
scholarfs file add FILE --kind KIND [--course CODE] [--name FILENAME]
```

Copies a local regular file and appends a SHA-256 audit record to the Git-ignored `.student/import-log.jsonl`. The audit record can contain the source and destination filenames, so keep it private. The command never moves, parses, or overwrites the source. Symbolic-link sources and existing destinations are rejected.

| Kind | Course required | Destination |
|---|---:|---|
| `syllabus` | yes | `courses/CODE/syllabus/files/` |
| `assignment` | yes | `courses/CODE/assignments/imported/files/` |
| `lecture` | yes | `courses/CODE/lectures/files/` |
| `note` | yes | `courses/CODE/notes/files/` |
| `resource` | yes | `courses/CODE/resources/files/` |
| `inbox` | no; forbidden | `inbox/` |

`--name` must be one portable plain filename, not a path. Path separators, control characters, Windows device names, drive colons, and trailing dots or spaces are rejected.

## `deadline add`

```text
scholarfs deadline add TITLE [--course CODE]
  (--at RFC3339 | --on YYYY-MM-DD)
  [--kind KIND] [--url URL]
  [--remind MINUTES]...
  [--priority PRIORITY]
  [--weight PERCENT]
  [--estimate-minutes MINUTES]
  [--tag TAG]...
```

Exactly one due precision is required. `--at` requires an explicit UTC offset. `--on` preserves a date-only source without inventing a time.

Kinds: `assignment`, `exam`, `quiz`, `lab`, `project`, `reading`, `presentation`, `event`, `other`.

Priorities: `low`, `normal`, `high`, `critical`; default `normal`.

`--weight` accepts 0-100. `--estimate-minutes` must be positive. Repeating `--remind` or `--tag` creates a unique array. If no reminder is supplied, `.student/notifications.json` supplies the default.

## `deadline list`

```text
scholarfs deadline list [--course CODE]
  [--days N | --until YYYY-MM-DD | --all]
  [--include-closed]
  [--as-of RFC3339] [--json]
```

Defaults to open deadlines due within the next 14 days, plus overdue open items. `--until` is inclusive. `--include-closed` adds completed and cancelled items due today or later inside the selected forward window; use `--all` for closed history. `--all` ignores date and status filters.

`--as-of` supplies a deterministic clock for demos, tests, and audits. Day labels use the workspace timezone; timed items become overdue at their exact instant, while date-only items become overdue on the next local calendar day. Output marks a pending item for attention when it is overdue, due within three days, or has high/critical priority. This is a deterministic rule, not a prediction.

## `deadline done`, `reopen`, and `cancel`

```text
scholarfs deadline done ID_OR_PREFIX
scholarfs deadline reopen ID_OR_PREFIX
scholarfs deadline cancel ID_OR_PREFIX
```

Each accepts a full UUID or unique prefix. Ambiguous prefixes fail. Completing sets `completed_at`; reopening or cancelling clears it. Unknown extension fields already present on the record are preserved.

## `deadline import`

```text
scholarfs deadline import FILE [--apply] [--json]
```

Validates a v1 normalized connector envelope and reports add, update, unchanged, and delete counts. Preview is the default and is byte-for-byte non-mutating. `--apply` creates an ignored backup and atomically upserts by `(connector, external_id)`.

No import performs an implicit delete. See [CONNECTORS.md](./CONNECTORS.md).

## `calendar export`

```text
scholarfs calendar export FILE [--course CODE]
  [--include-completed | --exclude-completed]
  [--include-notes] [--force]
```

Writes an RFC 5545-style ICS calendar. Timed deadlines export in UTC; date-only deadlines become all-day events; reminder minutes become display alarms. Cancelled items are omitted. Completed-item behavior defaults to `notifications.calendar.include_completed`; either completion flag overrides it for one export.

Every event contains its title, course code, due value, kind, status, source URL when present, and reminders. Free-form `notes` are omitted by default because calendar files are often uploaded to cloud services. `--include-notes` opts into exporting them.

The output path may be anywhere the user can write. Existing files are refused unless `--force` explicitly names that target.

## `status`

```text
scholarfs status [--days N] [--as-of RFC3339] [--json]
```

Summarizes open, overdue, and attention-marked deadlines by course. The horizon defaults to 14 days.

## `context`

```text
scholarfs context [COURSE] [--include-private] [--max-bytes N]
  [--output PATH] [--force]
```

Prints deterministic Markdown to standard output. `--output PATH` writes atomically to a non-redirecting path inside the workspace; symlinks and Windows directory junctions are refused. Use `.student/generated/NAME.md` to keep the bundle ignored by Git. Existing files require `--force`. The default maximum is 250,000 UTF-8 bytes. Select one course to exclude unrelated course context. See [MEMORY.md](./MEMORY.md) for the exact allowlist.

`--include-private` includes immediate Markdown files from `.student/private/`. It does not include attachments or arbitrary directories.

## `validate` / `doctor`

```text
scholarfs validate [PATH] [--strict] [--json]
scholarfs doctor [PATH] [--strict] [--json]
```

The two names are aliases. Validation checks required paths, supported schema versions, course/index consistency, UUID and source uniqueness, deadline precision, status/completion invariants, reminder values, timestamps, ignore rules, symlinks and Windows directory junctions, and credential-looking filenames.

Warnings do not fail unless `--strict` is present. JSON output contains `workspace`, `ok`, `checks`, `errors`, and `warnings`.

## Related

- [Getting started](./GETTING_STARTED.md)
- [Workspace specification](./WORKSPACE_SPEC.md)
- [Deadline model](./DEADLINES.md)
- [Connector contract](./CONNECTORS.md)
