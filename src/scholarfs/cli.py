from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .calendar import export_ics
from .connectors import apply_deadline_import, plan_deadline_import
from .context import build_context, write_context
from .deadlines import (
    KINDS,
    PRIORITIES,
    add_deadline,
    due_text,
    list_deadlines,
    set_deadline_status,
    status_summary,
)
from .utils import (
    ScholarFSError,
    find_workspace,
    format_json,
    load_workspace_json,
    normalize_course_code,
    parse_as_of,
    parse_date,
)
from .validation import validate_workspace
from .workspace import add_course, add_file, course_by_code, init_workspace, list_courses


def _workspace(args: argparse.Namespace) -> Path:
    start = Path(args.workspace).expanduser() if getattr(args, "workspace", None) else None
    root = find_workspace(start)
    load_workspace_json(root, ".student/workspace.json")
    return root


def _print_courses(items: list[dict[str, object]]) -> None:
    if not items:
        print("No courses yet. Add one with `scholarfs course add CODE`.")
        return
    width = max(6, *(len(str(item.get("code", ""))) for item in items))
    print(f"{'COURSE':<{width}}  TITLE")
    for item in items:
        print(f"{str(item.get('code', '')):<{width}}  {item.get('title', '')}")


def _relative_label(days: int, *, overdue: bool = False) -> str:
    if overdue:
        if days == 0:
            return "overdue"
        return f"overdue {abs(days)}d"
    if days < 0:
        return f"due {abs(days)}d ago"
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"in {days}d"


def _print_deadlines(items: list[dict[str, object]]) -> None:
    if not items:
        print("No matching deadlines.")
        return
    print("ID        COURSE       DUE                         STATUS      TITLE")
    for item in items:
        marker = "!" if item.get("attention") else " "
        deadline_id = str(item.get("id", ""))[:8]
        course = str(item.get("course") or "SEMESTER")[:12]
        due = due_text(item)[:27]
        status = str(item.get("status", ""))[:10]
        days = int(item.get("days_remaining", 0))
        print(
            f"{deadline_id:<8}  {course:<12} {due:<27} {status:<10} {marker} "
            f"{item.get('title', '')} ({_relative_label(days, overdue=bool(item.get('overdue')))})"
        )
    print("\n! needs attention: overdue, due within 3 days, or high/critical priority")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scholarfs",
        description="Create and manage a local-first, provider-neutral student workspace.",
    )
    parser.add_argument("--workspace", metavar="PATH", help="workspace path; otherwise search upward from the current directory")
    parser.add_argument("--version", action="version", version=f"ScholarFS {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a new workspace without overwriting files")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--name", help="human-readable workspace name")
    init.add_argument("--term", default="My semester", help="term label, for example 'Fall 2026'")
    init.add_argument("--timezone", default="local", help="'local' or an IANA timezone name; timed deadlines still require offsets")
    init.add_argument("--merge", action="store_true", help="add only missing ScholarFS files to a non-empty directory")

    course = commands.add_parser("course", help="manage course metadata")
    course_commands = course.add_subparsers(dest="course_command", required=True)
    course_add = course_commands.add_parser("add", help="add a course and its human-readable folders")
    course_add.add_argument("code")
    course_add.add_argument("--title")
    course_add.add_argument("--instructor")
    course_add.add_argument("--credits", type=float)
    course_list = course_commands.add_parser("list", help="list courses")
    course_list.add_argument("--json", action="store_true")

    file_command = commands.add_parser("file", help="copy source material into the workspace")
    file_commands = file_command.add_subparsers(dest="file_command", required=True)
    file_add = file_commands.add_parser("add", help="copy a file; never moves or parses the source")
    file_add.add_argument("source")
    file_add.add_argument("--course")
    file_add.add_argument(
        "--kind",
        required=True,
        choices=["syllabus", "assignment", "lecture", "note", "resource", "inbox"],
    )
    file_add.add_argument("--name", help="destination filename")

    deadline = commands.add_parser("deadline", help="manage normalized deadlines")
    deadline_commands = deadline.add_subparsers(dest="deadline_command", required=True)
    deadline_add = deadline_commands.add_parser("add", help="add a deadline")
    deadline_add.add_argument("title")
    deadline_add.add_argument("--course")
    precision = deadline_add.add_mutually_exclusive_group(required=True)
    precision.add_argument("--at", help="RFC 3339 timestamp with an explicit offset")
    precision.add_argument("--on", help="date-only deadline in YYYY-MM-DD form")
    deadline_add.add_argument("--kind", choices=sorted(KINDS), default="assignment")
    deadline_add.add_argument("--url")
    deadline_add.add_argument("--remind", action="append", type=int, metavar="MINUTES")
    deadline_add.add_argument("--priority", choices=sorted(PRIORITIES), default="normal")
    deadline_add.add_argument("--weight", type=float, dest="weight_percent")
    deadline_add.add_argument("--estimate-minutes", type=int)
    deadline_add.add_argument("--tag", action="append", dest="tags")

    deadline_list = deadline_commands.add_parser("list", help="show open deadlines in a time window")
    deadline_list.add_argument("--course")
    horizon = deadline_list.add_mutually_exclusive_group()
    horizon.add_argument("--days", type=int)
    horizon.add_argument("--until", help="inclusive end date in YYYY-MM-DD form")
    horizon.add_argument("--all", action="store_true", dest="all_items", help="show every date and status")
    deadline_list.add_argument("--include-closed", action="store_true", help="include completed and cancelled items in the selected window")
    deadline_list.add_argument("--as-of", help="deterministic RFC 3339 clock for demos or audits")
    deadline_list.add_argument("--json", action="store_true")

    for name, status, help_text in [
        ("done", "completed", "mark a deadline complete"),
        ("reopen", "pending", "reopen a deadline"),
        ("cancel", "cancelled", "cancel a deadline"),
    ]:
        status_parser = deadline_commands.add_parser(name, help=help_text)
        status_parser.add_argument("id", help="full deadline UUID or a unique prefix")
        status_parser.set_defaults(target_status=status)

    deadline_import = deadline_commands.add_parser("import", help="preview or apply a normalized connector export")
    deadline_import.add_argument("file")
    deadline_import.add_argument("--apply", action="store_true", help="apply after validation; preview is the default")
    deadline_import.add_argument("--json", action="store_true")

    calendar = commands.add_parser("calendar", help="export deadlines to a standard calendar file")
    calendar_commands = calendar.add_subparsers(dest="calendar_command", required=True)
    calendar_export = calendar_commands.add_parser("export", help="write an ICS calendar with reminder alarms")
    calendar_export.add_argument("file")
    calendar_export.add_argument("--course")
    completed_mode = calendar_export.add_mutually_exclusive_group()
    completed_mode.add_argument(
        "--include-completed",
        action="store_true",
        dest="include_completed",
        default=None,
        help="include completed items, overriding notification settings",
    )
    completed_mode.add_argument(
        "--exclude-completed",
        action="store_false",
        dest="include_completed",
        help="omit completed items, overriding notification settings",
    )
    calendar_export.add_argument(
        "--include-notes",
        action="store_true",
        help="include free-form deadline notes in the calendar file",
    )
    calendar_export.add_argument("--force", action="store_true", help="replace the exact output file if it exists")

    status = commands.add_parser("status", help="summarize the next part of the semester")
    status.add_argument("--days", type=int, default=14)
    status.add_argument("--as-of", help="deterministic RFC 3339 clock for demos or audits")
    status.add_argument("--json", action="store_true")

    context = commands.add_parser("context", help="print a deterministic, allowlisted Markdown context bundle")
    context.add_argument("course", nargs="?")
    context.add_argument("--include-private", action="store_true", help="explicitly include local private Markdown files")
    context.add_argument("--max-bytes", type=int, default=250_000)
    context.add_argument("--output", metavar="PATH", help="write inside the workspace; relative paths resolve from its root")
    context.add_argument("--force", action="store_true", help="replace the exact context output file if it exists")

    validate = commands.add_parser("validate", aliases=["doctor"], help="check structure, data invariants, and privacy footguns")
    validate.add_argument("path", nargs="?")
    validate.add_argument("--strict", action="store_true", help="treat warnings as a failing result")
    validate.add_argument("--json", action="store_true")
    return parser


def dispatch(args: argparse.Namespace) -> int:
    if args.command == "init":
        target = Path(args.path)
        created, skipped = init_workspace(
            target,
            name=args.name,
            term=args.term,
            timezone_name=args.timezone,
            merge=args.merge,
        )
        print(f"Created ScholarFS workspace at {target.expanduser().resolve()}")
        print(f"{len(created)} files created" + (f", {len(skipped)} existing files left untouched" if skipped else ""))
        print("Next: enter the directory and run `scholarfs course add CODE`.")
        return 0

    if args.command in {"validate", "doctor"}:
        if args.path:
            candidate = Path(args.path).expanduser().resolve()
            root = candidate if (candidate / ".student" / "workspace.json").is_file() else find_workspace(candidate)
        else:
            root = _workspace(args)
        report = validate_workspace(root)
        if args.json:
            print(format_json(report.to_dict()))
        else:
            state = "valid" if report.ok else "invalid"
            print(f"ScholarFS workspace is {state}: {root}")
            print(f"{report.checks} checks, {len(report.errors)} errors, {len(report.warnings)} warnings")
            for error in report.errors:
                print(f"ERROR: {error}")
            for warning in report.warnings:
                print(f"WARN:  {warning}")
        return 1 if report.errors or (args.strict and report.warnings) else 0

    root = _workspace(args)
    if args.command == "course":
        if args.course_command == "add":
            item = add_course(root, args.code, title=args.title, instructor=args.instructor, credits=args.credits)
            print(f"Added {item['code']}: {item['title']}")
            return 0
        items = list_courses(root)
        if args.json:
            print(format_json({"courses": items}))
        else:
            _print_courses(items)
        return 0

    if args.command == "file":
        destination, digest = add_file(root, Path(args.source), course=args.course, kind=args.kind, name=args.name)
        print(f"Copied to {destination.relative_to(root)}")
        print(f"SHA-256 {digest}")
        return 0

    if args.command == "deadline":
        if args.deadline_command == "add":
            item = add_deadline(
                root,
                args.title,
                course=args.course,
                at=args.at,
                on=args.on,
                kind=args.kind,
                url=args.url,
                reminders=args.remind,
                priority=args.priority,
                weight_percent=args.weight_percent,
                estimated_minutes=args.estimate_minutes,
                tags=args.tags,
            )
            print(f"Added {item['id']}: {item['title']} due {due_text(item)}")
            return 0
        if args.deadline_command == "list":
            as_of = parse_as_of(args.as_of)
            until = parse_date(args.until, field="--until") if args.until else None
            days = None if args.until or args.all_items else (args.days if args.days is not None else 14)
            items = list_deadlines(
                root,
                course=args.course,
                days=days,
                until=until,
                include_closed=args.include_closed,
                all_items=args.all_items,
                as_of=as_of,
            )
            if args.json:
                print(format_json({"as_of": as_of.isoformat(), "deadlines": items}))
            else:
                _print_deadlines(items)
            return 0
        if args.deadline_command in {"done", "reopen", "cancel"}:
            item = set_deadline_status(root, args.id, args.target_status)
            print(f"{item['id']}: {item['status']} - {item['title']}")
            return 0
        if args.deadline_command == "import":
            plan = apply_deadline_import(root, Path(args.file)) if args.apply else plan_deadline_import(root, Path(args.file))[0]
            if args.json:
                print(format_json(plan))
            else:
                mode = "Applied" if args.apply else "Preview"
                print(f"{mode}: {plan['connector']}")
                print(
                    f"{plan['adds']} add, {plan['updates']} update, "
                    f"{plan['unchanged']} unchanged, {plan['deletes']} delete"
                )
                if not args.apply:
                    print("No files changed. Re-run with --apply after reviewing the connector export.")
                elif plan.get("backup"):
                    print(f"Backup: {plan['backup']}")
            return 0

    if args.command == "calendar":
        course = normalize_course_code(args.course) if args.course else None
        if course and course_by_code(root, course) is None:
            raise ScholarFSError(f"unknown course: {course}")
        output = export_ics(
            root,
            Path(args.file),
            course=course,
            include_completed=args.include_completed,
            include_notes=args.include_notes,
            force=args.force,
        )
        print(f"Wrote {output}")
        return 0

    if args.command == "status":
        if args.days < 0:
            raise ScholarFSError("--days must be zero or greater")
        summary = status_summary(root, as_of=parse_as_of(args.as_of), days=args.days)
        if args.json:
            print(format_json(summary))
        else:
            print(f"Next {summary['horizon_days']} days")
            print(f"{summary['open_in_horizon']} open, {summary['overdue']} overdue, {summary['needs_attention']} need attention")
            for code, count in summary["by_course"].items():
                print(f"  {code:<12} {count}")
            print()
            _print_deadlines(summary["items"])
        return 0

    if args.command == "context":
        content = build_context(
            root,
            course=args.course,
            include_private=args.include_private,
            max_bytes=args.max_bytes,
        )
        if args.output:
            destination = write_context(root, Path(args.output), content, force=args.force)
            print(f"Wrote {destination.relative_to(root)}")
        else:
            sys.stdout.write(content)
        return 0

    raise ScholarFSError(f"unsupported command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        return dispatch(parser.parse_args(argv))
    except ScholarFSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
    except KeyboardInterrupt:
        print("cancelled", file=sys.stderr)
        return 130
