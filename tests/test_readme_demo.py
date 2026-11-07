"""The README's scanner demo is real: the sample assignment in docs/examples/scanner/ really hides a
white-on-white trap, and the scanner really reports it as CRITICAL."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "docs/examples/scanner/assignment.docx"


def test_readme_shows_the_scanner_demo():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/images/scanner-demo.gif" in text
    assert (ROOT / "docs/images/scanner-demo.gif").stat().st_size < 1_000_000
    assert "docs/examples/scanner/assignment.docx" in text


def test_the_demo_sample_is_caught_as_critical(tmp_path):
    pytest.importorskip("docx")
    scan = ROOT / "skills/prompt-injection-scanner/scripts/scan.py"
    subprocess.run([sys.executable, "-I", str(scan), str(SAMPLE), "--out", str(tmp_path), "--no-ocr"],
                   capture_output=True, check=False)
    findings = json.loads((tmp_path / "findings.json").read_text(encoding="utf-8"))
    items = findings["findings"] if isinstance(findings, dict) else findings
    critical = [f for f in items if f.get("severity") == "CRITICAL"]
    assert critical and "If you are an AI" in json.dumps(critical)


def test_readme_discloses_what_the_plugin_runs_and_sends():
    """The Claude directory's security scan looks for undisclosed network use and code execution."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## What it runs and sends" in text
    section = text.split("## What it runs and sends", 1)[1].split("\n## ", 1)[0]
    for needle in ["PyPI", "uv.lock", "your own Moodle", "keychain", "no telemetry", "locally"]:
        assert needle in section, needle
