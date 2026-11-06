import importlib.util
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def skill_dirs() -> list[pathlib.Path]:
    return sorted(p.parent for p in (ROOT / "skills").glob("*/SKILL.md"))


def load_module(path: pathlib.Path, name: str):
    """Import a script by path without touching sys.path (scripts live in several skills)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses and pickling need the module registered
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def check_rtl():
    return load_module(ROOT / "skills/rtl-writing/scripts/check_rtl.py", "check_rtl_mod")
