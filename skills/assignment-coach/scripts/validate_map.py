#!/usr/bin/env python3
"""Validate an assignment map (the JSON every assignment-coach mode consumes) against
schemas/assignment-map.schema.json, plus the two rules a JSON schema cannot express: every id in
`depends_on` must name an existing question, and `due` must be a real calendar date.

Uses `jsonschema` when it is installed and a built-in validator of exactly the same rules otherwise,
so the result does not depend on what the student's machine has.

Usage:
    python3 validate_map.py MAP.json [--json]
Exit codes: 0 = valid, 1 = violations found, 2 = file unreadable / not JSON / usage.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

try:
    import jsonschema  # type: ignore

    HAVE_JSONSCHEMA = True
except ImportError:  # pragma: no cover - exercised by the tests through a blocked import
    jsonschema = None  # type: ignore
    HAVE_JSONSCHEMA = False

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "assignment-map.schema.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt_path(parts) -> str:
    out = ""
    for p in parts:
        out += f"[{p}]" if isinstance(p, int) else (f".{p}" if out else str(p))
    return out


def _with_path(path: str, message: str) -> str:
    return f"{path}: {message}" if path else message


# --------------------------------------------------------------------------------------------------
# Path 1: jsonschema
# --------------------------------------------------------------------------------------------------

def _schema_errors_jsonschema(obj, schema: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(obj), key=lambda e: (list(map(str, e.absolute_path)), e.message))
    return [_with_path(_fmt_path(e.absolute_path), e.message) for e in errors]


# --------------------------------------------------------------------------------------------------
# Path 2: hand-rolled, the same rules
# --------------------------------------------------------------------------------------------------

def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _enum_msg(value, allowed) -> str:
    return f"{value!r} is not one of {list(allowed)}"


def _schema_errors_builtin(obj, schema: dict) -> list[str]:
    props = schema["properties"]
    errors: list[str] = []
    if not isinstance(obj, dict):
        return [f"{obj!r} is not of type 'object'"]
    for key in schema["required"]:
        if key not in obj:
            errors.append(f"'{key}' is a required property")

    if "course" in obj and not isinstance(obj["course"], str):
        errors.append(f"course: {obj['course']!r} is not of type 'string'")
    if "family" in obj and obj["family"] not in props["family"]["enum"]:
        errors.append(f"family: {_enum_msg(obj['family'], props['family']['enum'])}")
    if "title" in obj:
        if not isinstance(obj["title"], str):
            errors.append(f"title: {obj['title']!r} is not of type 'string'")
        elif not obj["title"]:
            errors.append("title: '' should be non-empty")

    if "deliverables" in obj:
        if not isinstance(obj["deliverables"], list):
            errors.append(f"deliverables: {obj['deliverables']!r} is not of type 'array'")
        else:
            fmt_enum = props["deliverables"]["items"]["properties"]["format"]["enum"]
            for i, d in enumerate(obj["deliverables"]):
                if not isinstance(d, dict):
                    errors.append(f"deliverables[{i}]: {d!r} is not of type 'object'")
                    continue
                if "name" not in d:
                    errors.append(f"deliverables[{i}]: 'name' is a required property")
                elif not isinstance(d["name"], str):
                    errors.append(f"deliverables[{i}].name: {d['name']!r} is not of type 'string'")
                if "format" in d and d["format"] not in fmt_enum:
                    errors.append(f"deliverables[{i}].format: {_enum_msg(d['format'], fmt_enum)}")

    if "questions" in obj:
        qs = obj["questions"]
        if not isinstance(qs, list):
            errors.append(f"questions: {qs!r} is not of type 'array'")
        elif not qs:
            errors.append("questions: [] should be non-empty")
        else:
            q_props = props["questions"]["items"]["properties"]
            for i, q in enumerate(qs):
                p = f"questions[{i}]"
                if not isinstance(q, dict):
                    errors.append(f"{p}: {q!r} is not of type 'object'")
                    continue
                for key in props["questions"]["items"]["required"]:
                    if key not in q:
                        errors.append(f"{p}: '{key}' is a required property")
                if "id" in q:
                    if not isinstance(q["id"], str):
                        errors.append(f"{p}.id: {q['id']!r} is not of type 'string'")
                    elif not q["id"]:
                        errors.append(f"{p}.id: '' should be non-empty")
                if "type" in q and q["type"] not in q_props["type"]["enum"]:
                    errors.append(f"{p}.type: {_enum_msg(q['type'], q_props['type']['enum'])}")
                if "weight" in q:
                    if not _is_number(q["weight"]):
                        errors.append(f"{p}.weight: {q['weight']!r} is not of type 'number'")
                    elif q["weight"] < 0:
                        errors.append(f"{p}.weight: {q['weight']} is less than the minimum of 0")
                if "estimate_hours" in q:
                    if not _is_number(q["estimate_hours"]):
                        errors.append(f"{p}.estimate_hours: {q['estimate_hours']!r} is not of type 'number'")
                    elif q["estimate_hours"] <= 0:
                        errors.append(f"{p}.estimate_hours: {q['estimate_hours']} is less than or equal to the minimum of 0")
                if "text" in q and not isinstance(q["text"], str):
                    errors.append(f"{p}.text: {q['text']!r} is not of type 'string'")
                if "depends_on" in q:
                    if not isinstance(q["depends_on"], list):
                        errors.append(f"{p}.depends_on: {q['depends_on']!r} is not of type 'array'")
                    else:
                        for j, dep in enumerate(q["depends_on"]):
                            if not isinstance(dep, str):
                                errors.append(f"{p}.depends_on[{j}]: {dep!r} is not of type 'string'")

    if "constraints" in obj:
        if not isinstance(obj["constraints"], list):
            errors.append(f"constraints: {obj['constraints']!r} is not of type 'array'")
        else:
            for i, c in enumerate(obj["constraints"]):
                if not isinstance(c, str):
                    errors.append(f"constraints[{i}]: {c!r} is not of type 'string'")
    if "show_work" in obj and not isinstance(obj["show_work"], bool):
        errors.append(f"show_work: {obj['show_work']!r} is not of type 'boolean'")
    if "due" in obj and obj["due"] is not None:
        due = obj["due"]
        if not isinstance(due, str):
            errors.append(f"due: {due!r} is not of type 'string', 'null'")
        elif not DATE_RE.match(due):
            errors.append(f"due: {due!r} does not match {props['due']['pattern']!r}")
    if "ai_policy" in obj and obj["ai_policy"] not in props["ai_policy"]["enum"]:
        errors.append(f"ai_policy: {_enum_msg(obj['ai_policy'], props['ai_policy']['enum'])}")
    return errors


# --------------------------------------------------------------------------------------------------
# Rules beyond the schema (both paths)
# --------------------------------------------------------------------------------------------------

def _semantic_errors(obj) -> list[str]:
    errors: list[str] = []
    if not isinstance(obj, dict):
        return errors
    qs = obj.get("questions")
    if isinstance(qs, list):
        ids = {q.get("id") for q in qs if isinstance(q, dict) and isinstance(q.get("id"), str)}
        for i, q in enumerate(qs):
            if not isinstance(q, dict):
                continue
            for key in ("depends_on", "depends_on_interface"):
                if not isinstance(q.get(key), list):
                    continue
                for dep in q[key]:
                    if isinstance(dep, str) and dep not in ids:
                        errors.append(f"questions[{i}].{key}: {dep!r} is not the id of any question")
    due = obj.get("due")
    if isinstance(due, str) and DATE_RE.match(due):
        try:
            _dt.date.fromisoformat(due)
        except ValueError:
            errors.append(f"due: {due!r} is not a real calendar date")
    return errors


def validate_map(obj, schema: dict | None = None) -> list[str]:
    """Return a list of human-readable problems; an empty list means the map is valid."""
    schema = schema or load_schema()
    if HAVE_JSONSCHEMA:
        errors = _schema_errors_jsonschema(obj, schema)
    else:
        errors = _schema_errors_builtin(obj, schema)
    return errors + _semantic_errors(obj)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("map", help="assignment map JSON file")
    ap.add_argument("--json", action="store_true", help='print {"ok": bool, "errors": [...]} and nothing else')
    args = ap.parse_args(argv)

    def emit(ok: bool, errors: list[str], code: int) -> int:
        if args.json:
            print(json.dumps({"ok": ok, "errors": errors}, ensure_ascii=False))
        else:
            if ok:
                print(f"{args.map}: valid assignment map")
            else:
                for e in errors:
                    print(f"  {e}")
                print(f"{args.map}: {len(errors)} problem(s)")
        return code

    try:
        obj = json.loads(Path(args.map).read_text(encoding="utf-8"))
    except OSError as exc:
        return emit(False, [f"cannot read {args.map}: {exc.strerror or exc}"], 2)
    except json.JSONDecodeError as exc:
        return emit(False, [f"{args.map} is not valid JSON: {exc}"], 2)
    errors = validate_map(obj)
    return emit(not errors, errors, 1 if errors else 0)


if __name__ == "__main__":
    sys.exit(main())
