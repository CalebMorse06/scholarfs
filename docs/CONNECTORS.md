# Connector contract

ScholarFS v0.1 does not ship live LMS or calendar connectors. It defines a narrow, inspectable file interchange so those connectors can be built later without entering the trusted core.

## The boundary

```text
external program
    │ fetches or reads vendor data under its own policy
    │ emits only normalized v1 fields
    v
deadline-import.json
    │ scholarfs deadline import FILE          preview, no mutation
    │ scholarfs deadline import FILE --apply  backup + atomic upsert
    v
.student/deadlines.json
```

Core never executes the connector. A connector may be written in any language and released independently.

## Manifest

A connector repository should publish a `connector.json` matching [`connector-manifest.schema.json`](../schemas/connector-manifest.schema.json):

```json
{
  "schema_version": 1,
  "id": "example-json",
  "name": "Offline JSON example",
  "version": "0.1.0",
  "description": "Converts a static local fixture into a ScholarFS deadline import.",
  "capabilities": ["deadline-export"],
  "credential_policy": "none",
  "output_schema": "urn:scholarfs:schema:deadline-import:1"
}
```

v0.1 supports only `deadline-export`. A manifest is descriptive; ScholarFS does not discover or execute it.

## Import envelope

```json
{
  "schema_version": 1,
  "connector": {
    "id": "example-json",
    "version": "0.1.0"
  },
  "generated_at": "2026-08-27T18:00:00Z",
  "items": []
}
```

Root fields are strict. Raw payloads, credentials, cursor state, HTML, and extra vendor fields are rejected.

Schema: [`deadline-import.schema.json`](../schemas/deadline-import.schema.json).

## Import item

```json
{
  "external_id": "assignment-481",
  "course": "CS-241",
  "title": "Project 1",
  "kind": "project",
  "due": { "at": "2026-09-03T23:59:00-05:00" },
  "status": "pending",
  "url": "https://lms.example.invalid/courses/cs-241/assignments/481",
  "priority": "normal",
  "weight_percent": 12,
  "estimated_minutes": null
}
```

Required fields are `external_id`, `course`, `title`, `kind`, `due`, and `status`. Optional values default to normal or null in core. `status` is limited to `pending` or explicit `cancelled`; completion is local student state.

Every referenced course must already exist. This makes course mapping an explicit connector or user decision instead of silently creating directories from vendor names.

## Identity and idempotency

The unique import key is `(connector.id, external_id)`. Core generates a stable UUIDv5 for a new source key and preserves that ID on updates.

Importing the identical envelope again yields zero adds and updates. A later `generated_at` changes provenance and may produce an update even when academic fields are unchanged; this records the new observation boundary.

An envelope older than the stored `source.observed_at` for any matching item is rejected in full. Core does not let a delayed or replayed connector response roll confirmed fields backward, and the rejected import creates no backup or canonical write.

## Ownership and merge rules

Connector-owned values:

- course reference;
- title and kind;
- due precision;
- source URL;
- priority, weight, and estimate when supplied;
- provenance;
- explicit cancellation.

Local values preserved across ordinary re-import:

- stable ID and creation time;
- notes and tags;
- reminder offsets;
- locally completed status and completion time.

An explicit upstream cancellation changes any item to cancelled. A pending observation does not reopen a locally completed item.

## No implicit deletion

If an item disappears from a connector export, ScholarFS does nothing. Partial exports, pagination failures, permissions, and vendor outages make absence unsafe evidence. The connector must emit `status: "cancelled"` to cancel a record.

Preview always reports `deletes: 0` in v0.1.

## Credentials and state

Keep tokens in environment variables or the operating-system credential store. Never write them into:

- the manifest;
- the normalized import;
- `.student/connector-state/`;
- URLs;
- logs or error messages.

Ignored `.student/connector-state/` is for non-secret cursors, synchronization timestamps, and vendor-to-course mapping choices.

## Apply workflow

1. Run the connector separately.
2. Open the normalized JSON and inspect its scope.
3. Preview:

   ```bash
   scholarfs deadline import deadline-import.json
   ```

4. Resolve unknown courses or invalid fields.
5. Apply:

   ```bash
   scholarfs deadline import deadline-import.json --apply
   ```

6. Run `scholarfs validate`.

Apply writes a timestamped copy under `.student/backups/` before atomically replacing the canonical deadline file. Backups are ignored by Git.

## Build a connector

Your connector should:

1. authenticate outside core;
2. fetch the smallest necessary scope;
3. map vendor course IDs to existing ScholarFS course codes;
4. retain source precision and explicit offsets;
5. emit deterministic external IDs;
6. strip credentials and arbitrary raw fields;
7. validate against the published schema;
8. test pagination, partial failures, cancellation, and duplicate IDs;
9. document its network and data-retention behavior independently.

Use [`connectors/example-json`](../connectors/example-json/) as an offline executable example.

## Troubleshooting

### Unknown course

Add the course first or fix the connector's mapping. Core never guesses.

### Unsupported field

Transform it into a published field, omit it, or propose a schema change. Do not embed a `raw` object.

### Duplicate source key

Fix the connector's external-ID mapping or repair the existing duplicate before applying. ScholarFS will not choose one record silently.

### Stale import

Generate a fresh connector snapshot. ScholarFS refuses an observation older than the matching record already stored; it has no force flag that can silently roll deadline data backward.

## Related

- [Deadline model](./DEADLINES.md)
- [Privacy model](../PRIVACY.md)
- [Architecture](../ARCHITECTURE.md)
