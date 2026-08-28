# Deadline model reference

ScholarFS normalizes deadlines without erasing source precision or provenance. `.student/deadlines.json` is canonical.

## Root object

```json
{
  "schema_version": 1,
  "deadlines": []
}
```

## Record

```json
{
  "id": "a1241001-14da-4b1f-8a5e-2a6d6d9c1001",
  "course": "CS-241",
  "title": "Project 1: Unix shell",
  "kind": "project",
  "due": { "at": "2026-09-03T23:59:00-05:00" },
  "status": "pending",
  "priority": "normal",
  "weight_percent": 12,
  "estimated_minutes": 480,
  "source": { "type": "manual" },
  "url": null,
  "reminders_minutes": [2880, 120],
  "tags": ["coding", "individual"],
  "notes": "Run the provided test script before packaging.",
  "created_at": "2026-08-21T14:00:00Z",
  "updated_at": "2026-08-21T14:00:00Z",
  "completed_at": null
}
```

## Fields

| Field | Type | Constraint and meaning |
|---|---|---|
| `id` | UUID string | Stable local identity. Connector-created IDs are deterministic UUIDv5 values. |
| `course` | course code or null | Null means semester-wide. Non-null values must exist in the course index. |
| `title` | string | 1-500 characters. |
| `kind` | enum | `assignment`, `exam`, `quiz`, `lab`, `project`, `reading`, `presentation`, `event`, `other`. |
| `due` | object | Exactly one of `at` or `on`. |
| `status` | enum | `pending`, `completed`, `cancelled`. |
| `priority` | enum | `low`, `normal`, `high`, `critical`. Human-set, not predicted. |
| `weight_percent` | number or null | 0-100; null means unknown or not graded. |
| `estimated_minutes` | positive integer or null | Planning estimate, not elapsed time. |
| `source` | provenance object | Manual or connector. |
| `url` | HTTP(S) URL or null | A source link; never a credential-bearing URL. |
| `reminders_minutes` | integer array | Unique non-negative minutes before due. |
| `tags` | string array | Unique local labels. |
| `notes` | string | Short local note. Assignment detail belongs in Markdown. |
| `created_at`, `updated_at` | RFC 3339 strings | Explicit offset or `Z`. |
| `completed_at` | RFC 3339 or null | Required only for `completed`; null otherwise. |

Schema: [`deadlines.schema.json`](../schemas/deadlines.schema.json).

## Due precision

Timed:

```json
{ "at": "2026-09-03T23:59:00-05:00" }
```

The offset is mandatory. ScholarFS compares timed values as instants and exports them to ICS in UTC.

Date-only:

```json
{ "on": "2026-09-03" }
```

This means “due by the end of that date in the workspace's human context.” It exports as an all-day calendar event. ScholarFS does not turn it into 23:59, because that would fabricate precision the source did not provide.

## Status invariants

```text
pending   -> completed  (`deadline done` sets completed_at)
pending   -> cancelled  (`deadline cancel` clears completed_at)
completed -> pending    (`deadline reopen` clears completed_at)
cancelled -> pending    (`deadline reopen` clears completed_at)
```

All transitions preserve unknown human fields already present in the JSON object. A connector cannot silently mark a locally completed item pending; it may explicitly cancel it.

## Manual provenance

```json
{ "type": "manual" }
```

Manual means a person or local agent created the normalized record through the trusted workspace boundary. It does not prove the date is correct; cite the actual source in the assignment Markdown when ambiguity matters.

## Connector provenance

```json
{
  "type": "connector",
  "connector": "example-json",
  "connector_version": "0.1.0",
  "external_id": "stat-quiz-02",
  "observed_at": "2026-08-27T18:00:00Z"
}
```

`(connector, external_id)` is unique and drives idempotent upsert. `observed_at` records when the external state was represented, not when the import was applied.

## Import ownership

A connector owns the normalized source fields it reports: course, title, kind, due precision, URL, priority, weight, estimate, provenance, and explicit upstream cancellation. ScholarFS preserves local notes, tags, reminders, stable ID, creation time, and locally completed status during ordinary re-observation.

Missing upstream items are never deleted or cancelled. A connector must export `status: "cancelled"` explicitly.

## Attention rule

Calendar-day labels use the workspace timezone. A timed item becomes overdue at its exact instant even when its label is still the same local day; a date-only item becomes overdue when the next local date begins.

CLI list and status output mark a pending item with `attention: true` when any condition holds:

- it is overdue;
- it is due within three days;
- priority is `high` or `critical`.

This is a transparent sorting aid, not an AI risk score. Weight and estimated effort remain visible for an assistant or person to reason about.

## Reminders and calendar export

Manual deadlines copy default reminder offsets at creation. ICS export converts each offset to a display alarm. It omits cancelled items; completed items follow `notifications.calendar.include_completed` unless an export flag overrides the setting. Calendar events contain the course code, title, due value, kind, status, source URL, and reminders. Free-form deadline notes are omitted unless `--include-notes` is explicit.

Calendar applications may interpret or deduplicate imported ICS files differently. v0.1 exports a file; it does not maintain a remote subscription or remove events from a calendar you already imported.

## Examples

```bash
scholarfs deadline add "Final presentation" \
  --course CS-241 \
  --at 2026-12-09T13:00:00-06:00 \
  --kind presentation \
  --priority high \
  --weight 20 \
  --remind 10080 \
  --remind 1440

scholarfs deadline add "Registration opens" \
  --on 2026-10-12 \
  --kind event
```

## Related

- [CLI reference](./CLI.md)
- [Connector contract](./CONNECTORS.md)
- [Workspace specification](./WORKSPACE_SPEC.md)
