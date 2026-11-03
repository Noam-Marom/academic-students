"""check_rtl.py: the rules from SKILL.md, pinned; --fix suggests a Hebrew opener and never touches the file."""
import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_rtl.py"

WRONG = [
    "## Git Branching",
    "- **Train (10):** 5 אתגרי CTF",
    "**Note:** זה חשוב",
    "- pthread_create – יוצרת חוט",
    "- `ls -la` מציג קבצים",
    "| Command | What it does |",
    "Output: הפלט נראה כך",
    "2 threads run בו-זמנית",
    "~/.bashrc is הקובץ",
    "Running tests…",
]
RIGHT = [
    "## עבודה עם ענפים ב-Git",
    "- **סט ה-Train (10 אתגרים):** 5 אתגרי CTF",
    "**הערה:** זה חשוב",
    "- הפונקציה pthread_create יוצרת חוט",
    "- הפקודה `ls -la` מציגה קבצים",
    "| הפקודה | מה היא עושה |",
    "הפלט: נראה כך",
    "שני חוטים רצים בו-זמנית",
    "הקובץ `~/.bashrc` הוא קובץ ההגדרות",
    "מריץ את הבדיקות…",
]


@pytest.mark.parametrize("line", WRONG)
def test_wrong_lines_are_errors(rtl, line):
    errors, _ = rtl.check(line + "\n")
    assert errors, line


@pytest.mark.parametrize("line", RIGHT)
def test_right_lines_are_clean(rtl, line):
    errors, _ = rtl.check(line + "\n")
    assert errors == [], line


def test_code_blocks_are_exempt_but_neighbours_are_not(rtl):
    text = "הקוד:\n```bash\nls -la\n```\nOutput: shown above\n"
    errors, _ = rtl.check(text)
    assert [e["line"] for e in errors] == [5]


def test_suggest_fix_opens_with_hebrew_noun(rtl):
    assert rtl.suggest_fix("- `ls -la` מציג קבצים").startswith("- הפקודה `ls -la`")
    assert rtl.suggest_fix("- `malloc(size)` מקצה זיכרון").startswith("- הפונקציה `malloc(size)`")
    assert rtl.suggest_fix("~/.bashrc is הקובץ").startswith("הקובץ `~/.bashrc`")
    assert rtl.suggest_fix("**Note:** זה חשוב").startswith("**הערה:**")
    assert rtl.suggest_fix("**Train (10):** 5 אתגרים").startswith("**ה-Train (10):**")
    assert rtl.suggest_fix("3 steps בסך הכל").startswith("שלושה")
    assert rtl.suggest_fix("v2.1 adds תמיכה").startswith("גרסה 2.1")
    assert rtl.suggest_fix("https://example.com has התיעוד").startswith("הקישור https://example.com")
    assert rtl.suggest_fix("## Git Branching").startswith("## ")
    assert rtl.suggest_fix("הכל בסדר כאן") is None


def test_fix_flag_prints_suggestions_and_leaves_file_untouched(tmp_path):
    f = tmp_path / "draft.md"
    f.write_text("- `ls -la` מציג קבצים\n**Note:** זה חשוב\n", encoding="utf-8")
    before = hashlib.sha256(f.read_bytes()).hexdigest()
    proc = subprocess.run([sys.executable, str(SCRIPT), str(f), "--fix"], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "→" in proc.stdout and "הפקודה" in proc.stdout
    assert hashlib.sha256(f.read_bytes()).hexdigest() == before


def test_json_output_carries_suggestions_with_fix(tmp_path):
    f = tmp_path / "draft.md"
    f.write_text("**Note:** זה חשוב\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(SCRIPT), str(f), "--json", "--fix"], capture_output=True, text=True)
    data = json.loads(proc.stdout)
    [err] = data[str(f)]["errors"]
    assert err["suggestion"].startswith("**הערה:**")


# --- regressions from a real chat reply (Marvel summary, 2026-11-03) ---------------------------------------

def test_paragraph_opening_with_brand_name_is_error(rtl):
    errors, _ = rtl.check("## העולם של Marvel בקצרה\n\nMarvel היא חברת קומיקס שיצרה יקום בדיוני משותף.\n")
    assert [e["line"] for e in errors] == [3]


@pytest.mark.parametrize("line", [
    "- סאגת The Infinity Saga נפתחת ב-*Iron Man* (2008) ומסתיימת ב-*Avengers: Endgame* (2019), עם המאבק.",
    "- הסרט Iron Man (2008) פתח את היקום הקולנועי.",
    "- הגרסה Python 3 (2008) שברה תאימות לאחור.",
])
def test_english_name_followed_by_parenthesised_number_is_error(rtl, line):
    errors, _ = rtl.check(line + "\n")
    assert any("number in parentheses" in e["issue"] for e in errors), errors


@pytest.mark.parametrize("line", [
    "- הדמות Iron Man (Tony Stark) היא מיליארדר וממציא.",
    "- הסרט Iron Man משנת 2008 פתח את היקום הקולנועי.",
    "- מעגל RC (נגד וקבל) נטען לאט.",
])
def test_safe_parentheses_are_clean(rtl, line):
    errors, _ = rtl.check(line + "\n")
    assert errors == [], errors
