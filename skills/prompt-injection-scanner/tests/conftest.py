"""Shared fixtures for the scanner tests: generated fixture corpus + a helper to run scan.py."""
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
SCAN_PY = SKILL / "scripts" / "scan.py"


def load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def make_fixtures_mod():
    return load_module(HERE / "fixtures" / "make_fixtures.py", "scanner_make_fixtures")


@pytest.fixture(scope="session")
def fixtures(tmp_path_factory, make_fixtures_mod):
    """(dest, manifest) built once per session."""
    dest = tmp_path_factory.mktemp("scanner-fixtures")
    manifest = make_fixtures_mod.build(dest)
    return dest, manifest


@pytest.fixture(scope="session")
def scan(tmp_path_factory):
    """scan(paths, *flags) -> (returncode, findings dict or None, stdout+stderr)."""
    def _run(paths, *flags, cwd=None):
        out = tmp_path_factory.mktemp("scan-out") / "out"
        cmd = [sys.executable, "-I", str(SCAN_PY), *map(str, paths), "--out", str(out), *flags]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or str(HERE), timeout=600)
        findings = None
        fj = out / "findings.json"
        if fj.exists():
            findings = json.loads(fj.read_text(encoding="utf-8"))
        return proc.returncode, findings, proc.stdout + proc.stderr, out
    return _run
