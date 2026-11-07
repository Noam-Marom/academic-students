#!/usr/bin/env python3
"""What it takes to get the plugin's moodle MCP server running on this machine, as concrete steps.

    python3 setup_check.py [--url https://moodle.example.ac.il] [--json]

Steps, in order, each marked with who runs it:
  install-uv  (assistant, only after the student says yes) — the server runs through `uv`
  login       (student, in their own terminal) — Moodle asks for the password there, never in the chat
  reconnect   (student) — `/mcp` in Claude Code, or restart the desktop app, so the server starts

When the server is not bundled (a skill uploaded on its own, claude.ai on the web) there are no steps and the
fallback is the browser: Moodle opened in the student's own signed-in browser.

Exit codes: 0 ready (uv present and server bundled), 1 steps remain or browser fallback, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path

UV_INSTALL = {
    "windows": 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
    "posix": "curl -LsSf https://astral.sh/uv/install.sh | sh",
}


def _server_dir() -> Path | None:
    d = Path(__file__).resolve().parents[3] / "servers" / "moodle-mcp"
    return d if (d / "pyproject.toml").is_file() else None


def plan(os_name: str, have_uv: bool, server_dir: Path | None, moodle_url: str | None = None) -> dict:
    os_name = os_name.lower()
    out = {"os": os_name, "have_uv": have_uv, "server_dir": str(server_dir) if server_dir else None,
           "mcp_possible": server_dir is not None, "fallback": "browser", "steps": []}
    if server_dir is None:
        out["note"] = ("the moodle server is not bundled here (single skill or claude.ai on the web): "
                       "use Moodle in the student's browser instead")
        return out
    if not have_uv:
        out["steps"].append({
            "id": "install-uv", "run_by": "assistant", "needs_consent": True,
            "command": UV_INSTALL["windows" if os_name.startswith("win") else "posix"],
            "why": "the moodle server runs through uv (a Python package runner from astral.sh); a fresh "
                   "terminal is needed afterwards so uv is on PATH"})
    out["steps"].append({
        "id": "login", "run_by": "student", "needs_consent": False,
        "command": f"uv run --frozen --directory {server_dir} moodle-mcp login {moodle_url or '<moodle-url>'}",
        "why": "Moodle asks for the password in that terminal; only a revocable token is kept, in the keychain"})
    out["steps"].append({
        "id": "reconnect", "run_by": "student", "needs_consent": False,
        "command": "/mcp (Claude Code) or restart the Claude desktop app",
        "why": "the server starts with the session; it was not running while uv or the token was missing"})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    p = plan(platform.system() or sys.platform, shutil.which("uv") is not None, _server_dir(), a.url)
    if a.json:
        print(json.dumps(p, indent=1))
    else:
        if not p["mcp_possible"]:
            print(p["note"])
        for i, s in enumerate(p["steps"], 1):
            consent = " (ask first)" if s["needs_consent"] else ""
            print(f"{i}. [{s['run_by']}{consent}] {s['command']}\n   {s['why']}")
    ready = p["mcp_possible"] and p["have_uv"]
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
