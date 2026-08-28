from __future__ import annotations

import unittest

from scholarfs.calendar import build_ics
from scholarfs.context import build_context, write_context
from scholarfs.deadlines import add_deadline, deadlines_path, load_deadlines, set_deadline_status
from scholarfs.utils import ScholarFSError, load_workspace_json, write_json
from scholarfs.workspace import add_course

from tests.helpers import WorkspaceFixture


class ContextAndCalendarTests(WorkspaceFixture, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        add_course(self.root, "CS-241", title="Systems Programming")
        add_course(self.root, "STAT-210", title="Applied Statistics")
        self.timed = add_deadline(
            self.root,
            "Project",
            course="CS-241",
            at="2026-09-03T23:59:00-05:00",
            on=None,
            reminders=[120],
        )
        self.all_day = add_deadline(
            self.root,
            "Homework",
            course="STAT-210",
            at=None,
            on="2026-08-31",
            reminders=[1440],
        )
        deadlines = load_deadlines(self.root)
        deadlines["deadlines"][0]["notes"] = "PRIVATE CALENDAR NOTE"
        deadlines["deadlines"][0]["url"] = "https://example.edu/tasks;view?ids=1,2"
        write_json(deadlines_path(self.root), deadlines)

    def test_context_is_deterministic_scoped_and_private_by_default(self) -> None:
        private_file = self.root / ".student" / "private" / "profile.md"
        private_file.write_text("SECRET-FICTIONAL-CONTEXT", encoding="utf-8")
        first = build_context(self.root, course="CS-241")
        second = build_context(self.root, course="CS-241")
        self.assertEqual(first, second)
        self.assertIn("Systems Programming", first)
        self.assertNotIn("Applied Statistics", first)
        self.assertNotIn("SECRET-FICTIONAL-CONTEXT", first)
        explicit = build_context(self.root, course="CS-241", include_private=True)
        self.assertIn("SECRET-FICTIONAL-CONTEXT", explicit)

        output = write_context(self.root, self.root / ".student" / "generated" / "cs-241.md", first)
        self.assertEqual(output.read_text(encoding="utf-8"), first)
        with self.assertRaises(ScholarFSError):
            write_context(self.root, output, first)
        with self.assertRaises(ScholarFSError):
            write_context(self.root, self.root.parent / "outside.md", first)

    def test_context_requires_all_allowlisted_workspace_files(self) -> None:
        (self.root / "AGENTS.md").unlink()
        with self.assertRaisesRegex(ScholarFSError, "required context file.*AGENTS.md"):
            build_context(self.root, course="CS-241")

    def test_calendar_has_timed_all_day_uid_and_alarms(self) -> None:
        calendar = build_ics(self.root)
        self.assertIn(f"UID:{self.timed['id']}@scholarfs.local", calendar)
        self.assertIn("DTSTART:20260904T045900Z", calendar)
        self.assertIn("DTSTART;VALUE=DATE:20260831", calendar)
        self.assertIn("DTEND;VALUE=DATE:20260901", calendar)
        self.assertIn("TRIGGER:-PT120M", calendar)
        self.assertIn("TRIGGER;RELATED=END:-PT1440M", calendar)
        self.assertIn("URL:https://example.edu/tasks;view?ids=1,2", calendar)
        self.assertNotIn("URL:https://example.edu/tasks\\;view?ids=1\\,2", calendar)
        self.assertNotIn("PRIVATE CALENDAR NOTE", calendar)
        self.assertIn("PRIVATE CALENDAR NOTE", build_ics(self.root, include_notes=True))
        self.assertTrue(calendar.endswith("\r\n"))

    def test_calendar_completed_default_is_configurable_and_overridable(self) -> None:
        completed = add_deadline(
            self.root,
            "Finished work",
            course="CS-241",
            at=None,
            on="2026-08-30",
        )
        set_deadline_status(self.root, completed["id"], "completed")
        self.assertNotIn(completed["id"], build_ics(self.root))

        notifications_path = self.root / ".student" / "notifications.json"
        notifications = load_workspace_json(self.root, ".student/notifications.json")
        notifications["calendar"]["include_completed"] = True
        write_json(notifications_path, notifications)
        self.assertIn(completed["id"], build_ics(self.root))
        self.assertNotIn(completed["id"], build_ics(self.root, include_completed=False))

    def test_calendar_rejects_boolean_reminder_from_corrupt_json(self) -> None:
        deadlines = load_deadlines(self.root)
        deadlines["deadlines"][0]["reminders_minutes"] = [True]
        write_json(deadlines_path(self.root), deadlines)
        with self.assertRaisesRegex(ScholarFSError, "invalid reminder"):
            build_ics(self.root)
