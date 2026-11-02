"""Load lecture-notes scripts (and the test-only PPTX builder) by path, never via sys.path."""
import importlib.util
import pathlib

import pytest

SKILL = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
HERE = pathlib.Path(__file__).resolve().parent


def load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def pptx_builder():
    return load_module(HERE / "pptx_builder.py", "lecture_pptx_builder")


@pytest.fixture(scope="session")
def slides_extract():
    return load_module(SCRIPTS / "slides_extract.py", "lecture_slides_extract")


@pytest.fixture(scope="session")
def transcribe():
    return load_module(SCRIPTS / "transcribe.py", "lecture_transcribe")


@pytest.fixture(scope="session")
def align():
    return load_module(SCRIPTS / "align.py", "lecture_align")
