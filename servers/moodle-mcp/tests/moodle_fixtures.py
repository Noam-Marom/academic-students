"""Constants and fixture loader shared by the moodle-mcp tests (a unique name, so it never shadows the repo's
tests/conftest.py when both test trees are collected in one run)."""
from __future__ import annotations

import json
import pathlib

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"

SITE = "https://moodle.example.ac.il"
TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
PRIVATE_TOKEN = "pRiVaTe0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTU"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))
