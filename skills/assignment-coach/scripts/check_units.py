#!/usr/bin/env python3
"""Check that the numbers on final-answer lines of a solution carry units.

A final-answer line is one that starts (after list markers and bold) with `תשובה`, `תשובה סופית`,
`Answer`, `Final answer`, `∴` or `=>`. Every number on such a line must be followed, within two tokens,
by a unit token: an SI symbol with an optional prefix and exponent (`m`, `kJ`, `m/s^2`), `%`, `°C`, a
currency sign, or a Hebrew/English unit word (`מטר`, `ק"מ`, `קמ"ש`, `שניות`, `ק"ג`, …). Numbers in the
middle of a derivation are left alone: only the line the grader reads as the answer is checked.

With `--expect UNIT` and `pint` installed, every unit found is also compared with the expected
dimension (`m/s` against `km/h` passes, against `kg` fails). `ratio`, `dimensionless` and `1` mean a bare
number is the right answer. Without pint the dimension check is skipped and the script says so.

Usage:
    python3 check_units.py SOLUTION.md [--expect UNIT] [--json]
Exit codes: 0 = clean, 1 = findings, 2 = file unreadable / usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pint  # type: ignore

    HAVE_PINT = True
except ImportError:  # pragma: no cover - exercised by the tests through a blocked import
    pint = None  # type: ignore
    HAVE_PINT = False

# A line is a final answer when, after Markdown list/quote markers and bold, it opens with one of these.
ANSWER_LINE = re.compile(
    r"^\s*(?:(?:[-*+>]|\d+[.)])\s+)*(?:\*\*|__)?\s*"
    r"(?:תשובה(?:\s+סופית)?|final\s+answer|answer|∴|=>)",
    re.IGNORECASE,
)

# One number, including `3 × 10^8`, `1.5e-3`, `−2`, `3,5` (decimal comma) and an uncertainty `42 ± 1`.
_PLAIN = r"[-+−]?\d+(?:[.,]\d+)?(?:[eE][-+−]?\d+)?"
_SCI = r"(?:\s*[×x\*·]\s*10\s*(?:\^\s*\{?[-+−]?\d+\}?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+))?"
NUMBER = re.compile(rf"(?<![\w.^]){_PLAIN}{_SCI}(?:\s*(?:±|\+/-|\+-)\s*{_PLAIN}{_SCI})?")

SI_PREFIXES = "Y|Z|E|P|T|G|M|k|h|da|d|c|m|µ|μ|u|n|p|f|a|z|y"
SI_BASES = (
    "m|g|s|A|K|mol|cd|N|J|W|Pa|Hz|C|V|F|Ω|ohm|S|Wb|T|H|lm|lx|Bq|Gy|Sv|kat|L|l|t|eV|bar|atm|rad|sr|"
    "h|hr|min|d|yr|dB|cal|Wh|Ah|B|bit|byte|px|psi|mmHg|ly|pc|au|°|°C|°F|%|‰|ppm|₪|\\$|€|£|NIS|USD|EUR|ILS"
)
EXPONENT = r"(?:\^\s*\{?[-+−]?\d+\}?|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)?"
UNIT_ATOM = re.compile(rf"^(?:(?:{SI_PREFIXES})?(?:{SI_BASES})){EXPONENT}$")

# Hebrew and English unit words → a pint-parsable unit (or "" when the dimension is ambiguous).
UNIT_WORDS: dict[str, str] = {
    # length
    "מטר": "m", "מטרים": "m", "מ'": "m", "ס\"מ": "cm", "מ\"מ": "mm", "ק\"מ": "km", "קילומטר": "km", "קילומטרים": "km",
    "meter": "m", "meters": "m", "metre": "m", "metres": "m", "km": "km", "cm": "cm", "mm": "mm",
    # speed
    "קמ\"ש": "km/h", "ק\"מ/שעה": "km/h", "מ'/שנ'": "m/s", "מ/ש": "m/s",
    # time
    "שנייה": "s", "שניה": "s", "שניות": "s", "שנ'": "s", "דקה": "min", "דקות": "min", "דק'": "min",
    "שעה": "h", "שעות": "h", "ימים": "day", "יום": "day",
    "second": "s", "seconds": "s", "minute": "min", "minutes": "min", "hour": "h", "hours": "h", "day": "day", "days": "day",
    # mass
    "ק\"ג": "kg", "קילוגרם": "kg", "קילו": "kg", "גרם": "g", "גרמים": "g", "מ\"ג": "mg", "טון": "t",
    "kilogram": "kg", "kilograms": "kg", "gram": "g", "grams": "g", "tonne": "t",
    # volume
    "ליטר": "L", "ליטרים": "L", "מ\"ל": "mL", "סמ\"ק": "cm^3", "liter": "L", "liters": "L", "litre": "L", "litres": "L",
    # temperature / angle (ambiguous in Hebrew: "מעלות" is both; treated as temperature difference)
    "מעלות": "", "מעלה": "", "degree": "", "degrees": "",
    # physics
    "ניוטון": "N", "ג'אול": "J", "ג׳אול": "J", "וואט": "W", "ואט": "W", "אמפר": "A", "וולט": "V", "אוהם": "ohm",
    "הרץ": "Hz", "פסקל": "Pa", "מול": "mol", "קלוריות": "cal", "קלוריה": "cal", "קלווין": "K",
    "newton": "N", "newtons": "N", "joule": "J", "joules": "J", "watt": "W", "watts": "W", "ampere": "A", "amperes": "A",
    "amp": "A", "amps": "A", "volt": "V", "volts": "V", "ohm": "ohm", "ohms": "ohm", "hertz": "Hz", "pascal": "Pa",
    "pascals": "Pa", "mole": "mol", "moles": "mol", "kelvin": "K",
    # dimensionless / money
    "אחוז": "percent", "אחוזים": "percent", "percent": "percent", "ש\"ח": "ILS", "שקל": "ILS", "שקלים": "ILS",
    "dollars": "USD", "dollar": "USD", "shekel": "ILS", "shekels": "ILS",
}
DIMENSIONLESS_EXPECT = {"ratio", "dimensionless", "1", "none", "", "unitless"}

_UREG = None


def _ureg():
    global _UREG
    if _UREG is None and HAVE_PINT:
        _UREG = pint.UnitRegistry()
        for name, sym in (("ILS", "ILS"), ("USD", "USD"), ("EUR", "EUR")):
            try:
                _UREG.define(f"{name} = [currency]" if name == "ILS" else f"{name} = 1 * ILS")
            except Exception:  # pragma: no cover - already defined or registry quirk
                pass
    return _UREG


def _normalise(token: str) -> str:
    return (token.replace("״", '"').replace("׳", "'").replace("“", '"').replace("”", '"')
            .replace("⁻", "^-").strip(" ,;:.()[]{}"))


def unit_of(token: str) -> str | None:
    """Return a pint-parsable unit string if `token` is a unit token, "" if it is a unit with ambiguous
    dimension, None if it is not a unit at all."""
    tok = _normalise(token)
    if not tok:
        return None
    if tok in UNIT_WORDS:
        return UNIT_WORDS[tok]
    # composites: m/s, km/h, kg·m/s^2, N*m
    parts = re.split(r"(/|·|⋅|\*)", tok)
    atoms = parts[0::2]
    if all(UNIT_ATOM.match(a) for a in atoms if a != ""):
        if any(a == "" for a in atoms):
            return None
        return (tok.replace("·", "*").replace("⋅", "*").replace("Ω", "ohm").replace("°C", "degC")
                .replace("°F", "degF").replace("°", "degree").replace("%", "percent").replace("₪", "ILS")
                .replace("$", "USD").replace("€", "EUR").replace("£", "GBP"))
    # Hebrew compound like ק"מ/שעה
    if "/" in tok:
        num, _, den = tok.partition("/")
        un, ud = UNIT_WORDS.get(num), UNIT_WORDS.get(den)
        if un is not None and ud is not None:
            return f"{un}/{ud}" if un and ud else ""
    return None


def _same_dimension(got: str, expected: str) -> bool | None:
    """True/False when pint can decide, None when it cannot (unparsable or ambiguous unit)."""
    ureg = _ureg()
    if ureg is None or not got:
        return None
    try:
        g = ureg.parse_expression(got.replace("^", "**"))
        if expected.lower() in DIMENSIONLESS_EXPECT:
            return g.dimensionless
        e = ureg.parse_expression(expected.replace("^", "**"))
        return g.dimensionality == e.dimensionality
    except Exception:
        return None


def _answer_part(line: str) -> str | None:
    m = ANSWER_LINE.match(line)
    return line[m.end():] if m else None


def check_units(text: str, expect: str | None = None) -> list[dict]:
    """Return findings for every final-answer line of `text`; [] means every number carries a unit (and,
    with `expect` and pint, the right kind of unit)."""
    findings: list[dict] = []
    expect_dimensionless = expect is not None and expect.strip().lower() in DIMENSIONLESS_EXPECT
    for n, line in enumerate(text.split("\n"), 1):
        rest = _answer_part(line)
        if rest is None:
            continue
        for m in NUMBER.finditer(rest):
            value = re.sub(r"\s+", " ", m.group(0)).strip()
            after = rest[m.end():]
            # unit glued to the number (5m, 300K, 50%) or within the next two whitespace tokens
            glued = re.match(r"([^\s\d,;:]+)", after)
            candidates: list[str] = []
            if glued and after[:1] not in (" ", "\t"):
                candidates.append(glued.group(1))
                after = after[glued.end():]
            candidates += after.split()[:2]
            unit = None
            for cand in candidates:
                u = unit_of(cand)
                if u is not None:
                    unit = (cand, u)
                    break
            if unit is None:
                if not expect_dimensionless:
                    findings.append({"line": n, "issue": "bare number", "value": value})
                continue
            if expect is not None and HAVE_PINT:
                same = _same_dimension(unit[1], expect.strip())
                if same is False:
                    findings.append({"line": n, "issue": "dimension mismatch", "got": _normalise(unit[0]),
                                     "expected": expect.strip()})
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="solution text (Markdown or plain text)")
    ap.add_argument("--expect", help="unit the final answer should have, e.g. km/h, kg, ratio")
    ap.add_argument("--json", action="store_true", help="print one JSON object and nothing else")
    args = ap.parse_args(argv)
    try:
        text = Path(args.file).read_text(encoding="utf-8")
    except OSError as exc:
        msg = f"cannot read {args.file}: {exc.strerror or exc}"
        print(json.dumps({"ok": False, "findings": [], "skipped": [msg]}) if args.json else msg,
              file=sys.stdout if args.json else sys.stderr)
        return 2
    skipped: list[str] = []
    if args.expect and not HAVE_PINT:
        skipped.append("pint is not installed; dimension check against --expect skipped (pip install pint)")
    findings = check_units(text, args.expect)
    if args.json:
        print(json.dumps({"ok": not findings, "findings": findings, "skipped": skipped}, ensure_ascii=False))
    else:
        for f in findings:
            if f["issue"] == "bare number":
                print(f"  line {f['line']}: bare number {f['value']} on a final-answer line")
            else:
                print(f"  line {f['line']}: unit {f['got']} does not have the dimension of {f['expected']}")
        for s in skipped:
            print("  note: " + s)
        print(f"{args.file}: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
