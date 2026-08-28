from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from datetime import date
from importlib.resources import files
from pathlib import Path
from string import Template
from typing import Any

from .utils import (
    SPEC_VERSION,
    ScholarFSError,
    WINDOWS_RESERVED_NAMES,
    iso_now,
    load_json,
    load_workspace_json,
    normalize_course_code,
    require_safe_workspace_path,
    validate_timezone_name,
    write_json,
)


WORKSPACE_MARKER = Path(".student/workspace.json")


def _template(name: str, **values: object) -> str:
    source = files("scholarfs").joinpath("templates", name).read_text(encoding="utf-8")
    return Template(source).safe_substitute({key: str(value) for key, value in values.items()})


def _write_new(root: Path, path: Path, content: str, *, merge: bool, created: list[Path], skipped: list[Path]) -> None:
    path = require_safe_workspace_path(root, path, label="workspace scaffold path")
    if path.exists():
        if merge:
            skipped.append(path)
            return
        raise ScholarFSError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")
    created.append(path)


def init_workspace(
    target: Path,
    *,
    name: str | None = None,
    term: str = "My semester",
    timezone_name: str = "local",
    merge: bool = False,
) -> tuple[list[Path], list[Path]]:
    target = target.expanduser().resolve()
    workspace_name = (name or target.name or "My semester").strip()
    if not workspace_name:
        raise ScholarFSError("workspace name may not be empty")
    if len(workspace_name) > 200:
        raise ScholarFSError("workspace name may not exceed 200 characters")
    if not term.strip():
        raise ScholarFSError("term may not be empty")
    if len(term.strip()) > 100:
        raise ScholarFSError("term may not exceed 100 characters")
    if not timezone_name.strip():
        raise ScholarFSError("timezone may not be empty")
    if len(timezone_name.strip()) > 100:
        raise ScholarFSError("timezone may not exceed 100 characters")
    normalized_timezone = validate_timezone_name(timezone_name, field="--timezone")

    if target.exists() and not target.is_dir():
        raise ScholarFSError(f"target exists and is not a directory: {target}")
    if target.exists() and any(target.iterdir()) and not merge:
        raise ScholarFSError(
            f"target is not empty: {target}; choose an empty directory or pass --merge "
            "to add only missing ScholarFS files"
        )
    target.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    skipped: list[Path] = []
    now = iso_now()
    workspace = {
        "schema_version": SPEC_VERSION,
        "name": workspace_name,
        "term": term.strip(),
        "timezone": normalized_timezone,
        "created_at": now,
        "privacy": {
            "default_repository_visibility": "private",
            "private_context_included_by_default": False,
        },
    }
    courses = {"schema_version": SPEC_VERSION, "courses": []}
    deadlines = {"schema_version": SPEC_VERSION, "deadlines": []}
    notifications = {
        "schema_version": SPEC_VERSION,
        "calendar": {
            "default_reminders_minutes": [2880, 120],
            "include_completed": False,
        },
    }

    text_files = {
        "README.md": _template("workspace-readme.md.tpl", workspace_name=workspace_name, term=term.strip()),
        "AGENTS.md": _template("agents.md.tpl"),
        ".gitignore": _template("gitignore.tpl"),
        ".student/memory/semester.md": _template("semester-memory.md.tpl", today=date.today().isoformat()),
        ".student/private/README.md": _template("private-readme.md.tpl"),
        ".student/private/profile.md": _template("profile.md.tpl"),
        ".student/private/preferences.md": _template("preferences.md.tpl"),
        ".student/connector-state/README.md": _template("connectors-readme.md.tpl"),
        "courses/README.md": _template("courses-readme.md.tpl"),
        "inbox/README.md": _template("inbox-readme.md.tpl"),
    }
    json_files = {
        ".student/workspace.json": workspace,
        ".student/courses.json": courses,
        ".student/deadlines.json": deadlines,
        ".student/notifications.json": notifications,
    }

    for relative in (*text_files, *json_files):
        require_safe_workspace_path(target, target / relative, label="workspace scaffold path")

    for relative, content in text_files.items():
        _write_new(target, target / relative, content, merge=merge, created=created, skipped=skipped)
    for relative, data in json_files.items():
        path = require_safe_workspace_path(target, target / relative, label="workspace scaffold path")
        if path.exists():
            if merge:
                skipped.append(path)
                continue
            raise ScholarFSError(f"refusing to overwrite existing file: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, data)
        created.append(path)

    return created, skipped


def load_courses(root: Path) -> dict[str, Any]:
    return load_workspace_json(root, ".student/courses.json")


def course_by_code(root: Path, code: str) -> dict[str, Any] | None:
    normalized = normalize_course_code(code)
    data = load_courses(root)
    courses = data.get("courses", [])
    if not isinstance(courses, list):
        raise ScholarFSError(".student/courses.json has an invalid courses field; run scholarfs validate")
    return next((item for item in courses if isinstance(item, dict) and item.get("code") == normalized), None)


def add_course(
    root: Path,
    code: str,
    *,
    title: str | None = None,
    instructor: str | None = None,
    credits: float | None = None,
) -> dict[str, Any]:
    normalized = normalize_course_code(code)
    title_value = (title or normalized).strip()
    if not title_value:
        raise ScholarFSError("course title may not be empty")
    if len(title_value) > 300:
        raise ScholarFSError("course title may not exceed 300 characters")
    if instructor and len(instructor.strip()) > 200:
        raise ScholarFSError("instructor may not exceed 200 characters")
    if credits is not None and not (0 <= credits <= 30):
        raise ScholarFSError("credits must be between 0 and 30")

    courses_path = root / ".student" / "courses.json"
    data = load_courses(root)
    items = data.get("courses")
    if not isinstance(items, list):
        raise ScholarFSError(".student/courses.json has an invalid courses field; run scholarfs validate")
    if any(isinstance(item, dict) and item.get("code") == normalized for item in items):
        raise ScholarFSError(f"course already exists: {normalized}")

    destination = root / "courses" / normalized
    if destination.exists():
        raise ScholarFSError(f"course directory already exists but is not indexed: {destination}")
    workspace = load_workspace_json(root, ".student/workspace.json")
    record = {
        "code": normalized,
        "title": title_value,
        "instructor": instructor.strip() if instructor else None,
        "credits": credits,
        "term": workspace.get("term"),
        "source": {"type": "manual"},
        "created_at": iso_now(),
    }

    courses_root = root / "courses"
    require_safe_workspace_path(root, courses_root, label="courses directory")
    courses_root.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{normalized}.", dir=courses_root))
    try:
        (temp_dir / "COURSE.md").write_text(
            _template(
                "course.md.tpl",
                code=normalized,
                title=title_value,
                instructor=record["instructor"] or "Not recorded",
                credits=credits if credits is not None else "Not recorded",
                term=workspace.get("term", "Not recorded"),
            ),
            encoding="utf-8",
            newline="\n",
        )
        (temp_dir / "memory.md").write_text(
            _template("course-memory.md.tpl", code=normalized), encoding="utf-8", newline="\n"
        )
        folders = {
            "syllabus": ("Syllabus", "Store your syllabus and policy references here."),
            "assignments": ("Assignments", "Give each assignment its own directory and README.md."),
            "notes": ("Notes", "Keep maintained notes here; use dates or topic names."),
            "lectures": ("Lectures", "Keep lecture materials or references here."),
            "resources": ("Resources", "Keep stable course resources and links here."),
        }
        for folder, (heading, guidance) in folders.items():
            target = temp_dir / folder
            target.mkdir()
            (target / "README.md").write_text(
                _template("folder-readme.md.tpl", heading=heading, guidance=guidance),
                encoding="utf-8",
                newline="\n",
            )
        os.replace(temp_dir, destination)
        items.append(record)
        items.sort(key=lambda item: str(item.get("code", "")) if isinstance(item, dict) else "")
        write_json(courses_path, data)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        if destination.exists() and not any(
            isinstance(item, dict) and item.get("code") == normalized for item in load_courses(root).get("courses", [])
        ):
            shutil.rmtree(destination)
        raise
    return record


def list_courses(root: Path) -> list[dict[str, Any]]:
    data = load_courses(root)
    items = data.get("courses")
    if not isinstance(items, list):
        raise ScholarFSError(".student/courses.json has an invalid courses field; run scholarfs validate")
    return sorted((item for item in items if isinstance(item, dict)), key=lambda item: str(item.get("code", "")))


def add_file(
    root: Path,
    source: Path,
    *,
    course: str | None,
    kind: str,
    name: str | None = None,
) -> tuple[Path, str]:
    load_workspace_json(root, ".student/workspace.json")
    source_input = source.expanduser().absolute()
    if source_input.is_symlink():
        raise ScholarFSError("symbolic-link sources are refused; copy the real file explicitly")
    source = source_input.resolve()
    if not source.is_file():
        raise ScholarFSError(f"source is not a file: {source}")
    output_name = name or source.name
    if (
        not output_name
        or len(output_name) > 255
        or Path(output_name).name != output_name
        or output_name in {".", ".."}
        or "/" in output_name
        or "\\" in output_name
        or ":" in output_name
        or output_name != output_name.rstrip(" .")
        or any(ord(character) < 32 for character in output_name)
    ):
        raise ScholarFSError("--name must be a portable plain filename, not a path")
    if output_name.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES:
        raise ScholarFSError(f"--name {output_name!r} is a reserved Windows filename")

    folder_map = {
        "syllabus": "syllabus/files",
        "assignment": "assignments/imported/files",
        "lecture": "lectures/files",
        "note": "notes/files",
        "resource": "resources/files",
    }
    if kind == "inbox":
        if course:
            raise ScholarFSError("--course cannot be combined with --kind inbox")
        destination_dir = root / "inbox"
    else:
        if kind not in folder_map:
            raise ScholarFSError(f"unsupported file kind: {kind}")
        if not course:
            raise ScholarFSError(f"--course is required for file kind {kind}")
        normalized = normalize_course_code(course)
        if course_by_code(root, normalized) is None:
            raise ScholarFSError(f"unknown course: {normalized}")
        destination_dir = root / "courses" / normalized / Path(folder_map[kind])

    require_safe_workspace_path(root, destination_dir, label="file destination directory")
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / output_name
    require_safe_workspace_path(root, destination, label="file destination")
    if destination.exists():
        raise ScholarFSError(f"destination already exists: {destination}")
    shutil.copy2(source, destination)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    event = {
        "at": iso_now(),
        "action": "copy",
        "source_name": source.name,
        "destination": destination.relative_to(root).as_posix(),
        "sha256": digest,
    }
    log_path = root / ".student" / "import-log.jsonl"
    require_safe_workspace_path(root, log_path, label="import log")
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        import json

        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return destination, digest
