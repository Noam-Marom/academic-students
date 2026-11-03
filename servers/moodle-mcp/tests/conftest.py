"""Shared setup for the moodle-mcp tests.

The package is importable without an editable install (the repo-level `python3 -m pytest -q` collects
`servers/` straight from a checkout), so `src/` and this directory are put on sys.path here. Shared constants
live in `moodle_fixtures.py`. Every test module calls `pytest.importorskip` for the third-party packages it
needs, so a checkout without `mcp`/`httpx`/`respx` skips these tests instead of erroring.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
for p in (HERE.parent / "src", HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
