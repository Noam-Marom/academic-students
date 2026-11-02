"""Shared fixtures for the moodle-mcp tests.

The package is importable without an editable install (the repo-level `python3 -m pytest -q` collects
`servers/` straight from a checkout), so `src/` is put on sys.path here. Every test module calls
`pytest.importorskip` for the third-party packages it needs, so a checkout without `mcp`/`httpx`/`respx`
skips these tests instead of erroring.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

SERVER_DIR = pathlib.Path(__file__).resolve().parents[1]
SRC = SERVER_DIR / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

SITE = "https://moodle.example.ac.il"
TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
PRIVATE_TOKEN = "pRiVaTe0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTU"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def fixture():
    return load_fixture
