"""Offline reference connector for ScholarFS.

This script reads one local JSON file and writes normalized JSON to stdout. It
makes no network requests and handles no credentials.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def convert(source: dict[str, object]) -> dict[str, object]:
    assignments = source.get("assignments")
    if not isinstance(assignments, list):
        raise ValueError("source.assignments must be an array")
    items: list[dict[str, object]] = []
    for raw in assignments:
        if not isinstance(raw, dict):
            raise ValueError("every assignment must be an object")
        items.append(
            {
                "external_id": raw["id"],
                "course": raw.get("course_code"),
                "title": raw["name"],
                "kind": raw.get("category", "assignment"),
                "due": {"at": raw["due_at"]},
                "status": "cancelled" if raw.get("cancelled") else "pending",
                "url": raw.get("url"),
                "priority": "normal",
                "weight_percent": raw.get("weight"),
                "estimated_minutes": None,
            }
        )
    return {
        "schema_version": 1,
        "connector": {"id": "example-json", "version": "0.1.0"},
        "generated_at": source["generated_at"],
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("source must be a JSON object")
        json.dump(convert(data), sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

