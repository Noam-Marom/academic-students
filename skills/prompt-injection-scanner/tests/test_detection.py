"""Every injected fixture is found at or above its expected severity; the hidden text is quoted in a finding."""
import pytest

ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


@pytest.fixture(scope="module")
def full_scan(fixtures, scan):
    dest, manifest = fixtures
    rc, findings, out, _ = scan([dest], "--no-ocr")
    assert findings is not None, out
    return manifest, findings["findings"]


def _for_file(findings, rel):
    name = rel.rsplit("/", 1)[-1]
    return [f for f in findings if name in f["file"]]


def _cases(kind):
    # parametrisation happens at collection time, before fixtures exist, so build a cheap manifest here
    import importlib.util, pathlib, tempfile
    spec = importlib.util.spec_from_file_location("mf_collect", pathlib.Path(__file__).parent / "fixtures" / "make_fixtures.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as d:
        man = mod.build(pathlib.Path(d))
    return [r for r, m in man.items() if not r.startswith("_") and
            ((m["expected_min_severity"] != "NONE") if kind == "injected" else (m["expected_min_severity"] == "NONE"))]


@pytest.mark.parametrize("rel", _cases("injected"))
def test_injected_fixture_is_detected(rel, full_scan):
    manifest, findings = full_scan
    meta = manifest[rel]
    hits = _for_file(findings, rel)
    if meta["technique"] == "semantic_no_keyword":
        pytest.xfail("no keyword to match: pattern scanners cannot catch this; Claude's line-by-line read is the control")
    assert hits, f"{rel}: no finding at all"
    best = min(ORDER[f["severity"]] for f in hits)
    assert best <= ORDER[meta["expected_min_severity"]], \
        f"{rel}: best severity {[f['severity'] for f in hits]} below expected {meta['expected_min_severity']}"
    if meta["hidden_text"] and len(meta["hidden_text"]) > 3:
        needle = meta["hidden_text"][:30]
        assert any(needle in (f.get("text") or "") or needle in (f.get("detail") or "") for f in hits), \
            f"{rel}: hidden text not quoted in any finding"


@pytest.mark.parametrize("rel", _cases("clean"))
def test_clean_fixture_has_no_high_finding(rel, full_scan):
    _, findings = full_scan
    loud = [f for f in _for_file(findings, rel) if ORDER[f["severity"]] <= ORDER["HIGH"]]
    assert loud == [], f"{rel}: false alarm(s): {[(f['severity'], f['technique']) for f in loud]}"


def test_ocr_layer_lookalike_is_not_loud(full_scan):
    manifest, findings = full_scan
    rel = next((r for r, m in manifest.items() if m["technique"] == "pdf_ocr_layer_clean"), None)
    if rel is None:
        pytest.skip("PyMuPDF not available")
    loud = [f for f in _for_file(findings, rel) if ORDER[f["severity"]] <= ORDER["HIGH"]]
    assert loud == [], "a scanned page with an invisible OCR text layer must not be reported as an attack"
