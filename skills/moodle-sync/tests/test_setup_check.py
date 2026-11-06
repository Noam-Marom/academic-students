"""setup_check.py: what it takes to get the moodle MCP server running on this machine, as concrete steps."""
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "setup_check.py"


@pytest.fixture(scope="module")
def sc():
    spec = importlib.util.spec_from_file_location("moodle_setup_check", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["moodle_setup_check"] = mod
    spec.loader.exec_module(mod)
    return mod


SERVER = pathlib.Path("/plugin/servers/moodle-mcp")


def ids(p):
    return [s["id"] for s in p["steps"]]


def test_with_uv_only_login_and_reconnect_remain(sc):
    p = sc.plan("linux", have_uv=True, server_dir=SERVER, moodle_url="https://moodle.example.ac.il")
    assert ids(p) == ["login", "reconnect"]
    login = p["steps"][0]
    assert login["run_by"] == "student"
    assert login["command"] == f"uv run --directory {SERVER} moodle-mcp login https://moodle.example.ac.il"


@pytest.mark.parametrize("os_name,needle", [("windows", "install.ps1"), ("darwin", "install.sh"), ("linux", "install.sh")])
def test_without_uv_first_step_installs_it_with_consent(sc, os_name, needle):
    p = sc.plan(os_name, have_uv=False, server_dir=SERVER)
    step = p["steps"][0]
    assert step["id"] == "install-uv" and step["needs_consent"] is True and step["run_by"] == "assistant"
    assert needle in step["command"] and "astral.sh" in step["command"]
    assert ids(p) == ["install-uv", "login", "reconnect"]


def test_login_never_carries_a_password_and_is_typed_by_the_student(sc):
    p = sc.plan("linux", have_uv=True, server_dir=SERVER)
    login = next(s for s in p["steps"] if s["id"] == "login")
    assert "password" not in login["command"].lower() and login["run_by"] == "student"
    assert "<moodle-url>" in login["command"]


def test_no_server_bundled_means_browser_fallback(sc):
    p = sc.plan("linux", have_uv=True, server_dir=None)
    assert p["mcp_possible"] is False and p["fallback"] == "browser"
    assert p["steps"] == []


def test_cli_json_reports_this_machine(tmp_path):
    proc = subprocess.run([sys.executable, str(SCRIPT), "--json"], capture_output=True, text=True)
    assert proc.returncode in (0, 1), proc.stderr
    data = json.loads(proc.stdout)
    assert {"os", "have_uv", "mcp_possible", "steps", "fallback"} <= set(data)
