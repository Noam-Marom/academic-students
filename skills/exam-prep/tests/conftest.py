"""Load exam-prep scripts by path (never via sys.path), as tests/conftest.py does for the repo."""
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
def question_bank():
    return load_module(SCRIPTS / "question_bank.py", "exam_question_bank")


@pytest.fixture(scope="session")
def mock_exam():
    return load_module(SCRIPTS / "mock_exam.py", "exam_mock_exam")


@pytest.fixture(scope="session")
def anki_export():
    return load_module(SCRIPTS / "anki_export.py", "exam_anki_export")
