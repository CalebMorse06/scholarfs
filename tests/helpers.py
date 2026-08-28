from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from scholarfs.workspace import init_workspace


class WorkspaceFixture:
    def setUp(self) -> None:
        super().setUp()
        self._temporary_directory = TemporaryDirectory()
        self.root = Path(self._temporary_directory.name) / "semester"
        init_workspace(
            self.root,
            name="Test semester",
            term="Fall 2026",
            timezone_name="America/Chicago",
        )

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()
        super().tearDown()

