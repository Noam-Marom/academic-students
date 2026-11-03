"""Thin httpx wrapper over Moodle's REST web-service endpoint.

Protocol facts are in `docs/moodle-ws-facts.md`. The client only ever calls functions in
`ALLOWED_FUNCTIONS` (a test pins the set), posts the token in the form body (never in the URL),
maps Moodle's error JSON to the exceptions in `errors.py`, and strips the token from every message
it raises so that no exception, log line or tool result can leak it.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import httpx

from .errors import AuthError, MoodleError, TransportError

SERVICE = "moodle_mobile_app"
REST_PATH = "/webservice/rest/server.php"
TOKEN_PLACEHOLDER = "<token>"
RELOGIN_HINT = "re-authenticate: run `moodle-mcp login <site>` in a terminal"

# Error codes that mean the token is gone (invalid, or expired and deleted server-side).
AUTH_ERRORCODES = frozenset({"invalidtoken", "accessexception"})

# The complete set of web-service functions this client may call. Every one of them reads.
ALLOWED_FUNCTIONS: frozenset[str] = frozenset({
    "core_webservice_get_site_info",
    "core_enrol_get_users_courses",
    "core_course_get_contents",
    "mod_assign_get_assignments",
    "core_calendar_get_action_events_by_timesort",
    "core_calendar_get_calendar_upcoming_view",
    "core_calendar_get_calendar_export_token",
    "gradereport_user_get_grade_items",
    "mod_forum_get_forums_by_courses",
    "mod_forum_get_forum_discussions",
    "mod_forum_get_discussion_posts",
    "message_popup_get_popup_notifications",
    "mod_quiz_get_quizzes_by_courses",
    "tool_mobile_get_public_config",
})


def encode_params(params: dict, prefix: str = "") -> dict[str, str]:
    """Flatten nested params into PHP query syntax: {"courseids": [1, 2]} → {"courseids[0]": "1", …}.

    Booleans become "1"/"0"; None values are dropped.
    """
    out: dict[str, str] = {}
    for key, value in params.items():
        name = f"{prefix}[{key}]" if prefix else str(key)
        if value is None:
            continue
        if isinstance(value, dict):
            out.update(encode_params(value, name))
        elif isinstance(value, (list, tuple)):
            out.update(encode_params({i: v for i, v in enumerate(value)}, name))
        elif isinstance(value, bool):
            out[name] = "1" if value else "0"
        else:
            out[name] = str(value)
    return out


def strip_token(text: str, token: str) -> str:
    """Replace every occurrence of the token with a placeholder."""
    if not token:
        return text
    return text.replace(token, TOKEN_PLACEHOLDER)


class MoodleClient:
    def __init__(self, site: str, token: str, http: httpx.Client | None = None, userid: int | None = None):
        self.site = site.rstrip("/")
        self.token = token
        self.userid = userid
        self.http = http or httpx.Client(timeout=60.0, follow_redirects=True)

    # -- helpers ---------------------------------------------------------------------------------------

    def _strip(self, text: Any) -> str:
        return strip_token(str(text), self.token)

    def _raise_for_moodle_error(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        code = payload.get("errorcode")
        if not code or not ("exception" in payload or "error" in payload or "message" in payload):
            return
        if code in AUTH_ERRORCODES:
            raise AuthError(code, RELOGIN_HINT)
        raise MoodleError(code, self._strip(payload.get("message") or payload.get("error") or code))

    # -- API -------------------------------------------------------------------------------------------

    def call(self, wsfunction: str, **params: Any) -> Any:
        """Call one web-service function and return the parsed JSON."""
        if wsfunction not in ALLOWED_FUNCTIONS:
            raise PermissionError(f"{wsfunction} is not in the read-only allowlist of moodle-mcp")
        data = {"wstoken": self.token, "wsfunction": wsfunction, "moodlewsrestformat": "json"}
        data.update(encode_params(params))
        try:
            resp = self.http.post(self.site + REST_PATH, data=data)
        except httpx.HTTPError as exc:
            raise TransportError(self._strip(f"{wsfunction}: {type(exc).__name__}: {exc}")) from None
        if resp.status_code >= 400:
            raise TransportError(self._strip(f"HTTP {resp.status_code} calling {wsfunction}: {resp.text[:200]}"))
        try:
            payload = resp.json()
        except ValueError:
            raise TransportError(self._strip(f"non-JSON response from {wsfunction}: {resp.text[:200]}")) from None
        self._raise_for_moodle_error(payload)
        return payload

    def is_site_url(self, url: str) -> bool:
        """True when `url` belongs to this Moodle site (same scheme, host and path prefix)."""
        return url == self.site or url.startswith(self.site + "/")

    def fetch_text(self, url: str) -> str:
        """GET a page of this site (e.g. the calendar export) and return its body as text."""
        if not self.is_site_url(url):
            raise PermissionError("moodle-mcp only fetches URLs on the logged-in Moodle site")
        try:
            resp = self.http.get(url)
        except httpx.HTTPError as exc:
            raise TransportError(self._strip(f"GET failed: {type(exc).__name__}: {exc}")) from None
        if resp.status_code >= 400:
            raise TransportError(self._strip(f"HTTP {resp.status_code} fetching {url}"))
        return resp.text

    def file_url(self, fileurl: str) -> str:
        """A `webservice/pluginfile.php` URL with the token appended the way Moodle expects."""
        sep = "&" if "?" in fileurl else "?"
        return f"{fileurl}{sep}token={self.token}"

    def download(self, fileurl: str, dest: Path) -> tuple[Path, str]:
        """Stream a file to `dest` (parents created) and return (dest, sha256 hex digest).

        Bytes go to a hidden `.part` file next to `dest` and replace `dest` only when the download completed, so
        a broken connection never leaves a truncated file and never destroys a previous complete copy."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(f".{dest.name}.part")
        digest = hashlib.sha256()
        try:
            with self.http.stream("GET", self.file_url(fileurl)) as resp:
                if resp.status_code >= 400:
                    raise TransportError(self._strip(f"HTTP {resp.status_code} downloading {fileurl}"))
                if resp.headers.get("content-type", "").split(";")[0].strip() == "application/json":
                    # pluginfile.php answers errors as JSON with HTTP 200
                    body = resp.read()
                    try:
                        payload = httpx.Response(200, content=body).json()
                    except ValueError:
                        payload = None
                    self._raise_for_moodle_error(payload)
                    part.write_bytes(body)
                    digest.update(body)
                else:
                    with part.open("wb") as fh:
                        for chunk in resp.iter_bytes():
                            fh.write(chunk)
                            digest.update(chunk)
            os.replace(part, dest)
        except httpx.HTTPError as exc:
            part.unlink(missing_ok=True)
            raise TransportError(self._strip(f"download failed: {type(exc).__name__}: {exc}")) from None
        except BaseException:
            part.unlink(missing_ok=True)
            raise
        return dest, digest.hexdigest()
