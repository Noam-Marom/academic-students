"""The MCP tools, called as plain functions against respx-mocked Moodle answers.

`build_server(client_factory=...)` returns the FastMCP server; its `.tools` dict holds the registered functions so
they can be exercised without the MCP transport. One test goes through the MCP layer to prove registration.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time

import pytest

httpx = pytest.importorskip("httpx")
respx = pytest.importorskip("respx")
pytest.importorskip("mcp")

from moodle_mcp import client as mc  # noqa: E402
from moodle_mcp import server as srv  # noqa: E402
from moodle_mcp.store import Store  # noqa: E402

from conftest import SITE, TOKEN, load_fixture  # noqa: E402

REST = f"{SITE}/webservice/rest/server.php"
CAL_TOKEN = "cal0123456789abcdef0123456789abcdef01234567"

EXPECTED_ALLOWLIST = frozenset({
    "core_webservice_get_site_info", "core_enrol_get_users_courses", "core_course_get_contents",
    "mod_assign_get_assignments", "core_calendar_get_action_events_by_timesort",
    "core_calendar_get_calendar_upcoming_view", "core_calendar_get_calendar_export_token",
    "gradereport_user_get_grade_items", "mod_forum_get_forums_by_courses", "mod_forum_get_forum_discussions",
    "mod_forum_get_discussion_posts", "message_popup_get_popup_notifications", "mod_quiz_get_quizzes_by_courses",
    "tool_mobile_get_public_config",
})

TOOL_NAMES = {
    "moodle_status", "list_courses", "get_course_contents", "list_assignments", "get_upcoming_events",
    "get_grades", "list_forum_discussions", "get_notifications", "list_quizzes", "download_file",
    "export_calendar_ics", "sync_course",
}


class FakeMoodle:
    """Answers REST calls from fixtures, keyed by wsfunction; records every call's form fields."""

    def __init__(self):
        self.calls: list[dict[str, str]] = []
        self.responses = {
            "core_webservice_get_site_info": load_fixture("site_info.json"),
            "core_enrol_get_users_courses": load_fixture("courses.json"),
            "core_course_get_contents": load_fixture("course_contents.json"),
            "mod_assign_get_assignments": load_fixture("assignments.json"),
            "core_calendar_get_action_events_by_timesort": load_fixture("action_events.json"),
            "gradereport_user_get_grade_items": load_fixture("grades.json"),
            "mod_forum_get_forums_by_courses": load_fixture("forums.json"),
            "mod_forum_get_forum_discussions": self._discussions,
            "message_popup_get_popup_notifications": load_fixture("notifications.json"),
            "mod_quiz_get_quizzes_by_courses": load_fixture("quizzes.json"),
            "core_calendar_get_calendar_export_token": {"token": CAL_TOKEN, "warnings": []},
        }

    @staticmethod
    def _discussions(fields):
        if fields["forumid"] == "7":
            return load_fixture("discussions.json")
        return {"discussions": [], "warnings": []}

    def __call__(self, request):
        fields = dict(httpx.QueryParams(request.content.decode()))
        self.calls.append(fields)
        body = self.responses[fields["wsfunction"]]
        if callable(body):
            body = body(fields)
        return httpx.Response(200, json=body)

    def of(self, wsfunction: str) -> list[dict[str, str]]:
        return [c for c in self.calls if c["wsfunction"] == wsfunction]


@pytest.fixture
def moodle():
    with respx.mock(assert_all_called=False) as router:
        fake = FakeMoodle()
        router.post(REST).mock(side_effect=fake)
        fake.router = router
        yield fake


@pytest.fixture
def tools(moodle):
    server = srv.build_server(client_factory=lambda: mc.MoodleClient(SITE, TOKEN, userid=42))
    return server.tools


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


# --- registration and allowlist ----------------------------------------------------------------------

def test_allowlist_is_exactly_the_pinned_set():
    assert mc.ALLOWED_FUNCTIONS == EXPECTED_ALLOWLIST


def test_tools_are_registered_with_the_mcp_server(moodle):
    server = srv.build_server(client_factory=lambda: mc.MoodleClient(SITE, TOKEN, userid=42))
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert TOOL_NAMES <= names
    assert set(server.tools) == names


def test_call_through_the_mcp_layer_returns_course_shortnames(moodle):
    server = srv.build_server(client_factory=lambda: mc.MoodleClient(SITE, TOKEN, userid=42))
    result = asyncio.run(server.call_tool("list_courses", {}))
    # mcp 1.x returns content blocks / a (content, structured) tuple; mcp 2.x a pydantic CallToolResult
    text = result.model_dump_json() if hasattr(result, "model_dump_json") else json.dumps(result, default=str)
    assert "OS-2026A" in text and "ALGO-2026A" in text
    assert TOKEN not in text


# --- status -------------------------------------------------------------------------------------------

def test_moodle_status_logged_in(tools):
    out = tools["moodle_status"]()
    assert out["logged_in"] is True and out["token_valid"] is True
    assert out["username"] == "student01" and out["userid"] == 42
    assert out["site"] == SITE and out["downloadfiles"] is True
    assert TOKEN not in dumps(out)


def test_moodle_status_without_credentials_is_calm(tmp_path, monkeypatch):
    monkeypatch.setattr("moodle_mcp.store.keyring", None)
    monkeypatch.delenv("MOODLE_MCP_SITE", raising=False)
    server = srv.build_server(store=Store(backend="file", path=tmp_path / "credentials.json"))
    out = server.tools["moodle_status"]()
    assert out["logged_in"] is False
    assert out["how_to_login"] == srv.HOW_TO_LOGIN
    assert "password is typed there, never here" in out["how_to_login"]


def test_moodle_status_with_dead_token_reports_auth(moodle, tools):
    moodle.responses["core_webservice_get_site_info"] = load_fixture("error_accessexception.json")
    out = tools["moodle_status"]()
    assert out["logged_in"] is False and out["token_valid"] is False
    assert out["error"] == "auth" and out["how_to_login"] == srv.HOW_TO_LOGIN
    assert "Access control exception" not in dumps(out)


# --- courses and contents ----------------------------------------------------------------------------

def test_list_courses_shape(tools, moodle):
    out = tools["list_courses"]()
    assert [c["id"] for c in out] == [12, 15]
    os_course = out[0]
    assert os_course["shortname"] == "OS-2026A" and os_course["fullname"] == "Operating Systems"
    # 2026-10-25 is the Sunday Israel leaves DST: midnight is still +03:00
    assert os_course["start"] == "2026-10-25T00:00:00+03:00" and os_course["start_ts"] == 1792875600
    assert os_course["end"].startswith("2027-02-15")
    assert os_course["url"] == f"{SITE}/course/view.php?id=12"
    assert os_course["hidden"] is False
    assert moodle.of("core_enrol_get_users_courses")[0]["userid"] == "42"


def test_get_course_contents_files_have_urls_without_token(tools):
    out = tools["get_course_contents"](12)
    assert out["course_id"] == 12
    sections = out["sections"]
    assert [s["name"] for s in sections] == ["General", "Week 1 - Processes", "Week 2 - Threads"]
    modules = {m["id"]: m for s in sections for m in s["modules"]}
    slides = modules[1004]
    assert slides["type"] == "resource"
    assert sorted(f["filename"] for f in slides["files"]) == ["slides-handout.pdf", "slides.pdf"]
    for f in slides["files"]:
        assert f["url"].startswith(f"{SITE}/webservice/pluginfile.php/") and "token" not in f["url"]
        assert f["modified"] == "2026-10-28T14:30:00+02:00" and f["modified_ts"] == 1793190600
    label = modules[1003]
    assert label["type"] == "label" and label["files"] == []
    assert label["description"].startswith("Office hours")
    link = modules[1006]
    assert link["type"] == "url" and link["links"] == [
        {"name": "OSTEP - Processes chapter", "url": "https://pages.cs.wisc.edu/~remzi/OSTEP/cpu-intro.pdf"}]
    assert out["file_count"] == 6
    assert TOKEN not in dumps(out)


# --- assignments, events, grades ---------------------------------------------------------------------

def test_list_assignments_is_flat_with_iso_dates_and_markdown_intro(tools, moodle):
    out = tools["list_assignments"]([12])
    assert moodle.of("mod_assign_get_assignments")[0]["courseids[0]"] == "12"
    assert [a["name"] for a in out] == ["Homework 1 - Processes", "Homework 2 - Threads"]
    hw1 = out[0]
    assert hw1["course_id"] == 12 and hw1["course"] == "OS-2026A" and hw1["cmid"] == 1007
    assert hw1["due"] == "2026-11-20T23:55:00+02:00" and hw1["due_ts"] == 1795211700
    assert hw1["cutoff"] is None
    assert "**shell**" in hw1["intro"] and "- Use `fork` and `exec`." in hw1["intro"]
    assert "<" not in hw1["intro"]
    [att] = hw1["attachments"]
    assert att["filename"] == "hw1-brief.pdf" and "token" not in att["url"]
    assert hw1["url"] == f"{SITE}/mod/assign/view.php?id=1007"
    assert out[1]["team_submission"] is True and out[1]["cutoff"] is not None


def test_list_assignments_without_course_ids_asks_for_all(tools, moodle):
    tools["list_assignments"]()
    fields = moodle.of("mod_assign_get_assignments")[0]
    assert not any(k.startswith("courseids") for k in fields)


def test_get_upcoming_events_window_and_shape(tools, moodle):
    before = int(time.time())
    out = tools["get_upcoming_events"](7)
    fields = moodle.of("core_calendar_get_action_events_by_timesort")[0]
    start, end = int(fields["timesortfrom"]), int(fields["timesortto"])
    assert before - 5 <= start <= before + 5
    assert end - start == 7 * 86400
    assert [e["id"] for e in out] == [7001, 7002]
    quiz_close = out[0]
    assert quiz_close["type"] == "close" and quiz_close["module"] == "quiz"
    assert quiz_close["course_id"] == 12 and quiz_close["course"] == "OS-2026A"
    assert quiz_close["time"] == "2026-11-17T23:59:00+02:00" and quiz_close["time_ts"] == 1794952740
    assert quiz_close["url"] == f"{SITE}/mod/quiz/view.php?id=1010"
    assert out[1]["action"] == "Add submission"


def test_get_grades_items(tools, moodle):
    out = tools["get_grades"](12)
    assert moodle.of("gradereport_user_get_grade_items")[0]["userid"] == "42"
    assert out["course_id"] == 12
    items = out["items"]
    assert [i["name"] for i in items] == ["Homework 1 - Processes", "Quiz 1 - Processes", "Course total"]
    hw = items[0]
    assert hw["grade"] == "88.00" and hw["raw"] == 88 and hw["max"] == 100
    assert hw["percentage"] == "88.00 %" and hw["weight"] == "30.00 %"
    assert hw["feedback"] == "Good handling of zombie processes."
    assert hw["graded"] == "2026-11-02T12:00:00+02:00"
    assert items[1]["grade"] == "-" and items[1]["raw"] is None
    assert items[2]["type"] == "course"


# --- forums, notifications, quizzes ------------------------------------------------------------------

def test_list_forum_discussions_text_only_newest_first(tools, moodle):
    out = tools["list_forum_discussions"](12)
    assert sorted(c["forumid"] for c in moodle.of("mod_forum_get_forum_discussions")) == ["7", "8"]
    assert [d["subject"] for d in out] == ["Homework 1 published", "Welcome to Operating Systems"]
    first = out[0]
    assert first["forum"] == "Announcements" and first["forum_type"] == "news"
    assert first["author"] == "Course Lecturer"
    assert first["created"] == "2026-11-01T18:30:00+02:00"
    assert "<" not in first["message"] and "**20/11**" in first["message"]
    assert first["url"] == f"{SITE}/mod/forum/discuss.php?d=71"
    assert out[1]["pinned"] is True


def test_list_forum_discussions_limit(tools):
    assert len(tools["list_forum_discussions"](12, 1)) == 1


def test_get_notifications(tools, moodle):
    out = tools["get_notifications"](5)
    fields = moodle.of("message_popup_get_popup_notifications")[0]
    assert fields["limit"] == "5" and fields["useridto"] == "0" and fields["newestfirst"] == "1"
    assert out["unread"] == 1
    assert [n["id"] for n in out["notifications"]] == [9001, 9000]
    n = out["notifications"][0]
    assert n["read"] is False and n["subject"].startswith("Operating Systems")
    assert "<" not in n["text"] and "Homework 1 is up" in n["text"]
    assert n["created"] == "2026-11-02T09:00:00+02:00"
    assert n["url"] == f"{SITE}/mod/forum/discuss.php?d=71"


def test_list_quizzes_is_metadata_only(tools, moodle):
    out = tools["list_quizzes"](12)
    assert moodle.of("mod_quiz_get_quizzes_by_courses")[0]["courseids[0]"] == "12"
    [quiz] = out
    assert quiz["name"] == "Quiz 1 - Processes" and quiz["cmid"] == 1010
    assert quiz["opens"] == "2026-11-10T08:00:00+02:00" and quiz["closes"] == "2026-11-17T23:59:00+02:00"
    assert quiz["time_limit_minutes"] == 30 and quiz["max_attempts"] == 1 and quiz["grade"] == 10
    assert quiz["url"] == f"{SITE}/mod/quiz/view.php?id=1010"
    for key in quiz:
        assert not key.startswith("attempt"), key
        assert key not in {"questions", "answers", "layout", "state", "attemptid"}, key


# --- errors surface as data --------------------------------------------------------------------------

def test_auth_error_surfaces_as_auth_dict(tools, moodle):
    moodle.responses["core_enrol_get_users_courses"] = load_fixture("error_accessexception.json")
    out = tools["list_courses"]()
    assert out["error"] == "auth" and out["how_to_login"] == srv.HOW_TO_LOGIN
    assert "Access control exception" not in dumps(out) and TOKEN not in dumps(out)


def test_moodle_error_surfaces_as_dict(tools, moodle):
    moodle.responses["core_course_get_contents"] = {
        "exception": "moodle_exception", "errorcode": "invalidrecord", "message": "Can't find course"}
    out = tools["get_course_contents"](999)
    assert out["error"] == "moodle" and out["errorcode"] == "invalidrecord" and "Can't find course" in out["message"]


def test_transport_error_surfaces_as_dict(moodle):
    moodle.router.post(REST).mock(return_value=httpx.Response(403, text="REST disabled"))
    server = srv.build_server(client_factory=lambda: mc.MoodleClient(SITE, TOKEN, userid=42))
    out = server.tools["list_courses"]()
    assert out["error"] == "transport" and "403" in out["message"]


def test_not_logged_in_surfaces_as_dict_for_every_tool(tmp_path, monkeypatch):
    monkeypatch.setattr("moodle_mcp.store.keyring", None)
    monkeypatch.delenv("MOODLE_MCP_SITE", raising=False)
    server = srv.build_server(store=Store(backend="file", path=tmp_path / "credentials.json"))
    out = server.tools["list_courses"]()
    assert out["error"] == "not_logged_in" and out["how_to_login"] == srv.HOW_TO_LOGIN


# --- files --------------------------------------------------------------------------------------------

def test_download_file_saves_into_dest_dir_and_returns_sha256(tools, moodle, tmp_path):
    url = f"{SITE}/webservice/pluginfile.php/504/mod_resource/content/3/slides.pdf?forcedownload=1"
    data = b"%PDF-1.4 slides"
    moodle.router.get(url + f"&token={TOKEN}").mock(
        return_value=httpx.Response(200, content=data, headers={"content-type": "application/pdf"}))
    out = tools["download_file"](url, str(tmp_path / "dl"))
    assert out["path"] == str(tmp_path / "dl" / "slides.pdf")
    assert out["sha256"] == hashlib.sha256(data).hexdigest() and out["size"] == len(data)
    assert (tmp_path / "dl" / "slides.pdf").read_bytes() == data
    assert TOKEN not in dumps(out)


def test_download_file_refuses_urls_outside_the_site(tools, moodle, tmp_path):
    out = tools["download_file"]("https://evil.example/webservice/pluginfile.php/1/x.pdf", str(tmp_path))
    assert out["error"] == "forbidden"
    assert not any(c for c in moodle.router.calls)
    assert list(tmp_path.iterdir()) == []


def test_download_file_dead_token_surfaces_as_auth(tools, moodle, tmp_path):
    url = f"{SITE}/webservice/pluginfile.php/504/mod_resource/content/3/slides.pdf"
    moodle.router.get(url + f"?token={TOKEN}").mock(
        return_value=httpx.Response(200, json=load_fixture("error_invalidtoken.json")))
    out = tools["download_file"](url, str(tmp_path))
    assert out["error"] == "auth" and out["how_to_login"] == srv.HOW_TO_LOGIN


# --- calendar export ---------------------------------------------------------------------------------

ICS = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nSUMMARY:HW1\r\nEND:VEVENT\r\nBEGIN:VEVENT\r\nSUMMARY:Quiz\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"


def test_export_calendar_ics_writes_file(tools, moodle, tmp_path):
    route = moodle.router.get(url__startswith=f"{SITE}/calendar/export_execute.php").mock(
        return_value=httpx.Response(200, text=ICS, headers={"content-type": "text/calendar"}))
    dest = tmp_path / "cal" / "moodle.ics"
    out = tools["export_calendar_ics"](str(dest))
    assert out["path"] == str(dest) and out["events"] == 2
    assert dest.read_bytes() == ICS.encode("utf-8")  # CRLF preserved
    params = dict(route.calls.last.request.url.params)
    assert params["authtoken"] == CAL_TOKEN and params["userid"] == "42"
    assert params["preset_what"] == "all" and params["preset_time"] == "recentupcoming"
    assert TOKEN not in dumps(out) and TOKEN not in str(route.calls.last.request.url)


def test_export_calendar_ics_rejects_non_ics_body(tools, moodle, tmp_path):
    moodle.router.get(url__startswith=f"{SITE}/calendar/export_execute.php").mock(
        return_value=httpx.Response(200, text="Invalid authentication"))
    dest = tmp_path / "moodle.ics"
    out = tools["export_calendar_ics"](str(dest))
    assert out["error"] == "export" and "Invalid authentication" in out["message"]
    assert not dest.exists()


# --- the token never appears in any tool result -------------------------------------------------------

def test_no_tool_result_contains_the_token(tools, moodle, tmp_path):
    moodle.router.get(url__startswith=f"{SITE}/calendar/export_execute.php").mock(
        return_value=httpx.Response(200, text=ICS))
    url = f"{SITE}/webservice/pluginfile.php/504/mod_resource/content/3/slides.pdf?forcedownload=1"
    moodle.router.get(url + f"&token={TOKEN}").mock(return_value=httpx.Response(200, content=b"x"))
    calls = {
        "moodle_status": (), "list_courses": (), "get_course_contents": (12,), "list_assignments": ([12],),
        "get_upcoming_events": (30,), "get_grades": (12,), "list_forum_discussions": (12, 20),
        "get_notifications": (20,), "list_quizzes": (12,), "download_file": (url, str(tmp_path)),
        "export_calendar_ics": (str(tmp_path / "c.ics"),),
        "sync_course": (12, str(tmp_path / "courses")),
    }
    moodle.router.get(url__startswith=f"{SITE}/webservice/pluginfile.php").mock(
        return_value=httpx.Response(200, content=b"file", headers={"content-type": "application/pdf"}))
    assert set(calls) == TOOL_NAMES
    for name, args in calls.items():
        out = tools[name](*args)
        assert TOKEN not in dumps(out), name
        assert "error" not in out if isinstance(out, dict) else True, (name, out)


# --- sync_course ---------------------------------------------------------------------------------------

def test_sync_course_tool_mirrors_the_course_and_reports(tools, moodle, tmp_path):
    moodle.router.get(url__startswith=f"{SITE}/webservice/pluginfile.php").mock(
        return_value=httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"}))
    out = tools["sync_course"](12, str(tmp_path))
    root = tmp_path / "OS-2026A"
    assert out["root"] == str(root) and out["downloaded"] == 7 and out["errors"] == []
    assert (root / ".moodle-sync/manifest.json").exists() and (root / "announcements.md").exists()
    assert "materials/01-week-1-processes/slides.pdf" in out["new"]
    assert TOKEN not in dumps(out)
    again = tools["sync_course"](12, str(tmp_path))
    assert again["new"] == [] and again["downloaded"] == 0
