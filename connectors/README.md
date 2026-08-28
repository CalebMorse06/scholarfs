# Connectors

ScholarFS v0.1 uses a file boundary, not an in-process plugin system.

```text
external connector
    -> normalized deadline-import JSON
    -> scholarfs deadline import FILE       (preview)
    -> scholarfs deadline import FILE --apply
    -> backup + atomic upsert into .student/deadlines.json
```

Core never executes a connector, stores its credentials, or accepts arbitrary raw LMS payloads. A connector can be written in any language if it emits [`deadline-import.schema.json`](../schemas/deadline-import.schema.json).

The [`example-json`](./example-json/) connector is deliberately offline. It converts a small static source file into the interchange format so maintainers can test the boundary without an account, token, or network request.

See [the connector guide](../docs/CONNECTORS.md) before building a real integration.

