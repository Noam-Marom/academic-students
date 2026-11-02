"""CLI contract: --quick gate mode, exit codes, and --out that never deletes a directory it did not create."""
import pathlib
import subprocess
import sys

SCAN_PY = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "scan.py"


def _subset(fixtures, tmp_path, names):
    dest, _ = fixtures
    sub = tmp_path / "subset"
    sub.mkdir(parents=True)
    for n in names:
        (sub / n).write_bytes((dest / n).read_bytes())
    return sub


def test_quick_mode_prints_summary_and_skips_renders(fixtures, tmp_path, scan):
    sub = _subset(fixtures, tmp_path, ["docx_hidden_run.docx", "plain_clean.md"])
    rc, findings, out, outdir = scan([sub], "--quick")
    assert "QUICK:" in out
    assert "escalate=true" in out
    assert rc == 1
    assert findings is not None and (outdir / "findings.json").exists()
    assert not (outdir / "renders").exists()


def test_quick_mode_clean_exits_zero(fixtures, tmp_path, scan):
    sub = _subset(fixtures, tmp_path, ["plain_clean.md", "md_html_comment_clean.md"])
    rc, findings, out, _ = scan([sub], "--quick")
    assert rc == 0, out
    assert "escalate=false" in out


def test_full_mode_exit_code_reflects_findings(fixtures, tmp_path, scan):
    clean = _subset(fixtures, tmp_path / "a", ["plain_clean.md"])
    rc, _, out, _ = scan([clean], "--no-ocr")
    assert rc == 0, out
    (tmp_path / "b").mkdir()
    dirty = _subset(fixtures, tmp_path / "b", ["docx_hidden_run.docx"])
    rc, _, out, _ = scan([dirty], "--no-ocr")
    assert rc == 1, out


def test_out_refuses_to_delete_foreign_directory(fixtures, tmp_path, scan):
    dest, _ = fixtures
    foreign = tmp_path / "my-notes"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("important", encoding="utf-8")
    proc = subprocess.run([sys.executable, "-I", str(SCAN_PY), str(dest / "plain_clean.md"), "--out", str(foreign), "--no-ocr"],
                          capture_output=True, text=True)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert (foreign / "keep.txt").read_text(encoding="utf-8") == "important"
    assert "--force" in proc.stdout + proc.stderr


def test_out_reuses_its_own_previous_output(fixtures, tmp_path, scan):
    dest, _ = fixtures
    out = tmp_path / "scan-out"
    for _ in range(2):
        proc = subprocess.run([sys.executable, "-I", str(SCAN_PY), str(dest / "plain_clean.md"), "--out", str(out), "--no-ocr"],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "report.md").exists()
