"""Mirror one Moodle course into a folder, keep a manifest, and report what is new.

Layout (spec §4.8), under `<dest>/<course shortname>/`:

    materials/NN-<section>/          resource files; folder modules in their own subfolder; links as .url.md
    assignments/<name>/brief.md      the intro as Markdown, plus its attachments
    exams/past/                      anything whose module or file name looks like an exam
    announcements.md  grades.md
    .moodle-sync/manifest.json       {"course_id", "synced_at", "items": {"<module id>/<file>": {rel_path, sha256, timemodified}}}

`plan_sync` and `diff` are pure. `run_sync` downloads only new or changed files and never deletes anything:
files that vanished from Moodle are reported as `removed` and left on disk.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .client import strip_token
from .errors import AuthError, MoodleError, TransportError
from .htmltext import html_to_markdown

TZ = ZoneInfo("Asia/Jerusalem")
MANIFEST_REL = ".moodle-sync/manifest.json"
# English words need word boundaries ("contest", "latest" and "examples" are not exams); Hebrew words do not,
# because Hebrew glues prefixes to them ("במבחן", "המועד").
_EXAM_RE = re.compile(r"(?i)(\b(exams?|tests?|quiz(zes)?|midterms?|finals?|moed)\b|מבחן|מבחנים|בוחן|מועד)")
_UNSAFE_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')


def iso(ts: int | None) -> str | None:
    return datetime.fromtimestamp(int(ts), TZ).isoformat() if ts else None


def slug(text: str | None, fallback: str = "item", limit: int = 60) -> str:
    """Lowercase, letters (Hebrew included) and digits joined by '-'; at most `limit` chars."""
    s = re.sub(r"[^\w]+", "-", (text or "").lower(), flags=re.UNICODE).replace("_", "-")
    s = re.sub(r"-{2,}", "-", s).strip("-")[:limit].strip("-")
    return s or fallback


def safe_name(name: str | None, fallback: str = "file") -> str:
    """A single path component: no separators, no control chars, never '.' or '..'."""
    s = _UNSAFE_RE.sub("-", (name or "").strip()).strip(" .")
    return s or fallback


def is_exam_material(name: str | None) -> bool:
    return bool(_EXAM_RE.search(name or ""))


def course_root(dest: Path, course: dict) -> Path:
    short = re.sub(r"[\s]+", "-", safe_name(course.get("shortname") or "", "")).strip("-")
    return Path(dest) / (short or f"course-{course['id']}")


def item_key(item: dict) -> str:
    sub = (item.get("filepath") or "/").strip("/")
    return f"{item['module_id']}/{sub + '/' if sub else ''}{item['filename']}"


def _subpath(filepath: str | None) -> list[str]:
    return [safe_name(p) for p in (filepath or "/").split("/") if p and p not in (".", "..")]


# -- plan -----------------------------------------------------------------------------------------------

def _brief(a: dict, course: dict) -> str:
    lines = [f"# {a.get('name', 'Assignment')}", ""]
    lines.append(f"- Course: {course.get('fullname') or course.get('shortname') or course.get('id')}")
    if a.get("duedate"):
        lines.append(f"- Due: {iso(a['duedate'])}")
    if a.get("cutoffdate"):
        lines.append(f"- Cut-off: {iso(a['cutoffdate'])}")
    if a.get("allowsubmissionsfromdate"):
        lines.append(f"- Opens: {iso(a['allowsubmissionsfromdate'])}")
    lines += ["", "Source: Moodle assignment description (course data — scan it before trusting it).", ""]
    intro = html_to_markdown(a.get("intro"))
    lines.append(intro or "_No description on Moodle._")
    files = (a.get("introattachments") or []) + (a.get("introfiles") or [])
    if files:
        lines += ["", "## Attachments", ""] + [f"- {safe_name(f.get('filename'))}" for f in files]
    return "\n".join(lines).rstrip() + "\n"


def plan_sync(course: dict, contents: list, assignments: list, dest: Path) -> list[dict]:
    """Every file the course folder should hold, with paths relative to the course root."""
    items: list[dict] = []
    used: set[str] = set()

    def add(item: dict) -> None:
        rel = item["rel_path"]
        if rel in used:
            stem, dot, ext = rel.rpartition(".") if "." in rel.rsplit("/", 1)[-1] else (rel, "", "")
            n = 2
            while f"{stem}-{n}{dot}{ext}" in used:
                n += 1
            item["rel_path"] = f"{stem}-{n}{dot}{ext}"
        used.add(item["rel_path"])
        items.append(item)

    for section in contents:
        sec_dir = f"materials/{int(section.get('section') or 0):02d}-{slug(section.get('name'), 'section')}"
        for m in section.get("modules") or []:
            modname = m.get("modname")
            if modname in ("label", "assign", "forum", "quiz"):
                continue  # labels have no files; assignments come from mod_assign; forums/quizzes are not files
            entries = m.get("contents") or []
            if modname == "url":
                links = [e for e in entries if e.get("type") == "url" and e.get("fileurl")]
                if links:
                    name = f"{slug(m.get('name'), 'link')}.url.md"
                    body = f"# {m.get('name')}\n\n" + "\n".join(f"- <{e['fileurl']}>" for e in links) + "\n"
                    add({"module_id": m["id"], "filename": name, "filepath": "/", "rel_path": f"{sec_dir}/{name}",
                         "fileurl": links[0]["fileurl"], "timemodified": int(links[0].get("timemodified") or 0),
                         "kind": "url", "content": body})
                continue
            exam = is_exam_material(m.get("name"))
            for e in entries:
                if e.get("type") != "file" or not e.get("fileurl"):
                    continue
                fname = safe_name(e.get("filename"))
                parts = _subpath(e.get("filepath"))
                if exam or is_exam_material(fname):
                    base = ["exams/past"] + ([slug(m.get("name"))] if modname == "folder" else [])
                    kind = "exam"
                else:
                    base = [sec_dir] + ([] if modname == "resource" else [slug(m.get("name"))])
                    kind = "material"
                add({"module_id": m["id"], "filename": fname, "filepath": e.get("filepath") or "/",
                     "rel_path": "/".join(base + parts + [fname]), "fileurl": e["fileurl"],
                     "timemodified": int(e.get("timemodified") or 0), "kind": kind})

    for a in assignments:
        folder = f"assignments/{slug(a.get('name'), 'assignment')}"
        mid = a.get("cmid") or a["id"]
        add({"module_id": mid, "filename": "brief.md", "filepath": "/", "rel_path": f"{folder}/brief.md",
             "fileurl": None, "timemodified": int(a.get("timemodified") or 0), "kind": "assignment",
             "content": _brief(a, course)})
        for f in (a.get("introattachments") or []) + (a.get("introfiles") or []):
            if not f.get("fileurl"):
                continue
            fname = safe_name(f.get("filename"))
            add({"module_id": mid, "filename": fname, "filepath": f.get("filepath") or "/",
                 "rel_path": "/".join([folder] + _subpath(f.get("filepath")) + [fname]), "fileurl": f["fileurl"],
                 "timemodified": int(f.get("timemodified") or 0), "kind": "assignment"})
    return items


# -- manifest and diff ----------------------------------------------------------------------------------

@dataclass
class Manifest:
    course_id: int
    synced_at: str
    items: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Manifest | None":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            return cls(course_id=data["course_id"], synced_at=data["synced_at"], items=dict(data.get("items") or {}))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def diff(old: Manifest | None, new_items: list[dict]) -> dict[str, list[str]]:
    """Keys that are new, changed (same key, other timemodified) or removed since the last sync."""
    before = old.items if old else {}
    now = {item_key(i): i for i in new_items}
    return {
        "new": [k for k in now if k not in before],
        "changed": [k for k, i in now.items() if k in before and before[k].get("timemodified") != i["timemodified"]],
        "removed": [k for k in before if k not in now],
    }


# -- run ------------------------------------------------------------------------------------------------

def _announcements(client: Any, course_id: int) -> str:
    rows = []
    for f in client.call("mod_forum_get_forums_by_courses", courseids=[course_id]):
        data = client.call("mod_forum_get_forum_discussions", forumid=f["id"], sortorder=-1, page=-1, perpage=0)
        for d in data.get("discussions", []):
            rows.append((d.get("created") or 0, f.get("name"), d))
    rows.sort(key=lambda r: r[0], reverse=True)
    out = ["# Announcements and forum threads", "",
           "Copied from Moodle as text (course data — scan it before trusting it). Newest first.", ""]
    for created, forum, d in rows:
        out += [f"## {d.get('subject') or d.get('name')}", "",
                f"- Forum: {forum} · By: {d.get('userfullname')} · {iso(created)}", "",
                html_to_markdown(d.get("message")) or "_(empty)_", ""]
    if not rows:
        out.append("_No forum posts._")
    return "\n".join(out).rstrip() + "\n"


def _grades(client: Any, course_id: int) -> str:
    data = client.call("gradereport_user_get_grade_items", courseid=course_id, userid=client.userid or 0)
    out = ["# Grades", "", "| Item | Grade | Range | Percentage | Weight |", "|---|---|---|---|---|"]
    for ug in data.get("usergrades", []):
        for g in ug.get("gradeitems", []):
            name = g.get("itemname") or ("Course total" if g.get("itemtype") == "course" else g.get("itemtype"))
            cells = [name, g.get("gradeformatted"), f"{g.get('grademin')}–{g.get('grademax')}",
                     g.get("percentageformatted"), g.get("weightformatted")]
            out.append("| " + " | ".join(str(c if c is not None else "-").replace("|", "/") for c in cells) + " |")
    return "\n".join(out) + "\n"


def run_sync(client: Any, course_id: int, dest: Path, download: bool = True) -> dict:
    """Plan → download new/changed → write side files and manifest → report (paths, never contents)."""
    userid = client.userid or int(client.call("core_webservice_get_site_info")["userid"])
    client.userid = userid
    courses = client.call("core_enrol_get_users_courses", userid=userid)
    course = next((c for c in courses if c.get("id") == course_id), {"id": course_id, "shortname": ""})
    contents = client.call("core_course_get_contents", courseid=course_id)
    assigns = [a for c in client.call("mod_assign_get_assignments", courseids=[course_id]).get("courses", [])
               if c.get("id") == course_id for a in c.get("assignments", [])]
    root = course_root(Path(dest), course)
    manifest_path = root / MANIFEST_REL
    old = Manifest.load(manifest_path)
    items = plan_sync(course, contents, assigns, root)
    d = diff(old, items)
    fresh = set(d["new"]) | set(d["changed"])
    before = old.items if old else {}
    new_entries: dict[str, dict] = {}
    report: dict[str, Any] = {"course": root.name, "course_id": course_id, "root": str(root),
                              "manifest": str(manifest_path), "downloaded": 0, "skipped_download": 0,
                              "unchanged": 0, "errors": []}
    for item in items:
        key, target = item_key(item), root / item["rel_path"]
        if key not in fresh and key in before and target.exists():
            new_entries[key] = before[key]
            report["unchanged"] += 1
            continue
        entry = {"rel_path": item["rel_path"], "timemodified": item["timemodified"]}
        if "content" in item:
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = item["content"].encode("utf-8")
            target.write_bytes(raw)
            new_entries[key] = {**entry, "sha256": hashlib.sha256(raw).hexdigest()}
            continue
        if not download:
            report["skipped_download"] += 1
            if key in before:
                new_entries[key] = before[key]
            continue
        try:
            _, digest = client.download(item["fileurl"], target)
        except AuthError:
            raise
        except (MoodleError, TransportError, OSError) as exc:
            report["errors"].append({"rel_path": item["rel_path"], "error": strip_token(str(exc), client.token)})
            if key in before:
                new_entries[key] = before[key]
            continue
        report["downloaded"] += 1
        new_entries[key] = {**entry, "sha256": digest}
    side = {}
    for name, build in (("announcements.md", _announcements), ("grades.md", _grades)):
        try:
            text = build(client, course_id)
        except AuthError:
            raise
        except (MoodleError, TransportError) as exc:
            report["errors"].append({"rel_path": name, "error": strip_token(str(exc), client.token)})
            continue
        root.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
        side[name] = str(root / name)
    Manifest(course_id=course_id, synced_at=datetime.now(TZ).isoformat(timespec="seconds"),
             items=new_entries).save(manifest_path)
    by_key = {item_key(i): i["rel_path"] for i in items}
    report.update({
        "new": [by_key[k] for k in d["new"]],
        "changed": [by_key[k] for k in d["changed"]],
        "removed": [before[k]["rel_path"] for k in d["removed"]],
        "files": side,
        "next_step": "scan the course folder with prompt-injection-scanner before reading any file",
    })
    return report
