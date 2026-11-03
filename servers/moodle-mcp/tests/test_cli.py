"""`moodle-mcp login|logout|status|serve`: the only place a password is ever typed, and it never gets printed."""
from __future__ import annotations

import base64
import hashlib

import pytest

httpx = pytest.importorskip("httpx")
respx = pytest.importorskip("respx")
pytest.importorskip("mcp")

from moodle_mcp import cli  # noqa: E402
from moodle_mcp.store import Store  # noqa: E402

from moodle_fixtures import PRIVATE_TOKEN, SITE, TOKEN, load_fixture  # noqa: E402

AJAX = f"{SITE}/lib/ajax/service-nologin.php"
TOKEN_PHP = f"{SITE}/login/token.php"
REST = f"{SITE}/webservice/rest/server.php"
PASSWORD = "hunter2-very-secret"


def ajax_ok(config_name: str) -> httpx.Response:
    return httpx.Response(200, json=[{"error": False, "data": load_fixture(config_name)}])


def rest_dispatch(request):
    fields = dict(httpx.QueryParams(request.content.decode()))
    if fields["wsfunction"] == "core_webservice_get_site_info":
        if fields["wstoken"] == TOKEN:
            return httpx.Response(200, json=load_fixture("site_info.json"))
        return httpx.Response(200, json=load_fixture("error_invalidtoken.json"))
    raise AssertionError(f"unexpected function {fields['wsfunction']}")


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr("moodle_mcp.store.keyring", None)
    monkeypatch.delenv("MOODLE_MCP_SITE", raising=False)
    return Store(backend="file", path=tmp_path / "credentials.json")


@pytest.fixture
def moodle():
    with respx.mock(assert_all_called=False) as router:
        router.post(REST).mock(side_effect=rest_dispatch)
        yield router


def run(argv, store, capsys, **kw) -> tuple[int, str, str]:
    kw.setdefault("getpass_fn", lambda prompt="": PASSWORD)
    kw.setdefault("input_fn", lambda prompt="": "student01")
    kw.setdefault("opener", lambda url: True)
    code = cli.main(argv, store=store, **kw)
    out = capsys.readouterr()
    return code, out.out, out.err


def assert_no_secrets(*texts: str) -> None:
    for text in texts:
        assert TOKEN not in text and PRIVATE_TOKEN not in text and PASSWORD not in text


# --- login with username / password ------------------------------------------------------------------

def test_password_login_stores_credentials_and_prints_no_secret(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_app.json"))
    moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_ok.json")))
    code, out, err = run(["login", SITE, "--username", "student01"], store, capsys)
    assert code == 0, err
    creds = store.load(SITE)
    assert creds is not None
    assert creds.token == TOKEN and creds.privatetoken == PRIVATE_TOKEN
    assert creds.userid == 42 and creds.username == "student01" and creds.site == SITE and creds.created
    assert "student01" in out and "Example University Moodle" in out
    assert_no_secrets(out, err)


def test_password_login_asks_for_username_when_missing(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_app.json"))
    route = moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_ok.json")))
    code, out, err = run(["login", SITE], store, capsys, input_fn=lambda prompt="": "  Student01 ")
    assert code == 0, err
    fields = dict(httpx.QueryParams(route.calls.last.request.content.decode()))
    assert fields["username"] == "student01" and fields["password"] == PASSWORD


def test_password_login_adds_https_and_strips_trailing_slash(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_app.json"))
    moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_ok.json")))
    code, out, err = run(["login", "moodle.example.ac.il/", "--username", "student01"], store, capsys)
    assert code == 0, err
    assert store.load(SITE).site == SITE


def test_invalid_login_exits_1_stores_nothing_prints_no_secret(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_app.json"))
    moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_bad.json")))
    code, out, err = run(["login", SITE, "--username", "student01"], store, capsys)
    assert code == 1
    assert "Invalid login" in err
    assert store.load(SITE) is None and store.list_sites() == []
    assert_no_secrets(out, err)


def test_unreachable_public_config_falls_back_to_password_login(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=httpx.Response(500, text="boom"))
    moodle.get(AJAX).mock(return_value=httpx.Response(500, text="boom"))
    moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_ok.json")))
    code, out, err = run(["login", SITE, "--username", "student01"], store, capsys)
    assert code == 0, err
    assert "config" in err.lower()
    assert store.load(SITE).token == TOKEN
    assert_no_secrets(out, err)


def test_token_rejected_by_site_info_exits_1_and_stores_nothing(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_app.json"))
    moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json={"token": "deadbeef" * 4, "privatetoken": None}))
    code, out, err = run(["login", SITE, "--username", "student01"], store, capsys)
    assert code == 1 and store.load(SITE) is None
    assert "deadbeef" not in out + err


# --- browser flow ------------------------------------------------------------------------------------

def browser_payload(passport: str) -> str:
    plain = hashlib.md5((SITE + passport).encode()).hexdigest() + ":::" + TOKEN + ":::" + PRIVATE_TOKEN
    return "academicstudents://token=" + base64.b64encode(plain.encode()).decode()


def test_typeoflogin_2_picks_browser_flow_and_never_asks_for_a_password(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_browser.json"))
    token_route = moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_ok.json")))
    opened: list[str] = []

    def opener(url: str) -> bool:
        opened.append(url)
        return True

    def input_fn(prompt: str = "") -> str:
        passport = httpx.URL(opened[-1]).params["passport"]
        return browser_payload(passport)

    def getpass_fn(prompt: str = "") -> str:
        raise AssertionError("the browser flow must not ask for a password")

    code, out, err = run(["login", SITE], store, capsys, opener=opener, input_fn=input_fn, getpass_fn=getpass_fn)
    assert code == 0, err
    assert not token_route.called
    assert "launch.php" in opened[0] and "confirmed=1" in opened[0]
    assert store.load(SITE).token == TOKEN and store.load(SITE).privatetoken == PRIVATE_TOKEN
    assert_no_secrets(out, err)


def test_browser_flag_forces_browser_flow(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_app.json"))
    opened: list[str] = []

    def input_fn(prompt: str = "") -> str:
        return browser_payload(httpx.URL(opened[-1]).params["passport"])

    code, out, err = run(["login", SITE, "--browser"], store, capsys, opener=opened.append, input_fn=input_fn)
    assert code == 0, err
    assert opened and store.load(SITE).token == TOKEN


def test_browser_flow_wrong_signature_exits_1(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_browser.json"))
    code, out, err = run(["login", SITE], store, capsys, opener=lambda url: True,
                         input_fn=lambda prompt="": browser_payload("not-the-passport"))
    assert code == 1 and "signature" in err.lower()
    assert store.load(SITE) is None
    assert_no_secrets(out, err)


# --- logout / status / serve -------------------------------------------------------------------------

def test_logout_removes_credentials(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_app.json"))
    moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_ok.json")))
    assert run(["login", SITE, "--username", "student01"], store, capsys)[0] == 0
    code, out, err = run(["logout", SITE], store, capsys)
    assert code == 0 and store.load(SITE) is None
    assert "moodle.example.ac.il" in out


def test_status_lists_sites_and_token_validity_without_secrets(moodle, store, capsys):
    moodle.post(AJAX).mock(return_value=ajax_ok("public_config_app.json"))
    moodle.post(TOKEN_PHP).mock(return_value=httpx.Response(200, json=load_fixture("token_ok.json")))
    assert run(["login", SITE, "--username", "student01"], store, capsys)[0] == 0
    code, out, err = run(["status"], store, capsys)
    assert code == 0
    assert "moodle.example.ac.il" in out and "student01" in out and "valid" in out.lower()
    assert_no_secrets(out, err)


def test_status_without_login_exits_1_with_instructions(store, capsys):
    code, out, err = run(["status"], store, capsys)
    assert code == 1
    assert "moodle-mcp login" in out + err


def test_serve_is_the_default_command(store, capsys):
    calls: list[int] = []
    assert cli.main([], store=store, serve_fn=lambda: calls.append(1) or 0) == 0
    assert cli.main(["serve"], store=store, serve_fn=lambda: calls.append(1) or 0) == 0
    assert calls == [1, 1]


def test_cli_module_never_imports_the_mcp_server_eagerly():
    # `moodle-mcp login` must work (and fail clearly) even when the MCP stack is unimportable
    src = (cli.__file__ and open(cli.__file__, encoding="utf-8").read()) or ""
    assert "from .server import" not in src.split("def ")[0], "import the server lazily inside serve()"


def test_help_mentions_that_the_password_is_typed_here_only(capsys):
    with pytest.raises(SystemExit):
        cli.main(["login", "--help"])
    out = capsys.readouterr().out
    assert "password" in out.lower() and "never" in out.lower()
