"""Where the Moodle token lives: the OS keychain, or a 0600 file when there is no keychain.

`keyring` service `moodle-mcp`, username = the site's host (`moodle.bgu.ac.il`), secret = JSON
`{"site","token","privatetoken"|null,"userid","username","created"}`. When `keyring` is missing or has
no usable backend (headless Linux, CI), the same JSON goes to `~/.config/moodle-mcp/credentials.json`
with mode 0600 and a one-line warning on stderr. Hosts are listed in `sites.json` next to it (hosts
only, no secrets) because the keychain API cannot enumerate entries. Only the token is ever stored;
a password never reaches this module.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

try:  # optional: the file backend works without it
    import keyring  # type: ignore
except ImportError:  # pragma: no cover - exercised by monkeypatching keyring to None
    keyring = None  # type: ignore

KEYRING_SERVICE = "moodle-mcp"
DEFAULT_PATH = Path.home() / ".config" / "moodle-mcp" / "credentials.json"
BACKENDS = ("keyring", "file")


def site_host(site: str) -> str:
    """`https://Moodle.BGU.ac.il/moodle/` → `moodle.bgu.ac.il` (a non-default port is kept)."""
    raw = site.strip()
    if "://" not in raw:
        raw = "https://" + raw
    netloc = urlparse(raw).netloc.lower()
    if netloc.endswith(":443") or netloc.endswith(":80"):
        netloc = netloc.rsplit(":", 1)[0]
    return netloc


@dataclass(frozen=True)
class Credentials:
    site: str
    token: str
    privatetoken: str | None
    userid: int
    username: str
    created: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str, site: str | None = None) -> "Credentials":
        data = json.loads(raw)
        data.setdefault("site", site)
        return cls(**data)


def _keyring_error(name: str) -> type[BaseException]:
    errors = getattr(keyring, "errors", None)
    return getattr(errors, name, RuntimeError) if errors is not None else RuntimeError


class Store:
    def __init__(self, backend: str | None = None, path: Path | None = None):
        if backend is not None and backend not in BACKENDS:
            raise ValueError(f"unknown credential backend {backend!r}; expected one of {BACKENDS}")
        self.path = Path(path) if path else DEFAULT_PATH
        self.sites_path = self.path.with_name("sites.json")
        self._backend = backend
        self._warned = False

    # -- backend choice --------------------------------------------------------------------------------

    def _use_keyring(self) -> bool:
        if self._backend == "file":
            return False
        if keyring is None:
            if self._backend == "keyring":
                raise RuntimeError("the keyring package is not installed")
            return False
        return True

    def _warn_fallback(self, exc: BaseException) -> None:
        if not self._warned:
            self._warned = True
            print(f"moodle-mcp: no usable OS keychain ({type(exc).__name__}); storing the token in "
                  f"{self.path} with mode 0600 instead.", file=sys.stderr)

    # -- site index (hosts only) -----------------------------------------------------------------------

    def _read_index(self) -> dict[str, str]:
        if not self.sites_path.exists():
            return {}
        try:
            data = json.loads(self.sites_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_index(self, index: dict[str, str]) -> None:
        self.sites_path.parent.mkdir(parents=True, exist_ok=True)
        self.sites_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")

    # -- file backend ----------------------------------------------------------------------------------

    def _read_file(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_file(self, data: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    # -- API -------------------------------------------------------------------------------------------

    def save(self, c: Credentials) -> None:
        host = site_host(c.site)
        stored = False
        if self._use_keyring():
            try:
                keyring.set_password(KEYRING_SERVICE, host, c.to_json())
                stored = True
            except _keyring_error("NoKeyringError") as exc:
                if self._backend == "keyring":
                    raise
                self._warn_fallback(exc)
        if not stored:
            data = self._read_file()
            data[host] = json.loads(c.to_json())
            self._write_file(data)
        index = self._read_index()
        index[host] = c.site
        self._write_index(index)

    def load(self, site: str) -> Credentials | None:
        host = site_host(site)
        if self._use_keyring():
            try:
                raw = keyring.get_password(KEYRING_SERVICE, host)
                if raw:
                    return Credentials.from_json(raw, site=self._read_index().get(host, site))
            except _keyring_error("NoKeyringError") as exc:
                if self._backend == "keyring":
                    raise
                self._warn_fallback(exc)
        entry = self._read_file().get(host)
        if entry:
            entry.setdefault("site", self._read_index().get(host, site))
            return Credentials(**entry)
        return None

    def delete(self, site: str) -> None:
        host = site_host(site)
        if self._use_keyring():
            try:
                keyring.delete_password(KEYRING_SERVICE, host)
            except (_keyring_error("NoKeyringError"), _keyring_error("PasswordDeleteError")):
                pass
        data = self._read_file()
        if host in data:
            del data[host]
            self._write_file(data)
        index = self._read_index()
        if host in index:
            del index[host]
            self._write_index(index)

    def list_sites(self) -> list[str]:
        hosts = set(self._read_index()) | set(self._read_file())
        return sorted(hosts)
