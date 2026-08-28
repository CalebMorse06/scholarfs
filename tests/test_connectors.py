from __future__ import annotations

import json
import unittest
from pathlib import Path

from scholarfs.connectors import apply_deadline_import, plan_deadline_import
from scholarfs.utils import ScholarFSError
from scholarfs.workspace import add_course

from tests.helpers import WorkspaceFixture


REPOSITORY = Path(__file__).resolve().parents[1]


class ConnectorTests(WorkspaceFixture, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        add_course(self.root, "STAT-210", title="Applied Statistics")
        self.envelope = self.root / "import.json"
        self.envelope.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "connector": {"id": "test-lms", "version": "0.1.0"},
                    "generated_at": "2026-08-27T18:00:00Z",
                    "items": [
                        {
                            "external_id": "quiz-2",
                            "course": "STAT-210",
                            "title": "Quiz 2",
                            "kind": "quiz",
                            "due": {"on": "2026-09-05"},
                            "status": "pending",
                            "url": None,
                            "priority": "normal",
                            "weight_percent": 3,
                            "estimated_minutes": None,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_preview_is_nonmutating_and_apply_is_idempotent(self) -> None:
        deadlines = self.root / ".student" / "deadlines.json"
        before = deadlines.read_bytes()
        plan, _ = plan_deadline_import(self.root, self.envelope)
        self.assertEqual(plan["adds"], 1)
        self.assertEqual(deadlines.read_bytes(), before)

        applied = apply_deadline_import(self.root, self.envelope)
        self.assertEqual(applied["adds"], 1)
        self.assertTrue((self.root / applied["backup"]).is_file())
        repeated = apply_deadline_import(self.root, self.envelope)
        self.assertEqual(repeated["unchanged"], 1)
        self.assertEqual(repeated["adds"], 0)
        data = json.loads(deadlines.read_text(encoding="utf-8"))
        self.assertEqual(len(data["deadlines"]), 1)

    def test_import_rejects_title_longer_than_schema_limit(self) -> None:
        payload = json.loads(self.envelope.read_text(encoding="utf-8"))
        payload["items"][0]["title"] = "x" * 501
        self.envelope.write_text(json.dumps(payload), encoding="utf-8")
        deadlines = self.root / ".student" / "deadlines.json"
        before = deadlines.read_bytes()

        with self.assertRaisesRegex(ScholarFSError, "title must not exceed 500 characters"):
            apply_deadline_import(self.root, self.envelope)

        self.assertEqual(deadlines.read_bytes(), before)

    def test_import_requires_published_fields_and_normalized_course_code(self) -> None:
        payload = json.loads(self.envelope.read_text(encoding="utf-8"))
        del payload["items"][0]["status"]
        self.envelope.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ScholarFSError, "missing required fields: status"):
            plan_deadline_import(self.root, self.envelope)

        payload["items"][0]["status"] = "pending"
        payload["items"][0]["course"] = "stat-210"
        self.envelope.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ScholarFSError, "normalized uppercase form"):
            plan_deadline_import(self.root, self.envelope)

    def test_import_rejects_boolean_version_and_non_string_enums(self) -> None:
        payload = json.loads(self.envelope.read_text(encoding="utf-8"))
        payload["schema_version"] = True
        self.envelope.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ScholarFSError, "schema_version must be integer 1"):
            plan_deadline_import(self.root, self.envelope)

        payload["schema_version"] = 1
        for field in ("kind", "status", "priority"):
            candidate = json.loads(json.dumps(payload))
            candidate["items"][0][field] = []
            self.envelope.write_text(json.dumps(candidate), encoding="utf-8")
            with self.subTest(field=field), self.assertRaises(ScholarFSError):
                plan_deadline_import(self.root, self.envelope)

    def test_import_schema_and_core_share_connector_version_limit(self) -> None:
        payload = json.loads(self.envelope.read_text(encoding="utf-8"))
        payload["connector"]["version"] = "v" * 51
        self.envelope.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ScholarFSError, "up to 50 characters"):
            plan_deadline_import(self.root, self.envelope)
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is an optional development dependency")
        schema = json.loads((REPOSITORY / "schemas" / "deadline-import.schema.json").read_text(encoding="utf-8"))
        self.assertTrue(list(jsonschema.Draft202012Validator(schema).iter_errors(payload)))

    def test_import_rejects_stale_snapshot_without_mutation(self) -> None:
        apply_deadline_import(self.root, self.envelope)
        deadlines = self.root / ".student" / "deadlines.json"
        before = deadlines.read_bytes()
        backups = self.root / ".student" / "backups"
        backups_before = sorted(backups.iterdir())

        payload = json.loads(self.envelope.read_text(encoding="utf-8"))
        payload["generated_at"] = "2026-08-26T18:00:00Z"
        payload["items"][0]["title"] = "Stale quiz title"
        payload["items"][0]["due"] = {"on": "2026-09-01"}
        self.envelope.write_text(json.dumps(payload), encoding="utf-8")

        with self.assertRaisesRegex(ScholarFSError, "stale deadline import for test-lms / quiz-2"):
            apply_deadline_import(self.root, self.envelope)

        self.assertEqual(deadlines.read_bytes(), before)
        self.assertEqual(sorted(backups.iterdir()), backups_before)
