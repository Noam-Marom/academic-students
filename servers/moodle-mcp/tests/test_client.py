"""MoodleClient: REST call shape, PHP-style params, error mapping, allowlist, token stripping, downloads."""
from __future__ import annotations

import hashlib
import re

import pytest

httpx = pytest.importorskip("httpx")
respx = pytest.importorskip("respx")

from moodle_mcp import client as mc  # noqa: E402
from moodle_mcp.errors import AuthError, MoodleError, TransportError  # noqa: E402

from moodle_fixtures import SITE, TOKEN, load_fixture  # noqa: E402

REST = f"{SITE}/webservice/rest/server.php"


def make_client() -> "mc.MoodleClient":
    return mc.MoodleClient(SITE, TOKEN)


def form(request) -> dict[str, str]:
    """The POSTed form fields of a captured request."""
    return dict(httpx.QueryParams(request.content.decode()))


# --- encode_params -----------------------------------------------------------------------------------

def test_encode_params_arrays_php_style():
    assert mc.encode_params({"courseids": [1, 2]}) == {"courseids[0]": "1", "courseids[1]": "2"}


def test_encode_params_structs_in_arrays():
    out = mc.encode_params({"options": [{"name": "excludecontents", "value": 1}]})
    assert out == {"options[0][name]": "excludecontents", "options[0][value]": "1"}


def test_encode_params_scalars_bools_and_none():
    assert mc.encode_params({"courseid": 12, "flag": True, "off": False, "skip": None}) == {
        "courseid": "12", "flag": "1", "off": "0",
    }


# --- call --------------------------------------------------------------------------------------------

@respx.mock
def test_call_posts_to_rest_endpoint_with_json_format():
    route = respx.post(REST).mock(return_value=httpx.Response(200, json=load_fixture("site_info.json")))
    out = make_client().call("core_webservice_get_site_info")
    assert out["username"] == "student01"
    assert route.called
    fields = form(route.calls.last.request)
    assert fields["wsfunction"] == "core_webservice_get_site_info"
    assert fields["moodlewsrestformat"] == "json"
    assert fields["wstoken"] == TOKEN
    assert "token" not in str(route.calls.last.request.url)


@respx.mock
def test_call_encodes_array_params():
    route = respx.post(REST).mock(return_value=httpx.Response(200, json={"courses": []}))
    make_client().call("mod_assign_get_assignments", courseids=[12, 15])
    fields = form(route.calls.last.request)
    assert fields["courseids[0]"] == "12" and fields["courseids[1]"] == "15"


@respx.mock
def test_invalidtoken_maps_to_auth_error_with_relogin_hint():
    respx.post(REST).mock(return_value=httpx.Response(200, json=load_fixture("error_invalidtoken.json")))
    with pytest.raises(AuthError) as ei:
        make_client().call("core_webservice_get_site_info")
    assert ei.value.errorcode == "invalidtoken"
    assert "moodle-mcp login" in str(ei.value)


@respx.mock
def test_accessexception_maps_to_auth_error_not_generic_message():
    respx.post(REST).mock(return_value=httpx.Response(200, json=load_fixture("error_accessexception.json")))
    with pytest.raises(AuthError) as ei:
        make_client().call("core_webservice_get_site_info")
    assert "moodle-mcp login" in str(ei.value)
    assert "Access control exception" not in str(ei.value)


@respx.mock
def test_other_errorcode_maps_to_moodle_error():
    body = {"exception": "moodle_exception", "errorcode": "sitemaintenance", "message": "Site is under maintenance"}
    respx.post(REST).mock(return_value=httpx.Response(200, json=body))
    with pytest.raises(MoodleError) as ei:
        make_client().call("core_webservice_get_site_info")
    assert not isinstance(ei.value, AuthError)
    assert ei.value.errorcode == "sitemaintenance"
    assert ei.value.message == "Site is under maintenance"


@respx.mock
def test_http_403_maps_to_transport_error():
    respx.post(REST).mock(return_value=httpx.Response(403, text="<html>Forbidden</html>"))
    with pytest.raises(TransportError) as ei:
        make_client().call("core_webservice_get_site_info")
    assert "403" in str(ei.value)


@respx.mock
def test_non_json_200_maps_to_transport_error():
    respx.post(REST).mock(return_value=httpx.Response(200, text="<xml>not json</xml>"))
    with pytest.raises(TransportError):
        make_client().call("core_webservice_get_site_info")


@respx.mock
def test_network_failure_maps_to_transport_error():
    respx.post(REST).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(TransportError):
        make_client().call("core_webservice_get_site_info")


# --- allowlist ---------------------------------------------------------------------------------------

@respx.mock
def test_write_function_is_refused_before_any_request():
    route = respx.post(REST).mock(return_value=httpx.Response(200, json={}))
    with pytest.raises(PermissionError):
        make_client().call("mod_quiz_start_attempt", quizid=50)
    assert not route.called


def test_allowlist_contains_only_get_functions():
    # Every Moodle function that writes is named by its verb (start_attempt, save_submission, add_discussion_post,
    # mark_notification_read, …). Everything we call is a `<component>_get_<thing>` reader.
    for fn in mc.ALLOWED_FUNCTIONS:
        assert re.fullmatch(r"[a-z_]+_get_[a-z_]+", fn), fn
        assert not any(bad in fn for bad in ("start_attempt", "save_", "process_attempt", "submit",
                                              "create", "update", "delete", "add_", "send", "mark_")), fn


# --- file urls and downloads -------------------------------------------------------------------------

def test_file_url_appends_token_with_ampersand_when_query_exists():
    url = f"{SITE}/webservice/pluginfile.php/504/mod_resource/content/3/slides.pdf?forcedownload=1"
    assert make_client().file_url(url) == url + f"&token={TOKEN}"


def test_file_url_appends_token_with_question_mark_when_no_query():
    url = f"{SITE}/webservice/pluginfile.php/507/mod_assign/introattachment/0/hw1-brief.pdf"
    assert make_client().file_url(url) == url + f"?token={TOKEN}"


@respx.mock
def test_download_writes_bytes_and_returns_sha256(tmp_path):
    url = f"{SITE}/webservice/pluginfile.php/504/mod_resource/content/3/slides.pdf?forcedownload=1"
    data = b"%PDF-1.4 fake slides " * 100
    route = respx.get(url + f"&token={TOKEN}").mock(
        return_value=httpx.Response(200, content=data, headers={"content-type": "application/pdf"}))
    dest = tmp_path / "materials" / "01-week-1" / "slides.pdf"
    path, digest = make_client().download(url, dest)
    assert route.called
    assert path == dest and dest.read_bytes() == data
    assert digest == hashlib.sha256(data).hexdigest()


@respx.mock
def test_download_json_error_body_maps_to_auth_error(tmp_path):
    url = f"{SITE}/webservice/pluginfile.php/504/mod_resource/content/3/slides.pdf"
    respx.get(url + f"?token={TOKEN}").mock(
        return_value=httpx.Response(200, json=load_fixture("error_invalidtoken.json")))
    with pytest.raises(AuthError):
        make_client().download(url, tmp_path / "slides.pdf")
    assert not (tmp_path / "slides.pdf").exists()


# --- token never leaks -------------------------------------------------------------------------------

def test_strip_token_on_url():
    assert mc.strip_token(f"{SITE}/x.pdf?token={TOKEN}", TOKEN) == f"{SITE}/x.pdf?token=<token>"


def test_strip_token_with_empty_token_is_identity():
    assert mc.strip_token("hello", "") == "hello"


@respx.mock
def test_error_messages_never_contain_the_token():
    body = {"exception": "moodle_exception", "errorcode": "invalidrecord",
            "message": f"Can't find record with wstoken={TOKEN}", "debuginfo": f"token {TOKEN}"}
    respx.post(REST).mock(return_value=httpx.Response(200, json=body))
    with pytest.raises(MoodleError) as ei:
        make_client().call("core_webservice_get_site_info")
    assert TOKEN not in str(ei.value) and TOKEN not in repr(ei.value)
    assert "<token>" in str(ei.value)


@respx.mock
def test_transport_error_message_never_contains_the_token():
    respx.post(REST).mock(return_value=httpx.Response(500, text=f"server error for {TOKEN}"))
    with pytest.raises(TransportError) as ei:
        make_client().call("core_webservice_get_site_info")
    assert TOKEN not in str(ei.value)


@respx.mock
def test_download_transport_error_never_contains_the_token(tmp_path):
    url = f"{SITE}/webservice/pluginfile.php/504/mod_resource/content/3/slides.pdf"
    respx.get(url + f"?token={TOKEN}").mock(side_effect=httpx.ConnectError(f"cannot reach {url}?token={TOKEN}"))
    with pytest.raises(TransportError) as ei:
        make_client().download(url, tmp_path / "slides.pdf")
    assert TOKEN not in str(ei.value)


# --- extras used by the server -----------------------------------------------------------------------

def test_client_remembers_userid_from_credentials():
    assert mc.MoodleClient(SITE, TOKEN, userid=42).userid == 42
    assert make_client().userid is None


@respx.mock
def test_fetch_text_returns_body_and_maps_http_errors():
    url = f"{SITE}/calendar/export_execute.php?userid=42&authtoken=cal123&preset_what=all&preset_time=recentupcoming"
    respx.get(url).mock(return_value=httpx.Response(200, text="BEGIN:VCALENDAR\nEND:VCALENDAR\n"))
    assert make_client().fetch_text(url).startswith("BEGIN:VCALENDAR")
    respx.get(url).mock(return_value=httpx.Response(404, text="gone"))
    with pytest.raises(TransportError):
        make_client().fetch_text(url)


def test_fetch_text_refuses_urls_outside_the_site():
    with pytest.raises(PermissionError):
        make_client().fetch_text("https://evil.example/calendar/export_execute.php")
