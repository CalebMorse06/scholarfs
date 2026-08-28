from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from scholarfs.deadlines import add_deadline, list_deadlines, set_deadline_status
from scholarfs.utils import ScholarFSError
from scholarfs.utils import load_json, write_json
from scholarfs.workspace import add_course

from tests.helpers import WorkspaceFixture


class DeadlineTests(WorkspaceFixture, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        add_course(self.root, "CS-241", title="Systems Programming")

    def test_timed_deadline_requires_explicit_offset(self) -> None:
        for value in ("2026-09-03T23:59:00", "2026-09-03 23:59:00-05:00", "20260903T235900-05:00"):
            with self.subTest(value=value), self.assertRaises(ScholarFSError):
                add_deadline(
                    self.root,
                    "Project",
                    course="CS-241",
                    at=value,
                    on=None,
                )

    def test_add_list_and_status_round_trip(self) -> None:
        item = add_deadline(
            self.root,
            "Project",
            course="CS-241",
            at="2026-09-03T23:59:00-05:00",
            on=None,
            weight_percent=12,
            estimated_minutes=480,
        )
        as_of = datetime.fromisoformat("2026-08-28T12:00:00-05:00")
        selected = list_deadlines(self.root, days=14, as_of=as_of)
        self.assertEqual([record["id"] for record in selected], [item["id"]])
        completed = set_deadline_status(self.root, item["id"][:8], "completed")
        self.assertEqual(completed["status"], "completed")
        self.assertIsNotNone(completed["completed_at"])
        closed = list_deadlines(self.root, all_items=True, as_of=datetime.fromisoformat("2026-09-05T12:00:00-05:00"))[0]
        self.assertFalse(closed["overdue"])
        reopened = set_deadline_status(self.root, item["id"], "pending")
        self.assertIsNone(reopened["completed_at"])

    def test_date_only_precision_is_preserved(self) -> None:
        item = add_deadline(self.root, "Homework", course="CS-241", at=None, on="2026-08-31")
        self.assertEqual(item["due"], {"on": "2026-08-31"})

    def test_deadline_url_rejects_whitespace_and_embedded_credentials(self) -> None:
        for value in ("https://example.invalid/a b", "https://token@example.invalid/task", "http://[::1"):
            with self.subTest(value=value), self.assertRaises(ScholarFSError):
                add_deadline(
                    self.root,
                    "Unsafe URL",
                    course="CS-241",
                    at=None,
                    on="2026-08-31",
                    url=value,
                )

    def test_boolean_reminders_are_rejected(self) -> None:
        with self.assertRaises(ScholarFSError):
            add_deadline(
                self.root,
                "Bad reminder",
                course="CS-241",
                at=None,
                on="2026-08-31",
                reminders=[True],
            )

    def test_missing_notification_defaults_cannot_silently_drop_reminders(self) -> None:
        notifications = self.root / ".student" / "notifications.json"
        notifications.unlink()
        with self.assertRaisesRegex(ScholarFSError, "required file is missing"):
            add_deadline(
                self.root,
                "Must retain reminder defaults",
                course="CS-241",
                at=None,
                on="2026-08-31",
            )
        self.assertEqual(load_json(self.root / ".student" / "deadlines.json")["deadlines"], [])

    def test_timed_deadline_uses_calendar_days_but_exact_overdue_state(self) -> None:
        add_deadline(
            self.root,
            "Late-night project",
            course="CS-241",
            at="2026-09-04T23:59:00-05:00",
            on=None,
        )
        just_before = list_deadlines(
            self.root,
            days=0,
            as_of=datetime.fromisoformat("2026-09-04T23:58:59-05:00"),
        )[0]
        self.assertEqual(just_before["days_remaining"], 0)
        self.assertFalse(just_before["overdue"])

        one_second_overdue = list_deadlines(
            self.root,
            days=0,
            as_of=datetime.fromisoformat("2026-09-04T23:59:01-05:00"),
        )[0]
        self.assertEqual(one_second_overdue["days_remaining"], 0)
        self.assertTrue(one_second_overdue["overdue"])

        just_after = list_deadlines(
            self.root,
            days=0,
            as_of=datetime.fromisoformat("2026-09-05T00:00:01-05:00"),
        )[0]
        self.assertEqual(just_after["days_remaining"], -1)
        self.assertTrue(just_after["overdue"])

    def test_date_only_deadline_uses_workspace_timezone(self) -> None:
        add_deadline(self.root, "All-day task", course="CS-241", at=None, on="2026-09-04")
        evening_in_chicago = datetime.fromisoformat("2026-09-05T01:00:00+00:00")
        item = list_deadlines(self.root, days=0, as_of=evening_in_chicago)[0]
        self.assertEqual(item["days_remaining"], 0)
        self.assertFalse(item["overdue"])

    def test_local_timezone_uses_system_rules_for_each_instant(self) -> None:
        workspace_path = self.root / ".student" / "workspace.json"
        workspace = load_json(workspace_path)
        workspace["timezone"] = "local"
        write_json(workspace_path, workspace)
        add_deadline(
            self.root,
            "December boundary",
            course="CS-241",
            at="2026-12-02T05:30:00Z",
            on=None,
            reminders=[],
        )

        winter_zone = timezone(timedelta(hours=-6))

        def convert_with_winter_rules(moment: datetime) -> datetime:
            return moment.astimezone(winter_zone)

        with patch("scholarfs.deadlines._system_local", side_effect=convert_with_winter_rules) as converter:
            item = list_deadlines(
                self.root,
                days=0,
                as_of=datetime.fromisoformat("2026-12-01T23:30:00+00:00"),
            )[0]
        self.assertEqual(item["days_remaining"], 0)
        self.assertGreaterEqual(converter.call_count, 2)

    def test_mutation_refuses_unknown_schema_version(self) -> None:
        path = self.root / ".student" / "deadlines.json"
        data = load_json(path)
        for invalid_version in (999, True):
            with self.subTest(invalid_version=invalid_version):
                data["schema_version"] = invalid_version
                write_json(path, data)
                with self.assertRaisesRegex(ScholarFSError, "will not migrate it silently"):
                    add_deadline(self.root, "Blocked", course="CS-241", at=None, on="2026-09-04")
                self.assertEqual(load_json(path)["deadlines"], [])
