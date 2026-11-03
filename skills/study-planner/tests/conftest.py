"""Load study-planner scripts by path, never via sys.path."""
import importlib.util
import pathlib

import pytest

SKILL = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def merge_deadlines():
    return load_module(SCRIPTS / "merge_deadlines.py", "planner_merge_deadlines")


@pytest.fixture(scope="session")
def plan_week():
    return load_module(SCRIPTS / "plan_week.py", "planner_plan_week")


@pytest.fixture(scope="session")
def export_ics():
    return load_module(SCRIPTS / "export_ics.py", "planner_export_ics")
