"""Credential store: keychain first, 0600 file fallback, host normalisation; the token never lands in a file
when the keychain works."""
from __future__ import annotations

import json
import os
import stat
import sys
import types

import pytest

from moodle_mcp import store as st  # noqa: E402

from conftest import PRIVATE_TOKEN, SITE, TOKEN  # noqa: E402

POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")


def creds(site: str = SITE) -> "st.Credentials":
    return st.Credentials(site=site, token=TOKEN, privatetoken=PRIVATE_TOKEN, userid=42,
                          username="student01", created="2026-11-02T20:00:00+02:00")


class FakeNoKeyringError(Exception):
    pass


class FakePasswordDeleteError(Exception):
    pass


def fake_keyring(*, broken: bool = False) -> types.SimpleNamespace:
    """A stand-in for the `keyring` module: an in-memory dict, or one that raises NoKeyringError."""
    vault: dict[tuple[str, str], str] = {}

    def set_password(service, username, secret):
        if broken:
            raise FakeNoKeyringError("No recommended backend was available")
        vault[(service, username)] = secret

    def get_password(service, username):
        if broken:
            raise FakeNoKeyringError("No recommended backend was available")
        return vault.get((service, username))

    def delete_password(service, username):
        if broken:
            raise FakeNoKeyringError("No recommended backend was available")
        if (service, username) not in vault:
            raise FakePasswordDeleteError(username)
        del vault[(service, username)]

    errors = types.SimpleNamespace(NoKeyringError=FakeNoKeyringError, PasswordDeleteError=FakePasswordDeleteError)
    return types.SimpleNamespace(set_password=set_password, get_password=get_password,
                                 delete_password=delete_password, errors=errors, vault=vault)


def files_under(root) -> list[str]:
    return [str(p) for p in root.rglob("*") if p.is_file()]


# --- host normalisation ------------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "https://moodle.bgu.ac.il/", "https://moodle.bgu.ac.il", "HTTPS://Moodle.BGU.ac.il/moodle/",
    "moodle.bgu.ac.il", "http://moodle.bgu.ac.il/login/index.php",
])
def test_site_host_normalises_to_bare_lowercase_host(raw):
    assert st.site_host(raw) == "moodle.bgu.ac.il"


def test_site_host_keeps_a_non_default_port():
    assert st.site_host("https://moodle.example.ac.il:8443/") == "moodle.example.ac.il:8443"


# --- keyring backend ---------------------------------------------------------------------------------

def test_keyring_save_uses_service_and_host_and_json_secret(monkeypatch, tmp_path):
    fake = fake_keyring()
    monkeypatch.setattr(st, "keyring", fake)
    store = st.Store(path=tmp_path / "credentials.json")
    store.save(creds())
    [(service, username)] = fake.vault.keys()
    assert service == "moodle-mcp" and username == "moodle.example.ac.il"
    secret = json.loads(fake.vault[(service, username)])
    assert secret["token"] == TOKEN and secret["privatetoken"] == PRIVATE_TOKEN
    assert secret["userid"] == 42 and secret["username"] == "student01" and secret["created"]
    # nothing secret on disk when the keychain works
    for f in files_under(tmp_path):
        assert TOKEN not in open(f, encoding="utf-8").read(), f


def test_keyring_roundtrip_load_by_url_or_host(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "keyring", fake_keyring())
    store = st.Store(path=tmp_path / "credentials.json")
    store.save(creds())
    assert store.load(SITE) == creds()
    assert store.load("moodle.example.ac.il") == creds()
    assert store.load("https://other.example.ac.il") is None


def test_keyring_delete_and_list_sites(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "keyring", fake_keyring())
    store = st.Store(path=tmp_path / "credentials.json")
    store.save(creds())
    store.save(creds("https://other.example.ac.il/moodle"))
    assert store.list_sites() == ["moodle.example.ac.il", "other.example.ac.il"]
    store.delete(SITE)
    assert store.list_sites() == ["other.example.ac.il"]
    assert store.load(SITE) is None
    store.delete(SITE)  # deleting twice is not an error


# --- fallback to the file backend --------------------------------------------------------------------

@POSIX_ONLY
def test_no_keyring_backend_falls_back_to_0600_file_with_warning(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(st, "keyring", fake_keyring(broken=True))
    path = tmp_path / "cfg" / "credentials.json"
    store = st.Store(path=path)
    store.save(creds())
    err = capsys.readouterr().err
    assert "keychain" in err.lower() or "keyring" in err.lower()
    assert TOKEN not in err
    assert path.exists()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert store.load(SITE) == creds()


def test_missing_keyring_module_uses_file_backend(monkeypatch, tmp_path):
    monkeypatch.setattr(st, "keyring", None)
    store = st.Store(path=tmp_path / "credentials.json")
    store.save(creds())
    assert (tmp_path / "credentials.json").exists()
    assert store.load(SITE) == creds()


# --- explicit file backend ---------------------------------------------------------------------------

@POSIX_ONLY
def test_file_backend_roundtrip_mode_and_delete(tmp_path):
    path = tmp_path / "credentials.json"
    store = st.Store(backend="file", path=path)
    assert store.load(SITE) is None
    store.save(creds())
    store.save(creds("https://other.example.ac.il"))
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert store.list_sites() == ["moodle.example.ac.il", "other.example.ac.il"]
    assert store.load(SITE) == creds()
    store.delete(SITE)
    assert store.load(SITE) is None
    assert store.list_sites() == ["other.example.ac.il"]
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "moodle.example.ac.il" not in data


def test_file_backend_never_touches_keyring(monkeypatch, tmp_path):
    fake = fake_keyring()
    monkeypatch.setattr(st, "keyring", fake)
    store = st.Store(backend="file", path=tmp_path / "credentials.json")
    store.save(creds())
    assert store.load(SITE) == creds()
    assert fake.vault == {}


def test_unknown_backend_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        st.Store(backend="cloud", path=tmp_path / "x.json")
