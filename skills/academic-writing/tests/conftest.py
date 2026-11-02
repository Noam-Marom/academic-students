"""Shared fixtures for the academic-writing script tests.

Scripts are imported by path (never via sys.path) so that two skills may both ship a script with a
common name without shadowing each other. Module names are prefixed with `writing_` for the same reason.
"""
import importlib.util
import pathlib

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]


def _load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def skill_dir() -> pathlib.Path:
    return SKILL_DIR


@pytest.fixture(scope="session")
def load_module():
    return _load_module
