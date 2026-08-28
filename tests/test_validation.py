from __future__ import annotations

import copy
import json
import os
import unittest
import uuid
from collections.abc import Callable
from typing import Any

from scholarfs.deadlines import add_deadline
from scholarfs.utils import load_json
from scholarfs.validation import validate_workspace
from scholarfs.workspace import add_course

from tests.helpers import WorkspaceFixture


Mutation = Callable[[dict[str, Any]], None]


class ValidationSchemaConformanceTests(WorkspaceFixture, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        add_course(
            self.root,
            "CS-241",
            title="Systems Programming",
            instructor="Dr. Rivera",
            credits=4,
        )
        add_deadline(
            self.root,
            "Memory allocator lab",
            course="CS-241",
            at="2026-10-05T23:59:00-05:00",
            on=None,
            kind="lab",
            priority="high",
            weight_percent=12.5,
            estimated_minutes=180,
            reminders=[2880, 120],
            tags=["malloc", "lab"],
            url="https://lms.example.edu/courses/cs-241/labs/3",
        )
        self._paths = {
            "workspace": ".student/workspace.json",
            "courses": ".student/courses.json",
            "deadlines": ".student/deadlines.json",
            "notifications": ".student/notifications.json",
        }
        self._baseline = {
            name: load_json(self.root / relative)
            for name, relative in self._paths.items()
        }

    def _assert_invalid(self, document: str, mutation: Mutation, expected: str) -> None:
        relative = self._paths[document]
        candidate = copy.deepcopy(self._baseline[document])
        mutation(candidate)
        self._write_json(self.root / relative, candidate)
        try:
            report = validate_workspace(self.root)
            self.assertFalse(report.ok, report.to_dict())
            self.assertTrue(
                any(expected in error for error in report.errors),
                f"expected {expected!r} in {report.errors!r}",
            )
        finally:
            self._write_json(self.root / relative, self._baseline[document])

    @staticmethod
    def _write_json(path: Any, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def test_generated_workspace_is_valid(self) -> None:
        report = validate_workspace(self.root)
        self.assertEqual(report.errors, [])

    def test_workspace_contract_rejects_schema_drift(self) -> None:
        cases: list[tuple[str, Mutation, str]] = [
            ("root extra", lambda data: data.__setitem__("surprise", True), "unsupported fields: surprise"),
            ("missing field", lambda data: data.pop("term"), "missing required fields: term"),
            ("boolean version", lambda data: data.__setitem__("schema_version", True), "schema_version"),
            ("future version", lambda data: data.__setitem__("schema_version", 2), "schema_version"),
            ("name type", lambda data: data.__setitem__("name", 7), "workspace.name must be a string"),
            ("name empty", lambda data: data.__setitem__("name", ""), "at least 1"),
            ("name blank", lambda data: data.__setitem__("name", "   "), "must not be blank"),
            ("name long", lambda data: data.__setitem__("name", "n" * 201), "may not exceed 200"),
            ("term type", lambda data: data.__setitem__("term", []), "workspace.term must be a string"),
            ("term long", lambda data: data.__setitem__("term", "t" * 101), "may not exceed 100"),
            ("timezone empty", lambda data: data.__setitem__("timezone", ""), "at least 1"),
            ("timezone unknown", lambda data: data.__setitem__("timezone", "Mars/Olympus"), "valid IANA timezone"),
            ("timezone path", lambda data: data.__setitem__("timezone", "../Etc/UTC"), "valid IANA timezone"),
            ("timezone long", lambda data: data.__setitem__("timezone", "z" * 101), "may not exceed 100"),
            ("timestamp type", lambda data: data.__setitem__("created_at", 0), "timestamp string"),
            (
                "timestamp format",
                lambda data: data.__setitem__("created_at", "2026-08-28T12:00:00"),
                "RFC 3339",
            ),
            (
                "timestamp space separator",
                lambda data: data.__setitem__("created_at", "2026-08-28 12:00:00Z"),
                "RFC 3339",
            ),
            ("privacy type", lambda data: data.__setitem__("privacy", []), "privacy must be an object"),
            (
                "privacy missing",
                lambda data: data["privacy"].pop("private_context_included_by_default"),
                "missing required fields: private_context_included_by_default",
            ),
            (
                "privacy extra",
                lambda data: data["privacy"].__setitem__("telemetry", True),
                "unsupported fields: telemetry",
            ),
            (
                "public default",
                lambda data: data["privacy"].__setitem__("default_repository_visibility", "public"),
                "must be private",
            ),
            (
                "private context default",
                lambda data: data["privacy"].__setitem__("private_context_included_by_default", True),
                "must be false",
            ),
        ]
        for name, mutation, expected in cases:
            with self.subTest(name=name):
                self._assert_invalid("workspace", mutation, expected)

    def test_commented_or_negated_privacy_rules_do_not_satisfy_validation(self) -> None:
        gitignore = self.root / ".gitignore"
        gitignore.write_text(
            ".student/private/*\n!.student/private/*\n!.student/connector-state/*\n# .student/backups/\n# .env\n",
            encoding="utf-8",
        )
        report = validate_workspace(self.root)
        self.assertTrue(any(".student/private/*" in warning for warning in report.warnings), report.to_dict())
        self.assertTrue(any(".student/connector-state/*" in warning for warning in report.warnings), report.to_dict())

    def test_required_workspace_paths_must_have_expected_types(self) -> None:
        gitignore = self.root / ".gitignore"
        gitignore.unlink()
        gitignore.mkdir()
        report = validate_workspace(self.root)
        self.assertFalse(report.ok, report.to_dict())
        self.assertTrue(
            any("regular non-symbolic-link file: .gitignore" in error for error in report.errors),
            report.to_dict(),
        )

        courses = self.root / "courses"
        moved_courses = self.root / "courses-original"
        courses.rename(moved_courses)
        courses.write_text("not a directory\n", encoding="utf-8")
        report = validate_workspace(self.root)
        self.assertFalse(report.ok, report.to_dict())
        self.assertTrue(
            any("non-symbolic-link directory: courses" in error for error in report.errors),
            report.to_dict(),
        )

    def test_canonical_json_symlink_is_rejected_without_being_read(self) -> None:
        outside = self.root.parent / "outside-workspace.json"
        self._write_json(outside, {"schema_version": 1, "secret": "must-not-be-read"})
        marker = self.root / self._paths["workspace"]
        marker.unlink()
        try:
            os.symlink(outside, marker)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")

        report = validate_workspace(self.root)
        self.assertTrue(
            any("symbolic links" in error and self._paths["workspace"] in error for error in report.errors),
            report.to_dict(),
        )
        self.assertFalse(any("secret" in error for error in report.errors), report.to_dict())

    def test_course_contract_rejects_schema_drift(self) -> None:
        cases: list[tuple[str, Mutation, str]] = [
            ("root extra", lambda data: data.__setitem__("page", 1), "unsupported fields: page"),
            ("missing root", lambda data: data.pop("courses"), "missing required fields: courses"),
            ("courses type", lambda data: data.__setitem__("courses", {}), "courses must be an array"),
            ("item type", lambda data: data.__setitem__("courses", ["CS-241"]), "courses[0] must be an object"),
            (
                "item extra",
                lambda data: data["courses"][0].__setitem__("room", "201"),
                "unsupported fields: room",
            ),
            ("item missing", lambda data: data["courses"][0].pop("title"), "missing required fields: title"),
            ("code type", lambda data: data["courses"][0].__setitem__("code", 241), ".code must be a string"),
            (
                "code lowercase",
                lambda data: data["courses"][0].__setitem__("code", "cs-241"),
                "normalized uppercase",
            ),
            (
                "code pattern",
                lambda data: data["courses"][0].__setitem__("code", "CS/241"),
                ".code:",
            ),
            ("title type", lambda data: data["courses"][0].__setitem__("title", False), ".title must be a string"),
            ("title empty", lambda data: data["courses"][0].__setitem__("title", ""), "at least 1"),
            ("title long", lambda data: data["courses"][0].__setitem__("title", "x" * 301), "may not exceed 300"),
            (
                "instructor type",
                lambda data: data["courses"][0].__setitem__("instructor", 123),
                ".instructor must be null or a string",
            ),
            (
                "instructor long",
                lambda data: data["courses"][0].__setitem__("instructor", "i" * 201),
                "up to 200",
            ),
            (
                "credits boolean",
                lambda data: data["courses"][0].__setitem__("credits", True),
                ".credits must be null or a finite number",
            ),
            (
                "credits below minimum",
                lambda data: data["courses"][0].__setitem__("credits", -0.5),
                "between 0 and 30",
            ),
            (
                "credits above maximum",
                lambda data: data["courses"][0].__setitem__("credits", 30.5),
                "between 0 and 30",
            ),
            ("term type", lambda data: data["courses"][0].__setitem__("term", []), ".term must be null or a string"),
            ("term long", lambda data: data["courses"][0].__setitem__("term", "t" * 101), "up to 100"),
            ("source type", lambda data: data["courses"][0].__setitem__("source", "manual"), ".source must be an object"),
            (
                "source extra",
                lambda data: data["courses"][0]["source"].__setitem__("external_id", "1"),
                "unsupported fields: external_id",
            ),
            (
                "source enum",
                lambda data: data["courses"][0]["source"].__setitem__("type", "connector"),
                ".source.type must be manual",
            ),
            (
                "created timestamp",
                lambda data: data["courses"][0].__setitem__("created_at", "yesterday"),
                "RFC 3339",
            ),
            (
                "duplicate code",
                lambda data: data["courses"].append(copy.deepcopy(data["courses"][0])),
                "duplicate course code",
            ),
        ]
        for name, mutation, expected in cases:
            with self.subTest(name=name):
                self._assert_invalid("courses", mutation, expected)

    def test_deadline_contract_rejects_schema_drift(self) -> None:
        valid_connector = {
            "type": "connector",
            "connector": "example-lms",
            "connector_version": "1.0.0",
            "external_id": "assignment-123",
            "observed_at": "2026-08-28T12:00:00Z",
        }

        def connector_source(data: dict[str, Any]) -> dict[str, Any]:
            data["deadlines"][0]["source"] = copy.deepcopy(valid_connector)
            return data["deadlines"][0]["source"]

        def duplicate_deadline(data: dict[str, Any]) -> None:
            data["deadlines"].append(copy.deepcopy(data["deadlines"][0]))

        def duplicate_connector_source(data: dict[str, Any]) -> None:
            connector_source(data)
            duplicate = copy.deepcopy(data["deadlines"][0])
            duplicate["id"] = str(uuid.uuid4())
            data["deadlines"].append(duplicate)

        cases: list[tuple[str, Mutation, str]] = [
            ("root extra", lambda data: data.__setitem__("cursor", None), "unsupported fields: cursor"),
            ("missing root", lambda data: data.pop("deadlines"), "missing required fields: deadlines"),
            ("array type", lambda data: data.__setitem__("deadlines", {}), "deadlines must be an array"),
            ("item type", lambda data: data.__setitem__("deadlines", [None]), "deadlines[0] must be an object"),
            (
                "item extra",
                lambda data: data["deadlines"][0].__setitem__("color", "blue"),
                "unsupported fields: color",
            ),
            ("item missing", lambda data: data["deadlines"][0].pop("due"), "missing required fields: due"),
            ("id type", lambda data: data["deadlines"][0].__setitem__("id", 1), ".id must be a UUID"),
            ("id format", lambda data: data["deadlines"][0].__setitem__("id", "not-a-uuid"), ".id must be a UUID"),
            ("duplicate id", duplicate_deadline, "duplicate deadline id"),
            ("course type", lambda data: data["deadlines"][0].__setitem__("course", 241), ".course must be null"),
            (
                "unknown course",
                lambda data: data["deadlines"][0].__setitem__("course", "MATH-999"),
                "known normalized course",
            ),
            ("title type", lambda data: data["deadlines"][0].__setitem__("title", []), ".title must be a string"),
            ("title empty", lambda data: data["deadlines"][0].__setitem__("title", ""), "at least 1"),
            ("title long", lambda data: data["deadlines"][0].__setitem__("title", "t" * 501), "may not exceed 500"),
            ("kind type", lambda data: data["deadlines"][0].__setitem__("kind", []), ".kind is not supported"),
            ("kind enum", lambda data: data["deadlines"][0].__setitem__("kind", "homework"), ".kind is not supported"),
            ("status type", lambda data: data["deadlines"][0].__setitem__("status", []), ".status is not supported"),
            ("status enum", lambda data: data["deadlines"][0].__setitem__("status", "done"), ".status is not supported"),
            ("priority type", lambda data: data["deadlines"][0].__setitem__("priority", {}), ".priority is not supported"),
            ("priority enum", lambda data: data["deadlines"][0].__setitem__("priority", "urgent"), ".priority is not supported"),
            ("due type", lambda data: data["deadlines"][0].__setitem__("due", []), ".due must be an object"),
            ("due empty", lambda data: data["deadlines"][0].__setitem__("due", {}), "exactly one of at or on"),
            (
                "due both",
                lambda data: data["deadlines"][0].__setitem__(
                    "due", {"at": "2026-10-05T23:59:00-05:00", "on": "2026-10-05"}
                ),
                "exactly one of at or on",
            ),
            (
                "due extra",
                lambda data: data["deadlines"][0].__setitem__(
                    "due", {"at": "2026-10-05T23:59:00-05:00", "timezone": "America/Chicago"}
                ),
                "exactly one of at or on",
            ),
            ("due at type", lambda data: data["deadlines"][0].__setitem__("due", {"at": 0}), "timestamp string"),
            (
                "due at format",
                lambda data: data["deadlines"][0].__setitem__("due", {"at": "2026-10-05T23:59:00"}),
                "RFC 3339",
            ),
            ("due on type", lambda data: data["deadlines"][0].__setitem__("due", {"on": 0}), "YYYY-MM-DD string"),
            (
                "due on format",
                lambda data: data["deadlines"][0].__setitem__("due", {"on": "2026-02-30"}),
                "YYYY-MM-DD",
            ),
            (
                "weight boolean",
                lambda data: data["deadlines"][0].__setitem__("weight_percent", True),
                "finite number between 0 and 100",
            ),
            (
                "weight below minimum",
                lambda data: data["deadlines"][0].__setitem__("weight_percent", -0.1),
                "between 0 and 100",
            ),
            (
                "weight above maximum",
                lambda data: data["deadlines"][0].__setitem__("weight_percent", 100.1),
                "between 0 and 100",
            ),
            (
                "estimate boolean",
                lambda data: data["deadlines"][0].__setitem__("estimated_minutes", True),
                "positive integer",
            ),
            (
                "estimate minimum",
                lambda data: data["deadlines"][0].__setitem__("estimated_minutes", 0),
                "positive integer",
            ),
            (
                "estimate number type",
                lambda data: data["deadlines"][0].__setitem__("estimated_minutes", 1.5),
                "positive integer",
            ),
            ("source type", lambda data: data["deadlines"][0].__setitem__("source", []), ".source must be an object"),
            (
                "manual source extra",
                lambda data: data["deadlines"][0]["source"].__setitem__("external_id", "123"),
                "unsupported fields: external_id",
            ),
            (
                "source enum",
                lambda data: data["deadlines"][0]["source"].__setitem__("type", "import"),
                ".source.type must be manual or connector",
            ),
            (
                "connector missing",
                lambda data: connector_source(data).pop("external_id"),
                "missing required fields: external_id",
            ),
            (
                "connector extra",
                lambda data: connector_source(data).__setitem__("token", "secret"),
                "unsupported fields: token",
            ),
            (
                "connector id pattern",
                lambda data: connector_source(data).__setitem__("connector", "Canvas LMS"),
                "lowercase letters, numbers, and hyphens",
            ),
            (
                "connector version empty",
                lambda data: connector_source(data).__setitem__("connector_version", ""),
                "at least 1",
            ),
            (
                "external id empty",
                lambda data: connector_source(data).__setitem__("external_id", ""),
                "at least 1",
            ),
            (
                "external id long",
                lambda data: connector_source(data).__setitem__("external_id", "x" * 257),
                "may not exceed 256",
            ),
            (
                "observed timestamp",
                lambda data: connector_source(data).__setitem__("observed_at", "2026-08-28"),
                "RFC 3339",
            ),
            ("duplicate source key", duplicate_connector_source, "duplicate connector source key"),
            ("url type", lambda data: data["deadlines"][0].__setitem__("url", 123), ".url must be null"),
            ("url scheme", lambda data: data["deadlines"][0].__setitem__("url", "ftp://example.edu/a"), ".url must be null"),
            (
                "url whitespace",
                lambda data: data["deadlines"][0].__setitem__("url", "https://example.edu/a b"),
                ".url must be null",
            ),
            (
                "url malformed ipv6",
                lambda data: data["deadlines"][0].__setitem__("url", "http://[::1"),
                ".url must be null",
            ),
            (
                "reminders type",
                lambda data: data["deadlines"][0].__setitem__("reminders_minutes", {}),
                "non-negative integers",
            ),
            (
                "reminders boolean",
                lambda data: data["deadlines"][0].__setitem__("reminders_minutes", [True]),
                "non-negative integers",
            ),
            (
                "reminders minimum",
                lambda data: data["deadlines"][0].__setitem__("reminders_minutes", [-1]),
                "non-negative integers",
            ),
            (
                "reminders unique",
                lambda data: data["deadlines"][0].__setitem__("reminders_minutes", [120, 120]),
                "must be unique",
            ),
            ("tags type", lambda data: data["deadlines"][0].__setitem__("tags", {}), "strings of 1-100"),
            ("tag item type", lambda data: data["deadlines"][0].__setitem__("tags", [1]), "strings of 1-100"),
            ("tag empty", lambda data: data["deadlines"][0].__setitem__("tags", [""]), "strings of 1-100"),
            ("tag long", lambda data: data["deadlines"][0].__setitem__("tags", ["t" * 101]), "strings of 1-100"),
            ("tags unique", lambda data: data["deadlines"][0].__setitem__("tags", ["lab", "lab"]), "must be unique"),
            ("notes type", lambda data: data["deadlines"][0].__setitem__("notes", None), ".notes must be a string"),
            ("notes long", lambda data: data["deadlines"][0].__setitem__("notes", "n" * 10001), "up to 10000"),
            (
                "completed timestamp while pending",
                lambda data: data["deadlines"][0].__setitem__("completed_at", "2026-08-28T12:00:00Z"),
                "present only when status is completed",
            ),
            (
                "completed status without timestamp",
                lambda data: data["deadlines"][0].__setitem__("status", "completed"),
                "present only when status is completed",
            ),
            (
                "created timestamp",
                lambda data: data["deadlines"][0].__setitem__("created_at", "2026-08-28"),
                "RFC 3339",
            ),
            (
                "updated timestamp",
                lambda data: data["deadlines"][0].__setitem__("updated_at", False),
                "timestamp string",
            ),
        ]
        for name, mutation, expected in cases:
            with self.subTest(name=name):
                self._assert_invalid("deadlines", mutation, expected)

    def test_completed_deadline_and_connector_source_are_valid(self) -> None:
        data = copy.deepcopy(self._baseline["deadlines"])
        item = data["deadlines"][0]
        item["status"] = "completed"
        item["completed_at"] = "2026-08-28T12:00:00Z"
        item["source"] = {
            "type": "connector",
            "connector": "example-lms",
            "connector_version": "1.0.0",
            "external_id": "assignment-123",
            "observed_at": "2026-08-28T12:00:00Z",
        }
        self._write_json(self.root / self._paths["deadlines"], data)
        report = validate_workspace(self.root)
        self.assertEqual(report.errors, [])

    def test_notification_contract_rejects_schema_drift(self) -> None:
        cases: list[tuple[str, Mutation, str]] = [
            ("root extra", lambda data: data.__setitem__("email", {}), "unsupported fields: email"),
            ("missing calendar", lambda data: data.pop("calendar"), "missing required fields: calendar"),
            ("calendar type", lambda data: data.__setitem__("calendar", []), "calendar must be an object"),
            (
                "calendar extra",
                lambda data: data["calendar"].__setitem__("enabled", True),
                "unsupported fields: enabled",
            ),
            (
                "calendar missing",
                lambda data: data["calendar"].pop("include_completed"),
                "missing required fields: include_completed",
            ),
            (
                "reminders type",
                lambda data: data["calendar"].__setitem__("default_reminders_minutes", "120"),
                "non-negative integers",
            ),
            (
                "reminders boolean",
                lambda data: data["calendar"].__setitem__("default_reminders_minutes", [True]),
                "non-negative integers",
            ),
            (
                "reminders minimum",
                lambda data: data["calendar"].__setitem__("default_reminders_minutes", [-1]),
                "non-negative integers",
            ),
            (
                "reminders unique",
                lambda data: data["calendar"].__setitem__("default_reminders_minutes", [120, 120]),
                "must be unique",
            ),
            (
                "include completed string",
                lambda data: data["calendar"].__setitem__("include_completed", "false"),
                "must be a boolean",
            ),
            (
                "include completed integer",
                lambda data: data["calendar"].__setitem__("include_completed", 0),
                "must be a boolean",
            ),
        ]
        for name, mutation, expected in cases:
            with self.subTest(name=name):
                self._assert_invalid("notifications", mutation, expected)


if __name__ == "__main__":
    unittest.main()
