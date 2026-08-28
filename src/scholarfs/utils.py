from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SPEC_VERSION = 1
COURSE_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,31}$")
RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$"
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
WINDOWS_NAME_SURROGATE_TAG = 0x20000000


class ScholarFSError(Exception):
    """An expected, user-actionable ScholarFS error."""


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_rfc3339(value: str, *, field: str = "timestamp") -> datetime:
    candidate = value.strip()
    if not RFC3339_RE.fullmatch(candidate):
        raise ScholarFSError(
            f"{field} must be an RFC 3339 timestamp with an explicit offset, for example 2026-09-04T23:59:00-05:00 or Z"
        )
    if candidate.endswith(("Z", "z")):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ScholarFSError(f"{field} must be an RFC 3339 timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ScholarFSError(f"{field} must include an explicit UTC offset, for example -05:00 or Z")
    return parsed


def parse_date(value: str, *, field: str = "date") -> date:
    candidate = value.strip()
    if not DATE_RE.fullmatch(candidate):
        raise ScholarFSError(f"{field} must use YYYY-MM-DD: {value!r}")
    try:
        return date.fromisoformat(candidate)
    except ValueError as exc:
        raise ScholarFSError(f"{field} must use YYYY-MM-DD: {value!r}") from exc


def parse_as_of(value: str | None) -> datetime:
    return parse_rfc3339(value, field="--as-of") if value else datetime.now(timezone.utc)


def validate_timezone_name(value: object, *, field: str = "timezone") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScholarFSError(f"{field} must be 'local' or a valid IANA timezone name")
    name = value.strip()
    if name == "local":
        return name
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ScholarFSError(f"{field} must be 'local' or a valid IANA timezone name: {name!r}") from error
    return name


def normalize_course_code(value: str) -> str:
    code = value.strip().upper()
    if not COURSE_CODE_RE.fullmatch(code):
        raise ScholarFSError(
            "course code must be 1-32 letters, numbers, dots, underscores, or hyphens "
            "and may not contain spaces or path separators"
        )
    if code != code.rstrip(". "):
        raise ScholarFSError("course code may not end with a dot or space")
    windows_stem = code.rstrip(". ").split(".", 1)[0]
    if windows_stem in WINDOWS_RESERVED_NAMES:
        raise ScholarFSError(f"course code {code!r} is a reserved Windows filename")
    return code


def slugify(value: str, *, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or fallback)[:64]


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ScholarFSError(f"required file is missing: {path}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScholarFSError(f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ScholarFSError(f"expected a JSON object in {path}")
    return data


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temp_name = handle.name
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=False).relative_to(root.resolve())
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def require_within(root: Path, candidate: Path, *, label: str = "path") -> Path:
    try:
        resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise ScholarFSError(f"{label} cannot be resolved safely: {candidate}") from error
    if not is_within(root, resolved):
        raise ScholarFSError(f"{label} must stay inside the workspace: {candidate}")
    return resolved


def is_redirecting_path(path: Path) -> bool:
    """Return true for symlinks and Windows name-surrogate reparse points."""
    if path.is_symlink():
        return True
    try:
        reparse_tag = getattr(os.lstat(path), "st_reparse_tag", 0)
    except OSError:
        return False
    return bool(reparse_tag & WINDOWS_NAME_SURROGATE_TAG)


def has_symlink_component(root: Path, candidate: Path) -> bool:
    """Return true when a path redirects through a link or leaves its root."""
    # Inspect only path components *inside* the workspace. Resolving the root
    # before calculating the relative path makes ordinary OS-level aliases look
    # like workspace links: macOS exposes /var through /private/var, and Windows
    # may expose a temporary directory through both its short and long names.
    # Containment is still checked with resolved paths below, so a real link that
    # leaves the workspace remains blocked.
    lexical_root = root.expanduser().absolute()
    lexical = candidate.expanduser().absolute()
    try:
        relative = lexical.relative_to(lexical_root)
    except ValueError:
        return True
    if not is_within(lexical_root, lexical):
        return True
    cursor = lexical_root
    for part in relative.parts:
        cursor = cursor / part
        if is_redirecting_path(cursor):
            return True
    return False


def require_safe_workspace_path(root: Path, candidate: Path, *, label: str = "path") -> Path:
    if has_symlink_component(root, candidate):
        raise ScholarFSError(f"{label} may not contain symbolic links or Windows reparse points: {candidate}")
    return require_within(root, candidate, label=label)


def load_workspace_json(root: Path, relative: str | Path) -> dict[str, Any]:
    path = require_safe_workspace_path(root, root / relative, label="workspace JSON path")
    data = load_json(path)
    version = data.get("schema_version")
    if type(version) is not int or version != SPEC_VERSION:
        try:
            label = path.relative_to(root.resolve())
        except ValueError:
            label = path
        raise ScholarFSError(
            f"unsupported schema_version in {label}: {version!r}; "
            f"ScholarFS {SPEC_VERSION} will not migrate it silently"
        )
    return data


def find_workspace(start: Path | None = None) -> Path:
    configured = os.environ.get("SCHOLARFS_WORKSPACE")
    cursor = start if start is not None else (Path(configured).expanduser() if configured else Path.cwd())
    cursor = cursor.resolve()
    if cursor.is_file():
        cursor = cursor.parent
    for candidate in (cursor, *cursor.parents):
        if (candidate / ".student" / "workspace.json").is_file():
            return candidate
    raise ScholarFSError(
        "no ScholarFS workspace found; run this command inside one, pass --workspace PATH, "
        "or set SCHOLARFS_WORKSPACE"
    )


def format_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
