from __future__ import annotations

import math
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .deadlines import KINDS, PRIORITIES, STATUSES, validate_url
from .utils import (
    SPEC_VERSION,
    ScholarFSError,
    has_symlink_component,
    load_json,
    normalize_course_code,
    parse_date,
    parse_rfc3339,
    validate_timezone_name,
)


COURSE_FIELDS = {"code", "title", "instructor", "credits", "term", "source", "created_at"}
DEADLINE_FIELDS = {
    "id",
    "course",
    "title",
    "kind",
    "due",
    "status",
    "priority",
    "weight_percent",
    "estimated_minutes",
    "source",
    "url",
    "reminders_minutes",
    "tags",
    "notes",
    "created_at",
    "updated_at",
    "completed_at",
}
CONNECTOR_SOURCE_FIELDS = {"type", "connector", "connector_version", "external_id", "observed_at"}
CONNECTOR_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@dataclass
class ValidationReport:
    root: Path
    checks: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.errors.append(message)

    def warn(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.warnings.append(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace": str(self.root),
            "ok": self.ok,
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _load(report: ValidationReport, relative: str) -> dict[str, Any] | None:
    path = report.root / relative
    safe_path = not has_symlink_component(report.root, path)
    report.check(safe_path, f"canonical workspace JSON may not use symbolic links: {relative}")
    if not safe_path:
        return None
    report.check(path.is_file(), f"missing required file: {relative}")
    if not path.is_file():
        return None
    try:
        return load_json(path)
    except ScholarFSError as exc:
        report.errors.append(str(exc))
        return None


def _check_keys(report: ValidationReport, value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = sorted(expected - set(value))
    extras = sorted(set(value) - expected)
    report.check(not missing, f"{label} is missing required fields: {', '.join(missing)}")
    report.check(not extras, f"{label} contains unsupported fields: {', '.join(extras)}")


def _check_text(
    report: ValidationReport,
    value: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
    nonblank: bool = False,
) -> bool:
    valid_type = isinstance(value, str)
    report.check(valid_type, f"{label} must be a string")
    if not valid_type:
        return False
    assert isinstance(value, str)
    report.check(len(value) >= minimum, f"{label} must contain at least {minimum} character(s)")
    if maximum is not None:
        report.check(len(value) <= maximum, f"{label} may not exceed {maximum} characters")
    if nonblank:
        report.check(bool(value.strip()), f"{label} must not be blank")
    return True


def _check_timestamp(report: ValidationReport, value: object, label: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str):
        report.check(False, f"{label} must be a timestamp string")
        return
    report.check(bool(RFC3339_RE.fullmatch(value)), f"{label} must be an RFC 3339 date-time")
    if not RFC3339_RE.fullmatch(value):
        return
    normalized = f"{value[:-1]}Z" if value.endswith("z") else value
    try:
        parse_rfc3339(normalized, field=label)
    except ScholarFSError as exc:
        report.check(False, str(exc))


def _check_date(report: ValidationReport, value: object, label: str) -> None:
    if not isinstance(value, str):
        report.check(False, f"{label} must be a YYYY-MM-DD string")
        return
    report.check(bool(DATE_RE.fullmatch(value)), f"{label} must use YYYY-MM-DD")
    if not DATE_RE.fullmatch(value):
        return
    try:
        parse_date(value, field=label)
    except ScholarFSError as exc:
        report.check(False, str(exc))


def _check_schema_version(report: ValidationReport, data: dict[str, Any], relative: str) -> None:
    report.check(
        type(data.get("schema_version")) is int and data.get("schema_version") == SPEC_VERSION,
        f"{relative} schema_version must be integer {SPEC_VERSION}; migrations are never applied silently",
    )


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _check_workspace(report: ValidationReport, workspace: dict[str, Any]) -> None:
    label = ".student/workspace.json"
    _check_keys(report, workspace, {"schema_version", "name", "term", "timezone", "created_at", "privacy"}, label)
    _check_schema_version(report, workspace, label)
    _check_text(report, workspace.get("name"), "workspace.name", minimum=1, maximum=200, nonblank=True)
    _check_text(report, workspace.get("term"), "workspace.term", minimum=1, maximum=100, nonblank=True)
    timezone_value = workspace.get("timezone")
    timezone_is_text = _check_text(
        report,
        timezone_value,
        "workspace.timezone",
        minimum=1,
        maximum=100,
        nonblank=True,
    )
    if timezone_is_text:
        try:
            validate_timezone_name(timezone_value, field="workspace.timezone")
        except ScholarFSError as exc:
            report.check(False, str(exc))
    _check_timestamp(report, workspace.get("created_at"), "workspace.created_at")

    privacy = workspace.get("privacy")
    report.check(isinstance(privacy, dict), "workspace.privacy must be an object")
    if isinstance(privacy, dict):
        _check_keys(
            report,
            privacy,
            {"default_repository_visibility", "private_context_included_by_default"},
            "workspace.privacy",
        )
        report.check(
            privacy.get("default_repository_visibility") == "private"
            and isinstance(privacy.get("default_repository_visibility"), str),
            "workspace.privacy.default_repository_visibility must be private",
        )
        report.check(
            privacy.get("private_context_included_by_default") is False,
            "workspace.privacy.private_context_included_by_default must be false",
        )


def _check_courses(report: ValidationReport, courses_data: dict[str, Any]) -> set[str]:
    label = ".student/courses.json"
    _check_keys(report, courses_data, {"schema_version", "courses"}, label)
    _check_schema_version(report, courses_data, label)
    courses = courses_data.get("courses")
    report.check(isinstance(courses, list), "courses must be an array")
    course_codes: set[str] = set()
    if not isinstance(courses, list):
        return course_codes

    for index, item in enumerate(courses):
        item_label = f"courses[{index}]"
        report.check(isinstance(item, dict), f"{item_label} must be an object")
        if not isinstance(item, dict):
            continue
        _check_keys(report, item, COURSE_FIELDS, item_label)

        code = item.get("code")
        normalized = ""
        if not isinstance(code, str):
            report.check(False, f"{item_label}.code must be a string")
        else:
            try:
                normalized = normalize_course_code(code)
            except ScholarFSError as exc:
                report.check(False, f"{item_label}.code: {exc}")
            report.check(bool(normalized) and normalized == code, f"{item_label}.code must already be normalized uppercase")
        if normalized:
            report.check(normalized not in course_codes, f"duplicate course code: {normalized}")
            course_codes.add(normalized)
            report.check(
                (report.root / "courses" / normalized / "COURSE.md").is_file(),
                f"missing courses/{normalized}/COURSE.md",
            )
            report.check(
                (report.root / "courses" / normalized / "memory.md").is_file(),
                f"missing courses/{normalized}/memory.md",
            )

        _check_text(report, item.get("title"), f"{item_label}.title", minimum=1, maximum=300, nonblank=True)
        instructor = item.get("instructor")
        report.check(
            instructor is None or (isinstance(instructor, str) and len(instructor) <= 200),
            f"{item_label}.instructor must be null or a string up to 200 characters",
        )
        credits = item.get("credits")
        report.check(
            credits is None or (_is_number(credits) and 0 <= credits <= 30),
            f"{item_label}.credits must be null or a finite number between 0 and 30",
        )
        term = item.get("term")
        report.check(
            term is None or (isinstance(term, str) and len(term) <= 100),
            f"{item_label}.term must be null or a string up to 100 characters",
        )
        source = item.get("source")
        report.check(isinstance(source, dict), f"{item_label}.source must be an object")
        if isinstance(source, dict):
            _check_keys(report, source, {"type"}, f"{item_label}.source")
            report.check(source.get("type") == "manual", f"{item_label}.source.type must be manual")
        _check_timestamp(report, item.get("created_at"), f"{item_label}.created_at")
    return course_codes


def _check_deadline_source(
    report: ValidationReport,
    source: object,
    label: str,
    source_keys: set[tuple[str, str]],
) -> None:
    report.check(isinstance(source, dict), f"{label} must be an object")
    if not isinstance(source, dict):
        return
    source_type = source.get("type")
    if source_type == "manual":
        _check_keys(report, source, {"type"}, label)
        return
    if source_type != "connector":
        report.check(False, f"{label}.type must be manual or connector")
        return

    _check_keys(report, source, CONNECTOR_SOURCE_FIELDS, label)
    connector = source.get("connector")
    report.check(
        isinstance(connector, str) and bool(CONNECTOR_ID_RE.fullmatch(connector)),
        f"{label}.connector must use lowercase letters, numbers, and hyphens (1-64 characters)",
    )
    connector_version = source.get("connector_version")
    _check_text(report, connector_version, f"{label}.connector_version", minimum=1)
    external_id = source.get("external_id")
    _check_text(report, external_id, f"{label}.external_id", minimum=1, maximum=256)
    _check_timestamp(report, source.get("observed_at"), f"{label}.observed_at")
    if isinstance(connector, str) and isinstance(external_id, str):
        key = (connector, external_id)
        report.check(key not in source_keys, f"duplicate connector source key: {connector} / {external_id}")
        source_keys.add(key)


def _check_deadlines(report: ValidationReport, deadlines_data: dict[str, Any], course_codes: set[str]) -> None:
    label = ".student/deadlines.json"
    _check_keys(report, deadlines_data, {"schema_version", "deadlines"}, label)
    _check_schema_version(report, deadlines_data, label)
    deadlines = deadlines_data.get("deadlines")
    report.check(isinstance(deadlines, list), "deadlines must be an array")
    if not isinstance(deadlines, list):
        return

    ids: set[str] = set()
    source_keys: set[tuple[str, str]] = set()
    for index, item in enumerate(deadlines):
        item_label = f"deadlines[{index}]"
        report.check(isinstance(item, dict), f"{item_label} must be an object")
        if not isinstance(item, dict):
            continue
        _check_keys(report, item, DEADLINE_FIELDS, item_label)

        deadline_id = item.get("id")
        valid_uuid = isinstance(deadline_id, str) and bool(UUID_RE.fullmatch(deadline_id))
        if valid_uuid:
            try:
                uuid.UUID(deadline_id)
            except ValueError:
                valid_uuid = False
        report.check(valid_uuid, f"{item_label}.id must be a UUID")
        if isinstance(deadline_id, str):
            report.check(deadline_id not in ids, f"duplicate deadline id: {deadline_id}")
            ids.add(deadline_id)

        course = item.get("course")
        report.check(
            course is None or (isinstance(course, str) and course in course_codes),
            f"{item_label}.course must be null or reference a known normalized course: {course}",
        )
        _check_text(report, item.get("title"), f"{item_label}.title", minimum=1, maximum=500, nonblank=True)
        kind = item.get("kind")
        status = item.get("status")
        priority = item.get("priority")
        report.check(isinstance(kind, str) and kind in KINDS, f"{item_label}.kind is not supported")
        report.check(isinstance(status, str) and status in STATUSES, f"{item_label}.status is not supported")
        report.check(
            isinstance(priority, str) and priority in PRIORITIES,
            f"{item_label}.priority is not supported",
        )

        due = item.get("due")
        report.check(isinstance(due, dict), f"{item_label}.due must be an object")
        if isinstance(due, dict):
            report.check(set(due) in ({"at"}, {"on"}), f"{item_label}.due must contain exactly one of at or on")
            if set(due) == {"at"}:
                _check_timestamp(report, due.get("at"), f"{item_label}.due.at")
            elif set(due) == {"on"}:
                _check_date(report, due.get("on"), f"{item_label}.due.on")

        weight = item.get("weight_percent")
        report.check(
            weight is None or (_is_number(weight) and 0 <= weight <= 100),
            f"{item_label}.weight_percent must be null or a finite number between 0 and 100",
        )
        estimate = item.get("estimated_minutes")
        report.check(
            estimate is None or (type(estimate) is int and estimate >= 1),
            f"{item_label}.estimated_minutes must be null or a positive integer",
        )
        _check_deadline_source(report, item.get("source"), f"{item_label}.source", source_keys)

        url = item.get("url")
        url_valid = url is None
        if isinstance(url, str):
            try:
                validate_url(url)
                url_valid = url.startswith(("http://", "https://")) and not any(character.isspace() for character in url)
            except (ScholarFSError, ValueError):
                url_valid = False
        report.check(url_valid, f"{item_label}.url must be null or an absolute HTTP(S) URI")

        reminders = item.get("reminders_minutes")
        reminders_valid = isinstance(reminders, list) and all(type(value) is int and value >= 0 for value in reminders)
        report.check(reminders_valid, f"{item_label}.reminders_minutes must contain non-negative integers")
        if reminders_valid:
            report.check(len(reminders) == len(set(reminders)), f"{item_label}.reminders_minutes must be unique")

        tags = item.get("tags")
        tags_valid = isinstance(tags, list) and all(isinstance(value, str) and 1 <= len(value) <= 100 for value in tags)
        report.check(tags_valid, f"{item_label}.tags must contain strings of 1-100 characters")
        if tags_valid:
            report.check(len(tags) == len(set(tags)), f"{item_label}.tags must be unique")
        notes = item.get("notes")
        report.check(
            isinstance(notes, str) and len(notes) <= 10000,
            f"{item_label}.notes must be a string up to 10000 characters",
        )

        completed_at = item.get("completed_at")
        report.check(
            (status == "completed" and isinstance(completed_at, str))
            or (status != "completed" and completed_at is None),
            f"{item_label}.completed_at must be present only when status is completed",
        )
        if isinstance(completed_at, str):
            _check_timestamp(report, completed_at, f"{item_label}.completed_at")
        _check_timestamp(report, item.get("created_at"), f"{item_label}.created_at")
        _check_timestamp(report, item.get("updated_at"), f"{item_label}.updated_at")


def _check_notifications(report: ValidationReport, notifications: dict[str, Any]) -> None:
    label = ".student/notifications.json"
    _check_keys(report, notifications, {"schema_version", "calendar"}, label)
    _check_schema_version(report, notifications, label)
    calendar = notifications.get("calendar")
    report.check(isinstance(calendar, dict), "notifications.calendar must be an object")
    if not isinstance(calendar, dict):
        return
    _check_keys(report, calendar, {"default_reminders_minutes", "include_completed"}, "notifications.calendar")
    defaults = calendar.get("default_reminders_minutes")
    defaults_valid = isinstance(defaults, list) and all(type(value) is int and value >= 0 for value in defaults)
    report.check(defaults_valid, "notifications.calendar.default_reminders_minutes must contain non-negative integers")
    if defaults_valid:
        report.check(len(defaults) == len(set(defaults)), "notification default reminders must be unique")
    report.check(
        isinstance(calendar.get("include_completed"), bool),
        "notifications.calendar.include_completed must be a boolean",
    )


def validate_workspace(root: Path) -> ValidationReport:
    root = root.resolve()
    report = ValidationReport(root=root)
    workspace = _load(report, ".student/workspace.json")
    courses_data = _load(report, ".student/courses.json")
    deadlines_data = _load(report, ".student/deadlines.json")
    notifications = _load(report, ".student/notifications.json")

    required_files = ["README.md", "AGENTS.md", ".gitignore", ".student/memory/semester.md"]
    required_directories = ["courses", "inbox"]
    for required in required_files:
        path = root / required
        report.check(
            path.is_file() and not has_symlink_component(root, path),
            f"required workspace file must be a regular non-symbolic-link file: {required}",
        )
    for required in required_directories:
        path = root / required
        report.check(
            path.is_dir() and not has_symlink_component(root, path),
            f"required workspace directory must be a non-symbolic-link directory: {required}",
        )

    if workspace is not None:
        _check_workspace(report, workspace)
    course_codes = _check_courses(report, courses_data) if courses_data is not None else set()
    if deadlines_data is not None:
        _check_deadlines(report, deadlines_data, course_codes)
    if notifications is not None:
        _check_notifications(report, notifications)

    gitignore = root / ".gitignore"
    if gitignore.is_file() and not has_symlink_component(root, gitignore):
        ignore_text = gitignore.read_text(encoding="utf-8")
        active_ignore_rules = {
            line
            for raw_line in ignore_text.splitlines()
            if (line := raw_line.strip()) and not line.startswith(("#", "!"))
        }
        negated_ignore_rules = {
            line[1:]
            for raw_line in ignore_text.splitlines()
            if (line := raw_line.strip()).startswith("!") and len(line) > 1
        }
        for expected in (
            ".student/private/*",
            ".student/connector-state/*",
            ".student/backups/",
            ".student/generated/",
            ".student/import-log.jsonl",
            "inbox/*",
            "courses/*/syllabus/files/",
            "courses/*/assignments/*/files/",
            "courses/*/lectures/files/",
            "courses/*/resources/files/",
            ".env",
        ):
            report.warn(
                expected in active_ignore_rules and expected not in negated_ignore_rules,
                f".gitignore should protect {expected}",
            )

    secret_name = re.compile(r"(^|[._-])(credentials?|secrets?|tokens?)([._-]|$)", re.IGNORECASE)
    walk_errors: list[OSError] = []
    for current, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
        onerror=walk_errors.append,
    ):
        current_path = Path(current)
        safe_directories: list[str] = []
        for name in sorted(directory_names):
            if name == ".git":
                continue
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if has_symlink_component(root, path):
                report.warn(False, f"link or Windows reparse point is not traversed by ScholarFS core: {relative}")
                continue
            safe_directories.append(name)
        directory_names[:] = safe_directories

        for name in sorted(file_names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if has_symlink_component(root, path):
                report.warn(False, f"link or Windows reparse point is not read by ScholarFS core: {relative}")
                continue
            if not path.is_file():
                continue
            risky = (
                path.name.startswith(".env")
                or path.suffix.lower() in {".pem", ".key", ".p12"}
                or bool(secret_name.search(path.name))
            )
            if risky and relative not in {".env.example"}:
                report.warnings.append(f"possible credential file inside workspace: {relative}")
    for error in walk_errors:
        report.warn(False, f"workspace path could not be inspected safely: {error}")

    return report
