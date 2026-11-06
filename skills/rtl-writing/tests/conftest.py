import importlib.util
import pathlib
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"


def load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def rtl():
    return load_module(SCRIPTS / "check_rtl.py", "hebrew_check_rtl")


@pytest.fixture(scope="session")
def docx_rtl():
    return load_module(SCRIPTS / "check_docx_rtl.py", "hebrew_check_docx_rtl")
