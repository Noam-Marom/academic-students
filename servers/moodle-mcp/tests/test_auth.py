"""Token acquisition: public config, username/password at login/token.php, and the paste-back launch flow."""
from __future__ import annotations

import base64
import hashlib
import json
from urllib.parse import quote

import pytest

httpx = pytest.importorskip("httpx")
respx = pytest.importorskip("respx")

from moodle_mcp import auth  # noqa: E402
from moodle_mcp.errors import AuthError, TransportError  # noqa: E402

from conftest import PRIVATE_TOKEN, SITE, TOKEN, load_fixture  # noqa: E402

AJAX = f"{SITE}/lib/ajax/service-nologin.php"
TOKEN_PHP = f"{SITE}/login/token.php"
PASSPORT = "123.456789"


def payload(signature_site: str = SITE, passport: str = PASSPORT, private: str | None = PRIVATE_TOKEN) -> str:
    plain = hashlib.md5((signature_site.rstrip("/") + passport).encode()).hexdigest() + ":::" + TOKEN
    if private is not None:
        plain += ":::" + private
    return base64.b64encode(plain.encode()).decode()


# --- public config -----------------------------------------------------------------------------------

@respx.mock
def test_get_public_config_posts_ajax_nologin_call():
    route = respx.post(AJAX).mock(return_value=httpx.Response(
        200, json=[{"error": False, "data": load_fixture("public_config_app.json")}]))
    cfg = auth.get_public_config(SITE, httpx.Client())
    assert cfg["typeoflogin"] == 1 and cfg["wwwroot"] == SITE
    req = route.calls.last.request
    assert req.url.params["info"] == "tool_mobile_get_public_config"
    assert json.loads(req.content) == [{"index": 0, "methodname": "tool_mobile_get_public_config", "args": {}}]


@respx.mock
def test_get_public_config_falls_back_to_get_form():
    respx.post(AJAX).mock(return_value=httpx.Response(404, text="not here"))
    route = respx.get(AJAX).mock(return_value=httpx.Response(
        200, json=[{"error": False, "data": load_fixture("public_config_browser.json")}]))
    cfg = auth.get_public_config(SITE, httpx.Client())
    assert cfg["typeoflogin"] == 2 and cfg["identityproviders"][0]["name"] == "University SSO"
    params = route.calls.last.request.url.params
    assert params["info"] == "tool_mobile_get_public_config"
    assert json.loads(params["args"])[0]["methodname"] == "tool_mobile_get_public_config"


@respx.mock
def test_get_public_config_ajax_error_or_garbage_is_transport_error():
    respx.post(AJAX).mock(return_value=httpx.Response(
        200, json=[{"error": True, "exception": {"errorcode": "invalidparameter", "message": "bad"}}]))
    respx.get(AJAX).mock(return_value=httpx.Response(200, text="<html>login page</html>"))
    with pytest.raises(TransportError):
        auth.get_public_config(SITE, httpx.Client())


def test_wants_browser_login_decision():
    assert auth.wants_browser_login(load_fixture("public_config_app.json")) is False
    assert auth.wants_browser_login(load_fixture("public_config_browser.json")) is True
    assert auth.wants_browser_login({"typeoflogin": 3}) is True
    assert auth.wants_browser_login({"typeoflogin": 1, "identityproviders": [{"name": "SSO"}]}) is True
    assert auth.wants_browser_login({}) is False


# --- username / password -----------------------------------------------------------------------------

@respx.mock
def test_login_with_password_posts_once_and_returns_tokens():
    route = respx.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_ok.json")))
    out = auth.login_with_password(SITE, "student01", "hunter2", httpx.Client())
    assert out == {"token": TOKEN, "privatetoken": PRIVATE_TOKEN}
    assert route.call_count == 1
    fields = dict(httpx.QueryParams(route.calls.last.request.content.decode()))
    assert fields == {"username": "student01", "password": "hunter2", "service": "moodle_mobile_app"}
    assert "password" not in str(route.calls.last.request.url)


@respx.mock
def test_login_with_password_invalidlogin_is_auth_error_without_the_password():
    respx.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_bad.json")))
    with pytest.raises(AuthError) as ei:
        auth.login_with_password(SITE, "student01", "hunter2", httpx.Client())
    assert ei.value.errorcode == "invalidlogin"
    assert "Invalid login" in str(ei.value) and "hunter2" not in str(ei.value)


@respx.mock
def test_login_with_password_other_errorcode_and_http_errors():
    respx.post(TOKEN_PHP).mock(return_value=httpx.Response(
        200, json={"error": "Web services are not enabled", "errorcode": "enablewsdescription"}))
    with pytest.raises(AuthError) as ei:
        auth.login_with_password(SITE, "u", "p", httpx.Client())
    assert ei.value.errorcode == "enablewsdescription"
    respx.post(TOKEN_PHP).mock(return_value=httpx.Response(500, text="oops p"))
    with pytest.raises(TransportError):
        auth.login_with_password(SITE, "u", "p", httpx.Client())


@respx.mock
def test_login_with_password_non_json_is_transport_error():
    respx.post(TOKEN_PHP).mock(return_value=httpx.Response(200, text="<html>SSO redirect</html>"))
    with pytest.raises(TransportError):
        auth.login_with_password(SITE, "u", "p", httpx.Client())


# --- launch (browser) flow ---------------------------------------------------------------------------

def test_build_launch_url_has_the_four_params_and_a_plain_urlscheme():
    url = auth.build_launch_url(SITE + "/", PASSPORT)
    assert url.startswith(f"{SITE}/admin/tool/mobile/launch.php?")
    params = httpx.URL(url).params
    assert params["service"] == "moodle_mobile_app" and params["passport"] == PASSPORT
    assert params["urlscheme"] == "academicstudents" and params["confirmed"] == "1"
    assert "://" not in params["urlscheme"]


def test_new_passport_is_a_random_float_string():
    a, b = auth.new_passport(), auth.new_passport()
    assert a != b
    float(a)


def test_parse_launch_payload_from_full_link():
    out = auth.parse_launch_payload(f"academicstudents://token={payload()}", SITE, PASSPORT)
    assert out == {"token": TOKEN, "privatetoken": PRIVATE_TOKEN}


def test_parse_launch_payload_from_bare_base64_and_urlencoded():
    assert auth.parse_launch_payload(payload(), SITE, PASSPORT)["token"] == TOKEN
    assert auth.parse_launch_payload(f"academicstudents://token={quote(payload())}", SITE, PASSPORT)["token"] == TOKEN


def test_parse_launch_payload_without_privatetoken():
    out = auth.parse_launch_payload(payload(private=None), SITE, PASSPORT)
    assert out == {"token": TOKEN, "privatetoken": None}


def test_parse_launch_payload_accepts_http_https_swap_like_the_official_app():
    http_site = SITE.replace("https://", "http://")
    assert auth.parse_launch_payload(payload(signature_site=http_site), SITE, PASSPORT)["token"] == TOKEN


def test_parse_launch_payload_rejects_wrong_signature():
    with pytest.raises(AuthError, match="signature mismatch"):
        auth.parse_launch_payload(payload(passport="999.1"), SITE, PASSPORT)
    with pytest.raises(AuthError, match="signature mismatch"):
        auth.parse_launch_payload(payload(signature_site="https://evil.example"), SITE, PASSPORT)


def test_parse_launch_payload_rejects_malformed_input():
    for bad in ("academicstudents://token=%%%notbase64%%%", "academicstudents://token=",
                base64.b64encode(b"no separators").decode(), "", "https://moodle.example.ac.il/"):
        with pytest.raises(AuthError):
            auth.parse_launch_payload(bad, SITE, PASSPORT)


def test_login_via_browser_opens_launch_url_and_reads_pasted_link(capsys):
    opened: list[str] = []

    def reader(prompt: str) -> str:
        return f"academicstudents://token={payload()}"

    out = auth.login_via_browser(SITE, httpx.Client(), opener=opened.append, reader=reader, passport=PASSPORT)
    assert out == {"token": TOKEN, "privatetoken": PRIVATE_TOKEN}
    [url] = opened
    assert httpx.URL(url).params["passport"] == PASSPORT
    captured = capsys.readouterr()
    assert TOKEN not in captured.out + captured.err and PRIVATE_TOKEN not in captured.out + captured.err


def test_login_via_browser_prints_url_when_no_browser_opens(capsys):
    def reader(prompt: str) -> str:
        return f"academicstudents://token={payload()}"

    auth.login_via_browser(SITE, httpx.Client(), opener=lambda url: False, reader=reader, passport=PASSPORT)
    assert "launch.php" in capsys.readouterr().out
