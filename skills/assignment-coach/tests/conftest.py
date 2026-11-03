"""Shared fixtures for the assignment-coach script tests.

Scripts are imported by path (never via sys.path) so that two skills may both ship a script with a
common name without shadowing each other. Module names are prefixed with `coach_` for the same reason.
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


_CONTRACT = SKILL_DIR.parents[1] / "tests" / "eval_contract.py"


@pytest.fixture(scope="session")
def eval_case_ok():
    return _load_module(_CONTRACT, "coach_eval_contract").check_case


@pytest.fixture(scope="session")
def trigger_evals_ok():
    return _load_module(_CONTRACT, "coach_eval_contract_t").check_trigger_file
