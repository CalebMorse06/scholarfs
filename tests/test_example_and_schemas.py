from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from scholarfs.validation import validate_workspace


REPOSITORY = Path(__file__).resolve().parents[1]
EXAMPLE = REPOSITORY / "examples" / "fall-2026"


class ExampleTests(unittest.TestCase):
    def test_fake_semester_passes_core_validation(self) -> None:
        report = validate_workspace(EXAMPLE)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_reference_connector_matches_checked_in_import(self) -> None:
        result = subprocess.run(
            [sys.executable, str(REPOSITORY / "connectors" / "example-json" / "export.py"), str(REPOSITORY / "connectors" / "example-json" / "source.json")],
            check=True,
            capture_output=True,
            text=True,
        )
        generated = json.loads(result.stdout)
        checked_in = json.loads((EXAMPLE / "imports" / "example-json.deadline-import.json").read_text(encoding="utf-8"))
        self.assertEqual(generated, checked_in)

    def test_examples_match_published_json_schemas_when_jsonschema_is_installed(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is an optional development dependency")
        pairs = [
            (EXAMPLE / ".student" / "workspace.json", REPOSITORY / "schemas" / "workspace.schema.json"),
            (EXAMPLE / ".student" / "courses.json", REPOSITORY / "schemas" / "courses.schema.json"),
            (EXAMPLE / ".student" / "deadlines.json", REPOSITORY / "schemas" / "deadlines.schema.json"),
            (EXAMPLE / ".student" / "notifications.json", REPOSITORY / "schemas" / "notifications.schema.json"),
            (EXAMPLE / "imports" / "example-json.deadline-import.json", REPOSITORY / "schemas" / "deadline-import.schema.json"),
            (REPOSITORY / "connectors" / "example-json" / "connector.json", REPOSITORY / "schemas" / "connector-manifest.schema.json"),
        ]
        checker = jsonschema.FormatChecker()
        for instance_path, schema_path in pairs:
            with self.subTest(instance=instance_path.name):
                instance = json.loads(instance_path.read_text(encoding="utf-8"))
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator(schema, format_checker=checker).validate(instance)

