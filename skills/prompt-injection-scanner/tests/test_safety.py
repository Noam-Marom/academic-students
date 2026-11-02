"""The scanner must never execute anything from the scanned folder and must survive hostile inputs."""
import uuid
import zipfile


def test_planted_json_module_is_not_imported(tmp_path, scan):
    marker = tmp_path / f"pwned-{uuid.uuid4().hex}"
    target = tmp_path / "hw"
    target.mkdir()
    (target / "json.py").write_text(f"open({str(marker)!r}, 'w').write('x')\n", encoding="utf-8")
    (target / "notes.md").write_text("# HW\n\nplain text\n", encoding="utf-8")
    rc, findings, out, _ = scan([target], "--no-ocr", cwd=str(target))
    assert not marker.exists(), "a json.py inside the scanned folder was executed"
    assert findings is not None


def test_corrupt_pdf_and_deep_zip_do_not_crash(tmp_path, scan):
    target = tmp_path / "hw"
    target.mkdir()
    (target / "broken.pdf").write_bytes(b"%PDF-1.4\n" + bytes(range(256)) * 40)
    inner = b""
    for level in range(6):
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(f"level{level}.txt" if level == 0 else f"inner{level}.zip", inner or b"deep text")
        inner = buf.getvalue()
    (target / "deep.zip").write_bytes(inner)
    rc, findings, out, _ = scan([target], "--no-ocr")
    assert rc in (0, 1), out
    assert findings is not None


def test_originals_are_not_modified(fixtures, scan):
    dest, manifest = fixtures
    before = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file() and ".git" not in p.parts}
    scan([dest], "--no-ocr")
    after = {p: p.read_bytes() for p in dest.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert before == after
