from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .utils import (
    ScholarFSError,
    iso_now,
    load_workspace_json,
    normalize_course_code,
    parse_date,
    parse_rfc3339,
    validate_timezone_name,
    write_json,
)
from .workspace import course_by_code


KINDS = {"assignment", "exam", "quiz", "lab", "project", "reading", "presentation", "event", "other"}
STATUSES = {"pending", "completed", "cancelled"}
PRIORITIES = {"low", "normal", "high", "critical"}
LOCAL_DISPLAY_ZONE = "local"


def deadlines_path(root: Path) -> Path:
    return root / ".student" / "deadlines.json"


def load_deadlines(root: Path) -> dict[str, Any]:
    return load_workspace_json(root, ".student/deadlines.json")


def make_due(*, at: str | None, on: str | None) -> dict[str, str]:
    if bool(at) == bool(on):
        raise ScholarFSError("choose exactly one deadline precision: --at TIMESTAMP or --on YYYY-MM-DD")
    if at:
        parsed = parse_rfc3339(at, field="--at")
        return {"at": parsed.isoformat().replace("+00:00", "Z")}
    assert on is not None
    return {"on": parse_date(on, field="--on").isoformat()}


def validate_url(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ScholarFSError("--url must be an absolute http:// or https:// URL")
    if not value or any(character.isspace() or ord(character) < 32 for character in value):
        raise ScholarFSError("--url must be an absolute http:// or https:// URL without whitespace")
    try:
        parsed = urlparse(value)
        parsed.port
    except ValueError as error:
        raise ScholarFSError("--url is malformed or contains an invalid port") from error
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username is not None or parsed.password is not None:
        raise ScholarFSError("--url must be an absolute http:// or https:// URL")
    return value


def _default_reminders(root: Path) -> list[int]:
    data = load_workspace_json(root, ".student/notifications.json")
    calendar = data.get("calendar", {})
    values = calendar.get("default_reminders_minutes", []) if isinstance(calendar, dict) else []
    if not isinstance(values, list) or not all(type(value) is int and value >= 0 for value in values):
        raise ScholarFSError("invalid default_reminders_minutes in .student/notifications.json")
    return sorted(set(values), reverse=True)


def add_deadline(
    root: Path,
    title: str,
    *,
    course: str | None,
    at: str | None,
    on: str | None,
    kind: str = "assignment",
    url: str | None = None,
    reminders: list[int] | None = None,
    priority: str = "normal",
    weight_percent: float | None = None,
    estimated_minutes: int | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    load_workspace_json(root, ".student/workspace.json")
    title = title.strip()
    if not title:
        raise ScholarFSError("deadline title may not be empty")
    if len(title) > 500:
        raise ScholarFSError("deadline title may not exceed 500 characters")
    if kind not in KINDS:
        raise ScholarFSError(f"deadline kind must be one of: {', '.join(sorted(KINDS))}")
    if priority not in PRIORITIES:
        raise ScholarFSError(f"priority must be one of: {', '.join(sorted(PRIORITIES))}")
    if weight_percent is not None and not (0 <= weight_percent <= 100):
        raise ScholarFSError("--weight must be between 0 and 100")
    if estimated_minutes is not None and estimated_minutes <= 0:
        raise ScholarFSError("--estimate-minutes must be greater than zero")
    if reminders is not None and any(type(value) is not int or value < 0 for value in reminders):
        raise ScholarFSError("--remind values must be non-negative minutes")
    cleaned_tags = sorted(set(tag.strip() for tag in (tags or []) if tag.strip()))
    if any(len(tag) > 100 for tag in cleaned_tags):
        raise ScholarFSError("--tag values may not exceed 100 characters")

    normalized_course: str | None = None
    if course:
        normalized_course = normalize_course_code(course)
        if course_by_code(root, normalized_course) is None:
            raise ScholarFSError(f"unknown course: {normalized_course}")

    now = iso_now()
    record = {
        "id": str(uuid.uuid4()),
        "course": normalized_course,
        "title": title,
        "kind": kind,
        "due": make_due(at=at, on=on),
        "status": "pending",
        "priority": priority,
        "weight_percent": weight_percent,
        "estimated_minutes": estimated_minutes,
        "source": {"type": "manual"},
        "url": validate_url(url),
        "reminders_minutes": sorted(set(reminders if reminders is not None else _default_reminders(root)), reverse=True),
        "tags": cleaned_tags,
        "notes": "",
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    data = load_deadlines(root)
    items = data.get("deadlines")
    if not isinstance(items, list):
        raise ScholarFSError(".student/deadlines.json has an invalid deadlines field; run scholarfs validate")
    items.append(record)
    write_json(deadlines_path(root), data)
    return record


def set_deadline_status(root: Path, deadline_id: str, status: str) -> dict[str, Any]:
    load_workspace_json(root, ".student/workspace.json")
    if status not in STATUSES:
        raise ScholarFSError(f"status must be one of: {', '.join(sorted(STATUSES))}")
    data = load_deadlines(root)
    items = data.get("deadlines")
    if not isinstance(items, list):
        raise ScholarFSError(".student/deadlines.json has an invalid deadlines field; run scholarfs validate")
    matches = [
        item
        for item in items
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item["id"].startswith(deadline_id)
    ]
    if not matches:
        raise ScholarFSError(f"unknown deadline id: {deadline_id}")
    if len(matches) > 1:
        raise ScholarFSError(f"deadline id prefix is ambiguous: {deadline_id}")
    record = matches[0]
    now = iso_now()
    record["status"] = status
    record["updated_at"] = now
    record["completed_at"] = now if status == "completed" else None
    write_json(deadlines_path(root), data)
    return record


def due_sort_key(item: dict[str, Any]) -> tuple[float, str]:
    due = item.get("due", {})
    if isinstance(due, dict):
        if "at" in due:
            try:
                return (parse_rfc3339(str(due["at"]), field="deadline due.at").timestamp(), str(item.get("id", "")))
            except ScholarFSError:
                pass
        if "on" in due:
            try:
                end_of_date = datetime.combine(parse_date(str(due["on"])), time.max, tzinfo=timezone.utc)
                return (end_of_date.timestamp(), str(item.get("id", "")))
            except ScholarFSError:
                pass
    return (float("inf"), str(item.get("id", "")))


def _workspace_zone(root: Path, as_of: datetime) -> Any:
    workspace = load_workspace_json(root, ".student/workspace.json")
    name = validate_timezone_name(workspace.get("timezone"), field="workspace timezone")
    if name == "local":
        return LOCAL_DISPLAY_ZONE
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ScholarFSError(
            f"workspace timezone is unavailable: {name}; install the Python tzdata package or choose a valid IANA timezone"
        ) from error


def _system_local(moment: datetime) -> datetime:
    """Convert one instant with the operating system's rules for that instant."""
    return moment.astimezone()


def _display_datetime(moment: datetime, display_zone: Any | None) -> datetime:
    if display_zone == LOCAL_DISPLAY_ZONE:
        return _system_local(moment)
    zone = display_zone or moment.tzinfo or timezone.utc
    return moment.astimezone(zone)


def deadline_relation(item: dict[str, Any], as_of: datetime, *, display_zone: Any | None = None) -> tuple[int, bool]:
    due = item.get("due")
    if not isinstance(due, dict):
        raise ScholarFSError(f"deadline {item.get('id', '<unknown>')} has an invalid due field")
    local_as_of = _display_datetime(as_of, display_zone)
    if "on" in due:
        due_date = parse_date(str(due["on"]), field="deadline due.on")
        return (due_date - local_as_of.date()).days, due_date < local_as_of.date()
    if "at" in due:
        due_at = parse_rfc3339(str(due["at"]), field="deadline due.at")
        days = (_display_datetime(due_at, display_zone).date() - local_as_of.date()).days
        return days, due_at.astimezone(timezone.utc) < as_of.astimezone(timezone.utc)
    raise ScholarFSError(f"deadline {item.get('id', '<unknown>')} must contain due.at or due.on")


def days_from(item: dict[str, Any], as_of: datetime, *, display_zone: Any | None = None) -> int:
    return deadline_relation(item, as_of, display_zone=display_zone)[0]


def due_text(item: dict[str, Any]) -> str:
    due = item.get("due", {})
    if isinstance(due, dict):
        return str(due.get("at") or due.get("on") or "invalid")
    return "invalid"


def list_deadlines(
    root: Path,
    *,
    course: str | None = None,
    days: int | None = 14,
    until: date | None = None,
    include_closed: bool = False,
    all_items: bool = False,
    as_of: datetime | None = None,
) -> list[dict[str, Any]]:
    if days is not None and days < 0:
        raise ScholarFSError("--days must be zero or greater")
    normalized_course = normalize_course_code(course) if course else None
    moment = as_of or datetime.now().astimezone()
    display_zone = _workspace_zone(root, moment)
    data = load_deadlines(root)
    raw_items = data.get("deadlines")
    if not isinstance(raw_items, list):
        raise ScholarFSError(".student/deadlines.json has an invalid deadlines field; run scholarfs validate")

    selected: list[dict[str, Any]] = []
    for original in raw_items:
        if not isinstance(original, dict):
            continue
        if normalized_course and original.get("course") != normalized_course:
            continue
        if not include_closed and not all_items and original.get("status") in {"completed", "cancelled"}:
            continue
        remaining, overdue = deadline_relation(original, moment, display_zone=display_zone)
        if not all_items:
            if original.get("status") in {"completed", "cancelled"} and remaining < 0:
                continue
            if until is not None:
                due = original.get("due", {})
                due_date = (
                    parse_date(str(due["on"]))
                    if isinstance(due, dict) and "on" in due
                    else _display_datetime(parse_rfc3339(str(due["at"])), display_zone).date()
                )
                if due_date > until:
                    continue
            elif days is not None and remaining > days:
                continue
        pending_overdue = original.get("status") == "pending" and overdue
        item = dict(original)
        item["days_remaining"] = remaining
        item["overdue"] = pending_overdue
        item["attention"] = (
            original.get("status") == "pending"
            and (
                pending_overdue
                or remaining <= 3
                or original.get("priority") in {"high", "critical"}
            )
        )
        selected.append(item)
    return sorted(selected, key=due_sort_key)


def status_summary(root: Path, *, as_of: datetime | None = None, days: int = 14) -> dict[str, Any]:
    moment = as_of or datetime.now().astimezone()
    upcoming = list_deadlines(root, days=days, include_closed=False, as_of=moment)
    overdue = [item for item in upcoming if item["overdue"]]
    attention = [item for item in upcoming if item["attention"]]
    by_course: dict[str, int] = {}
    for item in upcoming:
        key = str(item.get("course") or "SEMESTER")
        by_course[key] = by_course.get(key, 0) + 1
    return {
        "as_of": moment.isoformat(),
        "horizon_days": days,
        "open_in_horizon": len(upcoming),
        "overdue": len(overdue),
        "needs_attention": len(attention),
        "by_course": dict(sorted(by_course.items())),
        "items": upcoming,
    }
