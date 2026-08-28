# Offline JSON example connector

This tiny converter demonstrates the v0.1 boundary. It does not contact an LMS.

```bash
python connectors/example-json/export.py connectors/example-json/source.json > deadline-import.json

cd examples/fall-2026
scholarfs deadline import ../../deadline-import.json
```

The first ScholarFS command is preview-only. Add `--apply` only after inspecting the normalized file and preview counts.

