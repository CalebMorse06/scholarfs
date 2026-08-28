from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import unquote


REPOSITORY = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


class DocumentationTests(unittest.TestCase):
    def test_all_local_markdown_links_resolve(self) -> None:
        broken: list[str] = []
        for document in REPOSITORY.rglob("*.md"):
            if any(part in {".venv", "build", "dist"} for part in document.parts):
                continue
            text = document.read_text(encoding="utf-8")
            for raw_target in LINK_RE.findall(text):
                target = raw_target.strip().strip("<>").split("#", 1)[0]
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (document.parent / unquote(target)).resolve()
                if not resolved.exists():
                    broken.append(f"{document.relative_to(REPOSITORY)} -> {raw_target}")
        self.assertEqual(broken, [], "broken local Markdown links:\n" + "\n".join(broken))

