from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scholarfs.utils import ScholarFSError, find_workspace, normalize_course_code
from scholarfs.workspace import add_course, add_file, init_workspace, list_courses

from tests.helpers import WorkspaceFixture


class InitTests(unittest.TestCase):
    def test_init_creates_expected_contract_and_merge_never_overwrites(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "semester"
            created, skipped = init_workspace(root, name="Semester", term="Fall 2026")
            self.assertGreaterEqual(len(created), 14)
            self.assertEqual(skipped, [])
            self.assertTrue((root / ".student" / "workspace.json").is_file())
            self.assertTrue((root / "AGENTS.md").is_file())

            sentinel = "student-owned text\n"
            (root / "README.md").write_text(sentinel, encoding="utf-8")
            _, skipped = init_workspace(root, name="Different", term="Spring 2027", merge=True)
            self.assertIn(root / "README.md", skipped)
            self.assertEqual((root / "README.md").read_text(encoding="utf-8"), sentinel)

    def test_init_refuses_nonempty_directory_without_merge(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaises(ScholarFSError):
                init_workspace(root)

    def test_init_rejects_invalid_timezone(self) -> None:
        with TemporaryDirectory() as temporary:
            for value in ("Mars/Olympus", "../Etc/UTC"):
                with self.subTest(value=value), self.assertRaisesRegex(ScholarFSError, "valid IANA timezone"):
                    init_workspace(Path(temporary) / value.replace("/", "-"), timezone_name=value)

    def test_explicit_workspace_path_overrides_environment(self) -> None:
        with TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            init_workspace(first)
            init_workspace(second)
            with patch.dict("os.environ", {"SCHOLARFS_WORKSPACE": str(first)}):
                self.assertEqual(find_workspace(second), second.resolve())


class CourseTests(WorkspaceFixture, unittest.TestCase):
    def test_add_course_creates_human_files_and_machine_index(self) -> None:
        item = add_course(self.root, "cs-241", title="Systems Programming", credits=4)
        self.assertEqual(item["code"], "CS-241")
        self.assertTrue((self.root / "courses" / "CS-241" / "COURSE.md").is_file())
        self.assertTrue((self.root / "courses" / "CS-241" / "assignments" / "README.md").is_file())
        self.assertEqual([course["code"] for course in list_courses(self.root)], ["CS-241"])
        with self.assertRaises(ScholarFSError):
            add_course(self.root, "CS-241")

    def test_unsafe_and_reserved_course_codes_are_rejected(self) -> None:
        for value in ("../CS-241", "CS/241", "CS 241", "CS.", "CON", "CON.txt", "COM1.LOG", ""):
            with self.subTest(value=value), self.assertRaises(ScholarFSError):
                normalize_course_code(value)

    def test_file_capture_rejects_nonportable_names_and_ignores_audit_log(self) -> None:
        add_course(self.root, "CS-241")
        source = self.root.parent / "source.txt"
        source.write_text("fixture", encoding="utf-8")
        for value in ("../escape.txt", "folder\\escape.txt", "CON.txt", "bad:name.txt", "trailing. "):
            with self.subTest(value=value), self.assertRaises(ScholarFSError):
                add_file(self.root, source, course="CS-241", kind="resource", name=value)
        self.assertIn(".student/import-log.jsonl", (self.root / ".gitignore").read_text(encoding="utf-8"))
