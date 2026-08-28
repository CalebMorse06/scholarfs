from __future__ import annotations

import json
import os
import subprocess
import unittest

from scholarfs.context import build_context
from scholarfs.utils import ScholarFSError
from scholarfs.validation import validate_workspace
from scholarfs.workspace import add_file, init_workspace

from tests.helpers import WorkspaceFixture


class SymlinkBoundaryTests(WorkspaceFixture, unittest.TestCase):
    def _symlink_or_skip(self, source, destination, *, directory: bool = False) -> None:
        try:
            os.symlink(source, destination, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")

    def _junction_or_skip(self, source, destination) -> None:
        if os.name != "nt":
            self.skipTest("directory junctions are Windows-specific")
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(destination), str(source)],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            self.skipTest(f"junction creation is unavailable: {result.stderr or result.stdout}")

    def test_context_refuses_symlinked_canonical_json(self) -> None:
        outside = self.root.parent / "outside-workspace.json"
        outside.write_text(json.dumps({"schema_version": 1, "secret": "DO-NOT-EMIT"}), encoding="utf-8")
        marker = self.root / ".student" / "workspace.json"
        marker.unlink()
        self._symlink_or_skip(outside, marker)
        with self.assertRaises(ScholarFSError):
            build_context(self.root)

    def test_file_add_refuses_symlinked_source_and_destination(self) -> None:
        real_source = self.root.parent / "source.txt"
        real_source.write_text("safe source", encoding="utf-8")
        linked_source = self.root.parent / "linked-source.txt"
        self._symlink_or_skip(real_source, linked_source)
        with self.assertRaises(ScholarFSError):
            add_file(self.root, linked_source, course=None, kind="inbox")

        inbox = self.root / "inbox"
        (inbox / "README.md").unlink()
        inbox.rmdir()
        outside_dir = self.root.parent / "outside-destination"
        outside_dir.mkdir()
        self._symlink_or_skip(outside_dir, inbox, directory=True)
        with self.assertRaises(ScholarFSError):
            add_file(self.root, real_source, course=None, kind="inbox")

    def test_init_merge_refuses_junction_before_writing_outside_workspace(self) -> None:
        target = self.root.parent / "junction-semester"
        target.mkdir()
        outside = self.root.parent / "junction-scaffold-target"
        outside.mkdir()
        self._junction_or_skip(outside, target / ".student")

        with self.assertRaisesRegex(ScholarFSError, "reparse points"):
            init_workspace(target, merge=True)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(list(target.iterdir()), [target / ".student"])

    def test_validation_does_not_traverse_junctions(self) -> None:
        outside = self.root.parent / "junction-validation-target"
        outside.mkdir()
        (outside / "credentials.pem").write_text("DO-NOT-INSPECT", encoding="utf-8")
        junction = self.root / "inbox" / "linked-outside"
        self._junction_or_skip(outside, junction)

        report = validate_workspace(self.root)
        self.assertTrue(any("reparse point" in warning for warning in report.warnings), report.to_dict())
        self.assertFalse(any("credentials.pem" in warning for warning in report.warnings), report.to_dict())
