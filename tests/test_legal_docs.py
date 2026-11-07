"""Terms, privacy notice and public wording, as revised after the 2026-11-07 legal review (liability, academic
integrity and platforms, privacy and IP). These live outside the skills, so they cost no model time."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def test_terms_cover_the_clauses_the_review_asked_for():
    t = _read("TERMS.md")
    for clause in ["fullest extent the law permits", "cannot lawfully be excluded", "remains in force",
                   "ILS 200", "apply only to use after", "may differ substantially", "MIT License",
                   "Noam Marom, Eyal Silbershtein", "age requirements", "trademarks of their owners",
                   "Not a cheating service", "detection", "voluntary gift", "without their consent"]:
        assert clause in t, clause
    assert "does not predict it" not in t and "smallest extent" not in t


def test_privacy_says_what_reaches_the_ai_provider_and_the_network():
    p = _read("PRIVACY.md")
    for clause in ["What reaches your AI provider", "Hugging Face", "PyPI", "credentials.json",
                   "moodle-mcp logout", "Retention", "GitHub's privacy statement", "Last updated"]:
        assert clause in p, clause


def test_public_wording_promises_design_not_guarantees():
    r = _read("README.md")
    for phrase in ["keeps you honest", "An honest grade", "real citations", "## What it will never do",
                   "funds the next"]:
        assert phrase not in r, phrase
    assert "## What it is designed not to do" in r and "Terms of use" in r and "voluntary gift" in r
    m = json.loads(_read(".claude-plugin/plugin.json"))
    assert m["termsOfServiceUrl"].endswith("/blob/main/TERMS.md")
    assert "Never submits" not in m["description"] and "Read-only by design" in m["description"]


def test_license_names_both_maintainers_and_a_security_policy_exists():
    assert "Noam Marom, Eyal Silbershtein and contributors" in _read("LICENSE")
    assert "inbound=outbound" in _read("CONTRIBUTING.md")
    assert "security/advisories/new" in _read("SECURITY.md")


def test_lecture_legal_note_is_accurate_and_not_israel_only():
    n = _read("skills/lecture-notes/references/legal-note.md")
    assert "Never sends audio or the transcript" not in n
    assert "processed by your AI provider" in n and "Recording laws differ" in n
