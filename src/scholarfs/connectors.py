from __future__ import annotations

import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .deadlines import KINDS, PRIORITIES, deadlines_path, load_deadlines, make_due, validate_url
from .utils import (
    ScholarFSError,
    iso_now,
    load_json,
    load_workspace_json,
    normalize_course_code,
    parse_rfc3339,
    require_safe_workspace_path,
    write_json,
)
from .workspace import course_by_code


CONNECTOR_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
IMPORT_ITEM_FIELDS = {
    "external_id",
    "course",
    "title",
    "kind",
    "due",
    "status",
    "url",
    "priority",
    "weight_percent",
    "estimated_minutes",
}
IMPORT_REQUIRED_FIELDS = {"external_id", "course", "title", "kind", "due", "status"}


def _source_key(item: dict[str, Any]) -> tuple[str, str] | None:
    source = item.get("source")
    if not isinstance(source, dict) or source.get("type") != "connector":
        return None
    connector = source.get("connector")
    external_id = source.get("external_id")
    if isinstance(connector, str) and isinstance(external_id, str):
        return connector, external_id
    return None


def _normalized_import_items(root: Path, envelope: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]]]:
    if type(envelope.get("schema_version")) is not int or envelope.get("schema_version") != 1:
        raise ScholarFSError("deadline import schema_version must be integer 1")
    extra_root = set(envelope) - {"schema_version", "connector", "generated_at", "items"}
    if extra_root:
        raise ScholarFSError(f"deadline import contains unsupported top-level fields: {', '.join(sorted(extra_root))}")
    connector = envelope.get("connector")
    if not isinstance(connector, dict):
        raise ScholarFSError("deadline import connector must be an object")
    extra_connector = set(connector) - {"id", "version"}
    if extra_connector:
        raise ScholarFSError(f"deadline import connector contains unsupported fields: {', '.join(sorted(extra_connector))}")
    connector_id = connector.get("id")
    connector_version = connector.get("version")
    if not isinstance(connector_id, str) or not CONNECTOR_ID_RE.fullmatch(connector_id):
        raise ScholarFSError("connector.id must use lowercase letters, numbers, and hyphens")
    if not isinstance(connector_version, str) or not connector_version.strip() or len(connector_version) > 50:
        raise ScholarFSError("connector.version must be a non-empty string up to 50 characters")
    generated_at = envelope.get("generated_at")
    if not isinstance(generated_at, str):
        raise ScholarFSError("deadline import generated_at must be a timestamp string")
    parse_rfc3339(generated_at, field="deadline import generated_at")
    raw_items = envelope.get("items")
    if not isinstance(raw_items, list):
        raise ScholarFSError("deadline import items must be an array")

    normalized: list[dict[str, Any]] = []
    external_ids: set[str] = set()
    for index, raw in enumerate(raw_items):
        label = f"items[{index}]"
        if not isinstance(raw, dict):
            raise ScholarFSError(f"{label} must be an object")
        extras = set(raw) - IMPORT_ITEM_FIELDS
        if extras:
            raise ScholarFSError(f"{label} contains unsupported fields: {', '.join(sorted(extras))}")
        missing = IMPORT_REQUIRED_FIELDS - set(raw)
        if missing:
            raise ScholarFSError(f"{label} is missing required fields: {', '.join(sorted(missing))}")
        external_id = raw.get("external_id")
        if not isinstance(external_id, str) or not external_id.strip() or len(external_id) > 256:
            raise ScholarFSError(f"{label}.external_id must be a non-empty string up to 256 characters")
        if external_id in external_ids:
            raise ScholarFSError(f"duplicate external_id in import: {external_id}")
        external_ids.add(external_id)
        title = raw.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ScholarFSError(f"{label}.title must be a non-empty string")
        if len(title.strip()) > 500:
            raise ScholarFSError(f"{label}.title must not exceed 500 characters")
        kind = raw.get("kind", "assignment")
        if not isinstance(kind, str) or kind not in KINDS:
            raise ScholarFSError(f"{label}.kind must be one of: {', '.join(sorted(KINDS))}")
        status = raw.get("status", "pending")
        if not isinstance(status, str) or status not in {"pending", "cancelled"}:
            raise ScholarFSError(f"{label}.status must be pending or cancelled")
        priority = raw.get("priority", "normal")
        if not isinstance(priority, str) or priority not in PRIORITIES:
            raise ScholarFSError(f"{label}.priority must be one of: {', '.join(sorted(PRIORITIES))}")
        course: str | None = None
        if raw.get("course") is not None:
            if not isinstance(raw["course"], str):
                raise ScholarFSError(f"{label}.course must be a string or null")
            course = normalize_course_code(raw["course"])
            if raw["course"] != course:
                raise ScholarFSError(f"{label}.course must already use normalized uppercase form: {course}")
            if course_by_code(root, course) is None:
                raise ScholarFSError(f"{label} references unknown course: {course}")
        due = raw.get("due")
        if not isinstance(due, dict) or set(due) not in ({"at"}, {"on"}):
            raise ScholarFSError(f"{label}.due must contain exactly one of at or on")
        normalized_due = make_due(at=str(due["at"]) if "at" in due else None, on=str(due["on"]) if "on" in due else None)
        weight = raw.get("weight_percent")
        if weight is not None and (not isinstance(weight, (int, float)) or isinstance(weight, bool) or not 0 <= weight <= 100):
            raise ScholarFSError(f"{label}.weight_percent must be between 0 and 100")
        estimate = raw.get("estimated_minutes")
        if estimate is not None and (not isinstance(estimate, int) or isinstance(estimate, bool) or estimate <= 0):
            raise ScholarFSError(f"{label}.estimated_minutes must be a positive integer")
        url = raw.get("url")
        if url is not None and not isinstance(url, str):
            raise ScholarFSError(f"{label}.url must be a string or null")
        normalized.append(
            {
                "external_id": external_id,
                "course": course,
                "title": title.strip(),
                "kind": kind,
                "due": normalized_due,
                "status": status,
                "url": validate_url(url),
                "priority": priority,
                "weight_percent": weight,
                "estimated_minutes": estimate,
            }
        )
    return connector_id, generated_at, normalized


def _merged_record(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
    *,
    connector_id: str,
    connector_version: str,
    generated_at: str,
) -> dict[str, Any]:
    now = iso_now()
    record: dict[str, Any] = dict(existing or {})
    if existing is None:
        record.update(
            {
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"urn:scholarfs:{connector_id}:{incoming['external_id']}")),
                "reminders_minutes": [],
                "tags": [],
                "notes": "",
                "created_at": now,
                "completed_at": None,
            }
        )
    record.update(
        {
            "course": incoming["course"],
            "title": incoming["title"],
            "kind": incoming["kind"],
            "due": incoming["due"],
            "priority": incoming["priority"],
            "weight_percent": incoming["weight_percent"],
            "estimated_minutes": incoming["estimated_minutes"],
            "url": incoming["url"],
            "source": {
                "type": "connector",
                "connector": connector_id,
                "connector_version": connector_version,
                "external_id": incoming["external_id"],
                "observed_at": generated_at,
            },
        }
    )
    incoming_status = incoming["status"]
    if incoming_status == "cancelled":
        record["status"] = "cancelled"
        record["completed_at"] = None
    elif existing is None or existing.get("status") != "completed":
        record["status"] = "pending"
        record["completed_at"] = None
    record["updated_at"] = now
    return record


def plan_deadline_import(root: Path, envelope_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    load_workspace_json(root, ".student/workspace.json")
    envelope_path = envelope_path.expanduser().resolve()
    if not envelope_path.is_file():
        raise ScholarFSError(f"deadline import file does not exist: {envelope_path}")
    envelope = load_json(envelope_path)
    connector_id, generated_at, incoming_items = _normalized_import_items(root, envelope)
    connector_version = str(envelope["connector"]["version"])

    data = load_deadlines(root)
    existing_items = data.get("deadlines")
    if not isinstance(existing_items, list):
        raise ScholarFSError(".student/deadlines.json has an invalid deadlines field; run scholarfs validate")
    by_source: dict[tuple[str, str], dict[str, Any]] = {}
    for item in existing_items:
        if not isinstance(item, dict):
            continue
        key = _source_key(item)
        if key:
            if key in by_source:
                raise ScholarFSError(f"existing deadlines contain duplicate connector source key: {key[0]} / {key[1]}")
            by_source[key] = item

    adds = updates = unchanged = 0
    next_items = list(existing_items)
    positions = {id(item): index for index, item in enumerate(next_items)}
    generated_moment = parse_rfc3339(generated_at, field="deadline import generated_at")
    for incoming in incoming_items:
        key = (connector_id, incoming["external_id"])
        existing = by_source.get(key)
        if existing is not None:
            source = existing.get("source")
            observed_at = source.get("observed_at") if isinstance(source, dict) else None
            if not isinstance(observed_at, str):
                raise ScholarFSError(
                    f"existing connector deadline {connector_id} / {incoming['external_id']} "
                    "has no valid source.observed_at; run scholarfs validate"
                )
            observed_moment = parse_rfc3339(
                observed_at,
                field=f"existing connector deadline {connector_id} / {incoming['external_id']} source.observed_at",
            )
            if generated_moment < observed_moment:
                raise ScholarFSError(
                    f"stale deadline import for {connector_id} / {incoming['external_id']}: "
                    f"generated_at {generated_at} is older than stored observation {observed_at}"
                )
        merged = _merged_record(
            existing,
            incoming,
            connector_id=connector_id,
            connector_version=connector_version,
            generated_at=generated_at,
        )
        if existing is None:
            next_items.append(merged)
            adds += 1
            continue
        comparable_existing = dict(existing)
        comparable_merged = dict(merged)
        comparable_existing.pop("updated_at", None)
        comparable_merged.pop("updated_at", None)
        if comparable_existing == comparable_merged:
            unchanged += 1
            continue
        next_items[positions[id(existing)]] = merged
        updates += 1

    next_data = dict(data)
    next_data["deadlines"] = next_items
    plan = {
        "connector": connector_id,
        "source_file": str(envelope_path),
        "adds": adds,
        "updates": updates,
        "unchanged": unchanged,
        "deletes": 0,
        "total_incoming": len(incoming_items),
    }
    return plan, next_data


def apply_deadline_import(root: Path, envelope_path: Path) -> dict[str, Any]:
    plan, next_data = plan_deadline_import(root, envelope_path)
    if not plan["adds"] and not plan["updates"]:
        plan["backup"] = None
        return plan
    source = deadlines_path(root)
    backup_dir = root / ".student" / "backups"
    require_safe_workspace_path(root, source, label="deadline store")
    require_safe_workspace_path(root, backup_dir, label="backup directory")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backup_dir / f"deadlines-{stamp}-{uuid.uuid4().hex[:8]}.json"
    shutil.copy2(source, backup)
    try:
        write_json(source, next_data)
    except Exception:
        shutil.copy2(backup, source)
        raise
    plan["backup"] = str(backup.relative_to(root))
    return plan
