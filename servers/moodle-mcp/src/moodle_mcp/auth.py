"""Getting a token — the only module that ever sees a password, and only inside the CLI process.

Two ways in (facts: `docs/moodle-ws-facts.md` §1–3):

* `login_with_password`: POST username/password once to `login/token.php` (service `moodle_mobile_app`).
  The password is a local variable here and in the CLI; it is never stored, logged or returned.
* `login_via_browser`: the mobile-app launch flow. Moodle's `urlscheme` must match
  `^[a-zA-Z][a-zA-Z0-9-\\+\\.]*$`, so it cannot redirect to a loopback URL; instead `confirmed=1` makes
  Moodle render a page with the `academicstudents://token=…` link, the student pastes it back, and
  `parse_launch_payload` checks `md5(site + passport)` before trusting the token inside.

Which one to use comes from `tool_mobile_get_public_config` (`typeoflogin`, `identityproviders`).
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import secrets
import sys
import webbrowser
from typing import Any, Callable
from urllib.parse import unquote

import httpx

from .errors import AuthError, TransportError

SERVICE = "moodle_mobile_app"
URLSCHEME = "academicstudents"
PUBLIC_CONFIG_FN = "tool_mobile_get_public_config"
_AJAX_BODY = [{"index": 0, "methodname": PUBLIC_CONFIG_FN, "args": {}}]
_TOKEN_RE = re.compile(r"token=([^&\s]+)")


def normalise_site(site: str) -> str:
    """`moodle.bgu.ac.il/` → `https://moodle.bgu.ac.il`."""
    site = site.strip()
    if "://" not in site:
        site = "https://" + site
    return site.rstrip("/")


# -- public config -------------------------------------------------------------------------------------

def _ajax_data(resp: httpx.Response) -> dict | None:
    if resp.status_code >= 400:
        return None
    try:
        body = resp.json()
    except ValueError:
        return None
    if isinstance(body, list) and body and isinstance(body[0], dict) and not body[0].get("error"):
        data = body[0].get("data")
        return data if isinstance(data, dict) else None
    return None


def get_public_config(site: str, http: httpx.Client) -> dict:
    """`tool_mobile_get_public_config` without a token, via the no-login AJAX endpoint (POST, then GET)."""
    site = normalise_site(site)
    url = f"{site}/lib/ajax/service-nologin.php"
    errors: list[str] = []
    try:
        data = _ajax_data(http.post(url, params={"info": PUBLIC_CONFIG_FN}, json=_AJAX_BODY))
        if data is not None:
            return data
        errors.append("POST form rejected")
    except httpx.HTTPError as exc:
        errors.append(f"POST: {type(exc).__name__}")
    try:
        data = _ajax_data(http.get(url, params={"info": PUBLIC_CONFIG_FN, "args": json.dumps(_AJAX_BODY)}))
        if data is not None:
            return data
        errors.append("GET form rejected")
    except httpx.HTTPError as exc:
        errors.append(f"GET: {type(exc).__name__}")
    raise TransportError(f"could not read the mobile public config of {site} ({'; '.join(errors)})")


def wants_browser_login(config: dict) -> bool:
    """typeoflogin 2/3 or any identity provider → the site expects the browser flow."""
    return int(config.get("typeoflogin") or 1) in (2, 3) or bool(config.get("identityproviders"))


# -- username / password -------------------------------------------------------------------------------

def login_with_password(site: str, username: str, password: str, http: httpx.Client) -> dict:
    """One POST to `login/token.php`; returns {"token", "privatetoken"}. Maps Moodle's errorcode to AuthError."""
    site = normalise_site(site)
    try:
        resp = http.post(f"{site}/login/token.php",
                         data={"username": username, "password": password, "service": SERVICE})
    except httpx.HTTPError as exc:
        raise TransportError(f"login/token.php unreachable: {type(exc).__name__}") from None
    if resp.status_code >= 400:
        raise TransportError(f"HTTP {resp.status_code} from login/token.php")
    try:
        body = resp.json()
    except ValueError:
        raise TransportError("login/token.php did not answer with JSON — the site may require browser (SSO) "
                             "login; try `moodle-mcp login <site> --browser`") from None
    if isinstance(body, dict) and body.get("token"):
        return {"token": body["token"], "privatetoken": body.get("privatetoken") or None}
    if isinstance(body, dict) and body.get("errorcode"):
        message = str(body.get("error") or body.get("message") or body["errorcode"]).replace(password, "<password>")
        raise AuthError(body["errorcode"], message)
    raise TransportError("unexpected answer from login/token.php")


# -- browser / launch flow -----------------------------------------------------------------------------

def new_passport() -> str:
    """A random float as a string, like the official app (`Math.random() * 1000`)."""
    return str(secrets.SystemRandom().random() * 1000)


def build_launch_url(site: str, passport: str, urlscheme: str = URLSCHEME) -> str:
    site = normalise_site(site)
    return (f"{site}/admin/tool/mobile/launch.php?service={SERVICE}&passport={passport}"
            f"&urlscheme={urlscheme}&confirmed=1")


def _signature(site: str, passport: str) -> str:
    return hashlib.md5((site.rstrip("/") + passport).encode("utf-8")).hexdigest()


def parse_launch_payload(pasted: str, site: str, passport: str) -> dict:
    """Decode the `<scheme>://token=<base64>` link Moodle shows; verify md5(site + passport); return tokens."""
    pasted = (pasted or "").strip()
    m = _TOKEN_RE.search(pasted)
    encoded = unquote(m.group(1)) if m else pasted
    if not encoded or "://" in encoded:
        raise AuthError("malformed", "that does not look like the login link (expected …token=…)")
    try:
        plain = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (binascii.Error, ValueError):
        raise AuthError("malformed", "the login link's token payload is not valid base64") from None
    parts = plain.split(":::")
    if len(parts) < 2 or not parts[1]:
        raise AuthError("malformed", "the login link's token payload has an unexpected shape")
    site = normalise_site(site)
    swapped = site.replace("https://", "http://", 1) if site.startswith("https://") else site.replace("http://", "https://", 1)
    if parts[0] not in (_signature(site, passport), _signature(swapped, passport)):
        raise AuthError("signature mismatch", "the login link was not issued for this site and login attempt")
    return {"token": parts[1], "privatetoken": parts[2] if len(parts) > 2 and parts[2] else None}


def login_via_browser(site: str, http: httpx.Client, opener: Callable[[str], Any] = webbrowser.open,
                      reader: Callable[[str], str] = input, passport: str | None = None) -> dict:
    """Open the launch URL, let the student log in (SSO included), and read the pasted-back link."""
    site = normalise_site(site)
    passport = passport or new_passport()
    url = build_launch_url(site, passport)
    opened = False
    try:
        opened = bool(opener(url))
    except Exception:  # a headless machine without a browser
        opened = False
    print("Log in to Moodle in the browser window that just opened." if opened
          else "Open this address in a browser and log in to Moodle:", file=sys.stdout)
    if not opened:
        print(f"  {url}")
    print(f"When Moodle shows a link starting with {URLSCHEME}://token= , copy the whole link and paste it here.")
    print("(Only a login token travels in that link; your password stays in the browser.)")
    pasted = reader("Paste the link: ")
    return parse_launch_payload(pasted, site, passport)
