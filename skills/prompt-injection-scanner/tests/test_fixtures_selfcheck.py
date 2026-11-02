"""The fixture generator must produce what it claims, or every detection test is meaningless."""
import zipfile

SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"}


def test_manifest_shape_and_coverage(fixtures):
    dest, manifest = fixtures
    assert len(manifest) >= 20
    for rel, meta in manifest.items():
        assert (dest / rel).exists(), rel
        assert meta["expected_min_severity"] in SEVERITIES, rel
        assert "technique" in meta and "hidden_text" in meta
    techniques = {m["technique"] for m in manifest.values()}
    for t in ["docx_hidden_run", "pptx_speaker_notes", "xlsx_hidden_sheet", "md_html_comment",
              "unicode_tags", "bidi_trojan_source", "base64_payload", "ipynb_stored_output",
              "zip_nested", "agent_config_claude_md", "hebrew_injection_docx", "windows1255_txt"]:
        assert t in techniques, t


def test_clean_twins_exist(fixtures):
    _, manifest = fixtures
    clean = [r for r, m in manifest.items() if m["expected_min_severity"] == "NONE"]
    assert len(clean) >= 4


def test_docx_hidden_run_is_really_hidden(fixtures):
    dest, manifest = fixtures
    rel = next(r for r, m in manifest.items() if m["technique"] == "docx_hidden_run")
    xml = zipfile.ZipFile(dest / rel).read("word/document.xml").decode("utf-8")
    hidden = manifest[rel]["hidden_text"]
    assert hidden in xml
    # the hidden string sits inside a run whose properties carry <w:vanish/>
    run_start = xml.rfind("<w:r>", 0, xml.find(hidden))
    assert "<w:vanish/>" in xml[run_start: xml.find(hidden)]


def test_windows1255_fixture_is_not_utf8(fixtures):
    dest, manifest = fixtures
    rel = next(r for r, m in manifest.items() if m["technique"] == "windows1255_txt")
    data = (dest / rel).read_bytes()
    try:
        data.decode("utf-8")
        assert False, "fixture must not be valid UTF-8"
    except UnicodeDecodeError:
        pass
    assert manifest[rel]["hidden_text"] in data.decode("cp1255")
