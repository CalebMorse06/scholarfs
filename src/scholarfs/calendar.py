from __future__ import annotations

from datetime import timedelta, timezone
from pathlib import Path
from typing import Any

from .deadlines import load_deadlines, validate_url
from .utils import ScholarFSError, atomic_write_text, load_workspace_json, parse_date, parse_rfc3339


def _escape(value: object) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def _fold(line: str) -> list[str]:
    if len(line.encode("utf-8")) <= 75:
        return [line]
    output: list[str] = []
    current = ""
    for character in line:
        candidate = current + character
        if len(candidate.encode("utf-8")) > 75:
            output.append(current)
            current = " " + character
        else:
            current = candidate
    if current:
        output.append(current)
    return output


def _timestamp(value: object) -> str:
    parsed = parse_rfc3339(str(value), field="deadline timestamp")
    return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(
    root: Path,
    *,
    course: str | None = None,
    include_completed: bool | None = None,
    include_notes: bool = False,
) -> str:
    load_workspace_json(root, ".student/workspace.json")
    if include_completed is None:
        notifications = load_workspace_json(root, ".student/notifications.json")
        calendar_settings = notifications.get("calendar")
        if not isinstance(calendar_settings, dict) or not isinstance(calendar_settings.get("include_completed"), bool):
            raise ScholarFSError(
                ".student/notifications.json has an invalid calendar.include_completed field; run scholarfs validate"
            )
        include_completed = calendar_settings["include_completed"]
    data = load_deadlines(root)
    raw_items = data.get("deadlines")
    if not isinstance(raw_items, list):
        raise ScholarFSError(".student/deadlines.json has an invalid deadlines field; run scholarfs validate")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ScholarFS//ScholarFS 0.1//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:ScholarFS deadlines",
    ]
    items = sorted(
        (item for item in raw_items if isinstance(item, dict)),
        key=lambda item: str(item.get("id", "")),
    )
    for item in items:
        if course and item.get("course") != course:
            continue
        status = item.get("status")
        if status == "cancelled" or (status == "completed" and not include_completed):
            continue
        deadline_id = str(item.get("id", ""))
        title = f"[{item['course']}] {item.get('title', 'Untitled')}" if item.get("course") else str(item.get("title", "Untitled"))
        updated = item.get("updated_at") or item.get("created_at")
        if not updated:
            raise ScholarFSError(f"deadline {deadline_id or '<unknown>'} has no updated_at or created_at")
        event = [
            "BEGIN:VEVENT",
            f"UID:{_escape(deadline_id)}@scholarfs.local",
            f"DTSTAMP:{_timestamp(updated)}",
            f"SUMMARY:{_escape(title)}",
        ]
        due = item.get("due")
        if not isinstance(due, dict):
            raise ScholarFSError(f"deadline {deadline_id or '<unknown>'} has an invalid due field")
        all_day = False
        if "on" in due:
            all_day = True
            start = parse_date(str(due["on"]), field="deadline due.on")
            event.extend(
                [
                    f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
                    f"DTEND;VALUE=DATE:{(start + timedelta(days=1)).strftime('%Y%m%d')}",
                ]
            )
        elif "at" in due:
            event.append(f"DTSTART:{_timestamp(due['at'])}")
        else:
            raise ScholarFSError(f"deadline {deadline_id or '<unknown>'} must contain due.at or due.on")
        description_parts = [f"Kind: {item.get('kind', 'other')}", f"Status: {status or 'pending'}"]
        if include_notes and item.get("notes"):
            description_parts.append(str(item["notes"]))
        event.append(f"DESCRIPTION:{_escape(chr(10).join(description_parts))}")
        if item.get("url"):
            event.append(f"URL:{validate_url(item['url'])}")
        reminders = item.get("reminders_minutes", [])
        if not isinstance(reminders, list):
            raise ScholarFSError(f"deadline {deadline_id or '<unknown>'} has invalid reminders_minutes")
        for minutes in reminders:
            if type(minutes) is not int or minutes < 0:
                raise ScholarFSError(f"deadline {deadline_id or '<unknown>'} has an invalid reminder")
            trigger = f"TRIGGER;RELATED=END:-PT{minutes}M" if all_day else f"TRIGGER:-PT{minutes}M"
            event.extend(
                [
                    "BEGIN:VALARM",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{_escape(title)}",
                    trigger,
                    "END:VALARM",
                ]
            )
        event.append("END:VEVENT")
        lines.extend(event)
    lines.append("END:VCALENDAR")
    folded = [folded_line for line in lines for folded_line in _fold(line)]
    return "\r\n".join(folded) + "\r\n"


def export_ics(
    root: Path,
    output: Path,
    *,
    course: str | None = None,
    include_completed: bool | None = None,
    include_notes: bool = False,
    force: bool = False,
) -> Path:
    output = output.expanduser().resolve()
    if output.exists() and not force:
        raise ScholarFSError(f"refusing to overwrite existing calendar: {output}; pass --force to replace it")
    atomic_write_text(
        output,
        build_ics(root, course=course, include_completed=include_completed, include_notes=include_notes),
    )
    return output
