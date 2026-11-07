"""`moodle-mcp` command line.

    moodle-mcp login <site> [--username U] [--browser]   log in once; the password is typed here, never in Claude
    moodle-mcp logout <site>                              forget the stored token
    moodle-mcp status                                     which sites are logged in and whether the tokens work
    moodle-mcp serve                                      run the MCP server over stdio (the default)

The token goes to the OS keychain (fallback: a 0600 file). Nothing this command prints ever contains the
token, the private token or the password.
"""
from __future__ import annotations

import argparse
import getpass
import sys
import webbrowser
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from . import auth
from .client import MoodleClient, default_http, strip_token
from .errors import AuthError, MoodleError, TransportError
from .store import Credentials, Store, site_host


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moodle-mcp",
        description="Read-only MCP server for Moodle. Log in here, in a terminal; Claude only ever sees a token.")
    sub = parser.add_subparsers(dest="command")
    login = sub.add_parser(
        "login", help="log in to a Moodle site and store the token in the OS keychain",
        description="Logs in once. With username/password sites the password is typed here (hidden) and sent "
                    "once to login/token.php; it is never stored and never shown to Claude. With browser/SSO "
                    "sites a browser window opens and you paste the resulting link back.")
    login.add_argument("site", help="the Moodle address, e.g. https://moodle.bgu.ac.il")
    login.add_argument("--username", help="Moodle username (asked interactively when omitted)")
    login.add_argument("--browser", action="store_true", help="force the browser (SSO) flow")
    logout = sub.add_parser("logout", help="delete the stored token for a site")
    logout.add_argument("site")
    sub.add_parser("status", help="list logged-in sites and check their tokens")
    sub.add_parser("serve", help="run the MCP server over stdio (default)")
    return parser


def _say(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"moodle-mcp: {msg}", file=sys.stderr)


def _verify_and_store(site: str, tokens: dict, store: Store, http: httpx.Client) -> int:
    token = tokens["token"]
    client = MoodleClient(site, token, http=http)
    try:
        info = client.call("core_webservice_get_site_info")
    except AuthError:
        _err("Moodle issued a token but then rejected it; nothing was stored. Try again.")
        return 1
    except (MoodleError, TransportError) as exc:
        _err(strip_token(f"could not verify the new token: {exc}; nothing was stored", token))
        return 1
    creds = Credentials(site=site, token=token, privatetoken=tokens.get("privatetoken"),
                        userid=int(info["userid"]), username=str(info.get("username", "")),
                        created=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"))
    store.save(creds)
    where = "the OS keychain" if (store.load(site) is not None and not store.path.exists()) else str(store.path)
    _say(f"Logged in to {info.get('sitename', site)} as {creds.username} (user id {creds.userid}).")
    _say(f"Token stored in {where}. Claude can now use the moodle MCP server; run `moodle-mcp logout {site}` to revoke.")
    if not info.get("downloadfiles"):
        _err("warning: this site's mobile service does not allow file downloads; sync_course will only index.")
    return 0


def cmd_login(args: argparse.Namespace, store: Store, http: httpx.Client, getpass_fn: Callable[[str], str],
              input_fn: Callable[[str], str], opener: Callable[[str], Any]) -> int:
    site = auth.normalise_site(args.site)
    _say(f"Connecting to {site} …")
    try:
        config = auth.get_public_config(site, http)
    except TransportError as exc:
        _err(f"could not read the site's mobile config ({exc}); trying username/password login anyway.")
        config = {}
    use_browser = args.browser or auth.wants_browser_login(config)
    try:
        if use_browser:
            tokens = auth.login_via_browser(site, http, opener=opener, reader=input_fn)
        else:
            username = (args.username or input_fn("Username: ")).strip().lower()
            password = getpass_fn("Password (typed here only — never stored, never shown to Claude): ")
            try:
                tokens = auth.login_with_password(site, username, password, http)
            finally:
                del password
    except AuthError as exc:
        _err(f"login failed: {exc}")
        if exc.errorcode == "invalidlogin" and not use_browser:
            _err("if your university signs you in through a browser (SSO), run: "
                 f"moodle-mcp login {site} --browser")
        return 1
    except TransportError as exc:
        _err(f"login failed: {exc}")
        return 1
    except (EOFError, KeyboardInterrupt):
        _err("login cancelled")
        return 1
    return _verify_and_store(site, tokens, store, http)


def cmd_logout(args: argparse.Namespace, store: Store) -> int:
    host = site_host(args.site)
    store.delete(args.site)
    _say(f"Removed the stored token for {host}. (The token itself stays valid on the server until it expires; "
         f"you can also delete it under Preferences → Security keys in Moodle.)")
    return 0


def cmd_status(store: Store, http: httpx.Client) -> int:
    sites = store.list_sites()
    if not sites:
        _say("Not logged in to any Moodle. Run: moodle-mcp login https://<your-moodle>")
        return 1
    any_valid = False
    for host in sites:
        creds = store.load(host)
        if creds is None:
            _say(f"{host}: index entry without credentials (run `moodle-mcp logout {host}` to clean up)")
            continue
        try:
            info = MoodleClient(creds.site, creds.token, http=http).call("core_webservice_get_site_info")
            state = f"token valid, user {info.get('username')} ({info.get('fullname')}), Moodle {info.get('release', '?')}"
            any_valid = True
        except AuthError:
            state = f"token invalid or expired — run: moodle-mcp login {creds.site}"
        except (MoodleError, TransportError) as exc:
            state = strip_token(f"could not reach the site ({exc})", creds.token)
        _say(f"{host} — {creds.username} — {state} — stored {creds.created}")
    return 0 if any_valid else 1


def main(argv: list[str] | None = None, *, store: Store | None = None, http: httpx.Client | None = None,
         getpass_fn: Callable[[str], str] = getpass.getpass, input_fn: Callable[[str], str] = input,
         opener: Callable[[str], Any] = webbrowser.open, serve_fn: Callable[[], int] | None = None) -> int:
    args = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    command = args.command or "serve"
    if command == "serve":
        if serve_fn is None:
            from .server import serve as serve_fn  # lazy: `login` must work even if the MCP stack is broken
        return serve_fn()
    store = store if store is not None else Store()
    http = http or default_http()
    if command == "login":
        return cmd_login(args, store, http, getpass_fn, input_fn, opener)
    if command == "logout":
        return cmd_logout(args, store)
    if command == "status":
        return cmd_status(store, http)
    _parser().print_help()
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
