#!/usr/bin/env python3
"""
Prompt-injection scanner for assignment material (PDF, Office, code, text, notebooks, images, archives).

It never executes anything from the scanned files. It only reads bytes, parses formats and
reports. Run it with `python3 -I` so nothing in the scanned folder can shadow a Python module.

Usage:
    python3 -I scan.py PATH [PATH ...] [--out DIR] [--no-ocr] [--include-vendor] [--max-pages N]

Writes to --out (default ./injection-scan):
    report.md        human-readable findings, severity-sorted, plus a full file inventory
    findings.json    the same findings, machine-readable
    extracted/       for every non-plain-text file (PDF, DOCX, PPTX, XLSX, ipynb, images...), the full
                     extracted text with hidden parts marked  [[HIDDEN: reason]] ... [[/HIDDEN]]
                     so the reviewer can read EVERYTHING line by line, including layers a human never sees.
    renders/         PNG renders of PDF pages that contain suspicious hidden text (for visual confirmation)
"""
from __future__ import annotations

import argparse
import base64
import binascii
import codecs
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unicodedata
import zipfile
from collections import Counter
from dataclasses import dataclass, asdict, field
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    import pymupdf as fitz  # PyMuPDF >= 1.24
except Exception:  # pragma: no cover
    try:
        import fitz  # older PyMuPDF
    except Exception:
        fitz = None

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover
    Image = None

# --------------------------------------------------------------------------------------
# Findings
# --------------------------------------------------------------------------------------

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


@dataclass
class Finding:
    severity: str
    file: str
    location: str
    technique: str
    text: str
    detail: str = ""
    patterns: list = field(default_factory=list)


FINDINGS: list[Finding] = []
INVENTORY: list[dict] = []
MANUAL: list[str] = []
ROOTS: list[Path] = []
OUT: Path = Path("injection-scan")
OPTS = None


def rel(p: Path | str) -> str:
    p = Path(p)
    for r in ROOTS:
        try:
            return str(p.relative_to(r.parent if r.is_file() else r)) if r.is_dir() else (
                p.name if p == r else str(p))
        except ValueError:
            continue
    return str(p)


def clip(s: str, n: int = 600) -> str:
    s = s.replace("\r", "")
    return s if len(s) <= n else s[:n] + f" …[+{len(s) - n} chars]"


def add(severity, file, location, technique, text, detail="", patterns=None):
    FINDINGS.append(Finding(severity, file, str(location), technique, clip(text), detail,
                            patterns or []))


# --------------------------------------------------------------------------------------
# Injection-language detection (English + Hebrew)
# --------------------------------------------------------------------------------------

AI_NOUN = (r"(?:ai|a\.i\.|llms?|large language models?|language models?|chat ?bots?|assistants?|"
           r"gpt(?:-?\d\w*)?|chat ?gpt|claude|gemini|copilot|bard|llama|mistral|grok|deepseek|"
           r"bots?|agents?|ai models?|models?)")

AI_STRICT = (r"(?:ai|a\.i\.|llms?|large language models?|language models?|chat ?bots?|ai assistants?|"
             r"(?:the\s+)?assistants?|gpt(?:-?\d\w*)?|chat ?gpt|claude|gemini|copilot|bard|llama|grok|deepseek|"
             r"ai models?|ai agents?|coding agents?|ai tools?)")

EN_PATTERNS = [
    ("override-instructions",
     r"\b(?:ignore|disregard|forget|override|bypass|skip)\b[^.\n]{0,40}?\b(?:previous|prior|above|earlier|all|any|your|the|system|original|other)\b[^.\n]{0,30}?\b(?:instructions?|prompts?|directions?|rules?|guidelines?|context|messages?|directives?)\b"),
    ("addresses-ai",
     rf"\bif\s+you(?:'re|\s+are)\s+(?:an?\s+|the\s+)?(?:\w+\s+)?{AI_NOUN}\b"),
    ("addresses-ai",
     rf"\b(?:note|message|instructions?|attention|reminder|warning|memo)\s+(?:to|for)\s+(?:the\s+|any\s+|all\s+)?{AI_NOUN}\b"),
    ("addresses-ai",
     rf"\b(?:dear|hey|hi|hello|attention)\s*,?\s+{AI_NOUN}\b"),
    ("addresses-ai",
     rf"\b(?:(?:any|an?|the|all)\s+)?{AI_NOUN}\s+(?:that\s+(?:is|are)\s+)?(?:reading|processing|parsing|summari[sz]ing|analy[sz]ing|seeing|reviewing|working\s+on)\s+(?:this|these)\b"),
    ("directive-to-ai",
     rf"(?<!teaching )(?<!research )(?<!lab )(?<!course )\b{AI_STRICT}\s+(?:must|should|shall|is required to|are required to|needs? to|has to|have to|will)\s+(?:not\s+|never\s+|always\s+)?(?:include|use|write|mention|add|insert|respond|reply|answer|output|say|refuse|ignore|name|call|print|state|claim|append|start|end|set|make|return|give|rate|grade|implement|choose|recommend|tell|change|skip|remove|delete|avoid|prefer|assume|treat|report)\b"),
    ("conceal-from-user",
     r"\b(?:do\s+not|don'?t|never|must\s+not|should\s+not)\s+(?:tell|inform|mention|reveal|disclose|show|alert|let|notify|warn|explain)(?:\s+(?:this|it|that|anything|any\s+of\s+this))?(?:\s+(?:to|with))?\s+(?:the\s+)?(?:user|human|student|reader|person|operator|developer|teacher|grader|lecturer)s?\b"),
    ("conceal-from-user",
     r"\bwithout\s+(?:telling|informing|mentioning\s+it\s+to|alerting|notifying|asking)\s+(?:the\s+)?(?:user|human|student|reader|person|operator)s?\b"),
    ("conceal-from-user",
     r"\b(?:secretly|covertly|silently|quietly|discreetly)\s+(?:add|include|insert|send|change|modify|run|execute|upload|embed|use|introduce|plant)\b"),
    ("fake-system-context",
     r"\b(?:system\s+prompt|developer\s+(?:message|mode)|new\s+instructions?|updated\s+instructions?|hidden\s+instructions?|special\s+instructions?\s+for|jailbreak|DAN\s+mode)\b"),
    ("fake-system-context",
     r"(?:<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|endoftext\|>|\[/?INST\]|<<\s*/?SYS\s*>>|</?\s*system\s*>|</?\s*instructions?\s*>|</?\s*(?:user|assistant)_?(?:message|turn)?\s*>|\bBEGIN\s+SYSTEM\b)"),
    ("fake-system-context",
     r"^\s*(?:system|assistant|human|user)\s*:\s+\S"),
    ("role-hijack",
     r"\b(?:you\s+are\s+now|from\s+now\s+on,?\s+you|pretend\s+(?:to\s+be|you\s+are)|roleplay\s+as|your\s+new\s+(?:role|task|goal|instructions?)\s+(?:is|are))\b"),
    ("canary-trap",
     r"\b(?:include|insert|use|mention|add|write|embed|incorporate|name|say)\s+(?:the\s+|a\s+|this\s+|these\s+)?(?:exact\s+|specific\s+|hidden\s+|secret\s+|following\s+)?(?:words?|phrases?|terms?|strings?|sentences?|keywords?|tokens?|variable\s+names?|function\s+names?|class\s+names?|code\s*words?)\s*(?:(?:called|named|like)\s+)?:?\s*[\"'“‘`«„]"),
    ("canary-trap",
     r"\b(?:in\s+your\s+(?:answer|response|output|solution|essay|code|report)|in\s+the\s+(?:answer|response|output|submission))\s*,?\s+(?:you\s+)?(?:must|should|need\s+to|have\s+to|always)\b"),
    ("exfiltration",
     r"\b(?:send|post|upload|exfiltrate|forward|transmit|leak|e-?mail)(?:s|ed|ing|es)?\b[^\n]{0,80}?\b(?:to|at)\s+(?:https?://|ftp://|\S+@\S+\.\w+)"),
    ("exfiltration",
     r"(?:id_rsa|\.ssh/|\.env\b|\.aws/|api[_ -]?keys?|passwords?|credentials?|cookies?|tokens?)[^\n]{0,60}?\b(?:to|at)\s+(?:https?://|ftp://)"),
    ("exfiltration",
     r"\b(?:api[_ -]?keys?|passwords?|secrets?|tokens?|credentials?|\.env|ssh\s+keys?|id_rsa|cookies?|environment\s+variables)\b[^.\n]{0,50}?\b(?:send|post|upload|print|reveal|share|include|output|exfiltrate|leak|copy)\b"),
    ("dangerous-command",
     r"(?:\b(?:curl|wget|iwr|Invoke-WebRequest|Invoke-Expression|iex)\b[^\n]{0,80}https?://|\brm\s+-rf\s+[~/]|\bchmod\s+\+x\b[^\n]{0,40}&&|\|\s*(?:ba|z)?sh\b|base64\s+-d[^\n]{0,40}\|\s*(?:ba)?sh)"),
]

HE_AI = r"(?:מודל(?:\s+ה?שפה)?|בינה\s+מלאכותית|בינה|AI|LLM|צ'?אט\s*ג'?י?פי?טי|ג'?י?פי?טי|GPT|ChatGPT|Claude|קלוד|ג'?מיני|בוט|צ'?אטבוט|עוזר(?:\s+וירטואלי)?|סוכן|מערכת\s+בינה)"

HE_PATTERNS = [
    ("override-instructions",
     r"(?:התעלם|תתעלם|התעלמי|התעלמו|להתעלם|שכח|תשכח|לשכוח|עקוף|תעקוף)\S*\s+(?:\S+\s+){0,4}?(?:מ?ה?הוראו?ת|מ?ה?הנחיו?ת|מ?ה?כללים|מ?ה?פקודו?ת|מ?ה?הקשר)"),
    ("addresses-ai", rf"אם\s+(?:אתה|את|הנך|אתם)\s+(?:\S+\s+){{0,2}}?{HE_AI}"),
    ("addresses-ai", rf"(?:הוראה|הוראות|הודעה|הערה|תזכורת)\s+(?:ל|עבור\s+|אל\s+)(?:ה)?{HE_AI}"),
    ("addresses-ai", rf"(?:ל|אל\s+)(?:כל\s+)?(?:ה)?{HE_AI}\s+(?:ה)?(?:קורא|קוראת|שקורא|המעבד|שמעבד)"),
    ("directive-to-ai", rf"{HE_AI}\s+(?:\S+\s+){{0,2}}?(?:חייב|חייבת|צריך|צריכה|עליו|עליה|נדרש|יש\s+ל|אסור\s+ל|אל\s+)"),
    ("conceal-from-user",
     r"(?:אל|לא|אסור)\s+(?:ל|ת)?(?:ספר|גלה|ציין|זכיר|זכור|ודיע|יידע|הראות|ראה)\S*\s+(?:\S+\s+){0,2}?(?:ל?(?:ה)?משתמש|ל?(?:ה)?סטודנט|ל?(?:ה)?אדם|ל?(?:ה)?קורא|ל?(?:ה)?בודק|ל?(?:ה)?מרצה)"),
    ("conceal-from-user", r"(?:בלי|מבלי)\s+ש(?:ה)?(?:משתמש|סטודנט|אדם|קורא|בודק)\s+(?:\S+\s+){0,2}?(?:ידע|יבחין|ישים\s+לב|יראה)"),
    ("conceal-from-user", r"(?:בסתר|בחשאי|בשקט|באופן\s+סמוי)\s+(?:\S+\s+){0,1}?(?:הוסף|הכנס|שלח|שנה|הרץ|כלול|תוסיף|תכניס|תשלח)"),
    ("role-hijack", r"(?:מעכשיו|מעתה|החל\s+מעכשיו)\s+(?:אתה|את|תפעל|תהיה)"),
    ("canary-trap",
     r"(?:כלול|תכלול|הכנס|תכניס|השתמש|תשתמש|שלב|תשלב|הוסף|תוסיף|ציין|תציין|כתוב|תכתוב)\s+(?:\S+\s+){0,2}?(?:את\s+)?(?:ה)?(?:מילה|מילים|ביטוי|משפט|מחרוזת|שם\s+(?:ה)?משתנה|שם\s+(?:ה)?פונקציה|מילת\s+קוד)"),
    ("canary-trap", r"(?:בתשובה|בתשובתך|בפתרון|בקוד|בעבודה|בתשובות)\s+(?:\S+\s+){0,2}?(?:חובה|יש\s+ל|עליך|תמיד|הקפד)"),
    ("fake-system-context", r"(?:הנחיות|הוראות)\s+(?:מערכת|חדשות|מעודכנות|סודיות|נסתרות)"),
]

COMPILED = [(n, re.compile(p, re.IGNORECASE | re.MULTILINE)) for n, p in EN_PATTERNS + HE_PATTERNS]

# Patterns that are directives on their own; others need a second signal to be "high".
STRONG = {"override-instructions", "addresses-ai", "conceal-from-user", "fake-system-context",
          "role-hijack", "directive-to-ai", "exfiltration"}


def match_patterns(text: str) -> list[tuple[str, str]]:
    hits = []
    if not text or len(text) < 6:
        return hits
    for name, rx in COMPILED:
        for m in rx.finditer(text):
            hits.append((name, m.group(0).strip()))
            break
    return hits


def classify(hits, hidden: bool, sensitive_place: bool = False) -> str | None:
    """Map pattern hits + context to a severity."""
    names = {n for n, _ in hits}
    if not names:
        return None
    strong = bool(names & STRONG)
    if hidden and (strong or "canary-trap" in names):
        return "CRITICAL"
    if hidden:
        return "HIGH"
    if strong and (sensitive_place or len(names) >= 2):
        return "HIGH"
    if strong:
        return "MEDIUM"
    if sensitive_place:
        return "MEDIUM"
    return "LOW"


def report_text(file, loc, text, technique, hidden, detail="", sensitive=False, base_sev=None):
    """Scan `text` for injection language. Hidden content is reported even without a match."""
    hits = match_patterns(text)
    sev = classify(hits, hidden, sensitive)
    pats = [f"{n}: “{clip(h, 80)}”" for n, h in hits]
    if sev:
        add(sev, file, loc, technique, text, detail, pats)
        return True
    if base_sev:
        add(base_sev, file, loc, technique, text, detail, pats)
        return True
    return False


# --------------------------------------------------------------------------------------
# Unicode tricks
# --------------------------------------------------------------------------------------

ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064, 0xFEFF, 0x180E, 0x00AD,
              0x034F, 0x115F, 0x1160, 0x3164, 0xFFA0, 0x2800}
BIDI_OVERRIDE = {0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069}
BIDI_MARKS = {0x200E, 0x200F, 0x061C}  # LRM/RLM: normal in Hebrew/Arabic text
TAG_RANGE = range(0xE0000, 0xE0080)
VS_RANGES = (range(0xFE00, 0xFE10), range(0xE0100, 0xE01F0))


def unicode_scan(file: str, line_no: int, line: str, is_code: bool):
    tags = [c for c in line if ord(c) in TAG_RANGE]
    if tags:
        decoded = "".join(chr(ord(c) - 0xE0000) for c in tags if 0x20 <= ord(c) - 0xE0000 < 0x7F)
        add("CRITICAL", file, f"line {line_no}", "Unicode TAG characters (invisible 'ASCII smuggling')",
            decoded or "(tag chars present, nothing printable)",
            f"{len(tags)} invisible tag characters; decoded payload shown above",
            [f"{n}: “{h}”" for n, h in match_patterns(decoded)])
    vs = [c for c in line if any(ord(c) in r for r in VS_RANGES)]
    if len(vs) >= 4:
        add("HIGH", file, f"line {line_no}", "Variation-selector run (possible data smuggling inside emoji/char)",
            line.strip()[:200], f"{len(vs)} variation selectors on one line")
    zw = [c for c in line if ord(c) in ZERO_WIDTH and not (ord(c) == 0xFEFF and line_no == 1 and line.startswith(c))]
    if zw:
        cnt = Counter(f"U+{ord(c):04X}" for c in zw)
        sev = "HIGH" if len(zw) >= 8 else "MEDIUM" if (is_code or len(zw) >= 3) else "LOW"
        bits = "".join("1" if ord(c) == 0x200C else "0" if ord(c) == 0x200B else "" for c in zw)
        extra = ""
        if len(bits) >= 8:
            try:
                b = int(bits, 2).to_bytes(len(bits) // 8, "big").decode("utf-8", "ignore")
                if b.strip():
                    extra = f"; ZW-binary decode attempt: {b[:120]!r}"
            except Exception:
                pass
        add(sev, file, f"line {line_no}", "Zero-width / invisible characters",
            repr(line.strip())[:300], f"{dict(cnt)}{extra}")
    bo = [c for c in line if ord(c) in BIDI_OVERRIDE]
    if bo:
        add("HIGH" if is_code else "MEDIUM", file, f"line {line_no}",
            "Bidirectional override characters (Trojan-Source: displayed text ≠ actual text)",
            repr(line.strip())[:300], ", ".join(f"U+{ord(c):04X}" for c in bo))
    other_cf = [c for c in line if unicodedata.category(c) == "Cf" and ord(c) not in ZERO_WIDTH
                and ord(c) not in BIDI_OVERRIDE and ord(c) not in BIDI_MARKS and ord(c) not in TAG_RANGE]
    if len(other_cf) >= 3:
        add("LOW", file, f"line {line_no}", "Unusual format-control characters",
            repr(line.strip())[:200], ", ".join(sorted({f"U+{ord(c):04X}" for c in other_cf})))
    # homoglyphs: one word mixing Latin with Cyrillic/Greek
    for w in re.findall(r"\w{3,}", line):
        scripts = set()
        for ch in w:
            if ch.isalpha():
                n = unicodedata.name(ch, "")
                scripts.add("LATIN" if n.startswith("LATIN") else "CYRILLIC" if n.startswith("CYRILLIC")
                            else "GREEK" if n.startswith("GREEK") else "OTHER")
        if "LATIN" in scripts and (scripts & {"CYRILLIC", "GREEK"}):
            add("MEDIUM" if is_code else "LOW", file, f"line {line_no}",
                "Homoglyph word (Latin mixed with Cyrillic/Greek look-alikes)", w,
                "A word that looks normal but contains look-alike letters; can dodge keyword filters or "
                "make two identifiers look identical")
            break


def strip_invisible(s: str) -> str:
    return "".join(c for c in s if not (ord(c) in ZERO_WIDTH or ord(c) in BIDI_OVERRIDE
                                        or ord(c) in TAG_RANGE or unicodedata.category(c) == "Cf"))


# --------------------------------------------------------------------------------------
# Encoded payloads
# --------------------------------------------------------------------------------------

B64_RX = re.compile(r"(?<![A-Za-z0-9+/=_-])([A-Za-z0-9+/]{32,}={0,2}|[A-Za-z0-9_-]{40,}={0,2})(?![A-Za-z0-9+/=_-])")
HEX_RX = re.compile(r"(?<![0-9A-Fa-f])((?:[0-9A-Fa-f]{2}){24,})(?![0-9A-Fa-f])")
ESC_RX = re.compile(r"((?:\\x[0-9A-Fa-f]{2}|\\u[0-9A-Fa-f]{4}|&#x?[0-9A-Fa-f]+;|%[0-9A-Fa-f]{2}){12,})")


def printable_ratio(s: str) -> float:
    if not s:
        return 0
    return sum(1 for c in s if c.isprintable() or c in "\n\t") / len(s)


def decode_payloads(text: str):
    """Yield (kind, decoded) for encoded blobs that decode to human text."""
    for m in B64_RX.finditer(text):
        blob = m.group(1)
        for dec in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                raw = dec(blob + "=" * (-len(blob) % 4))
                s = raw.decode("utf-8")
            except Exception:
                continue
            if printable_ratio(s) > 0.95 and len(s.split()) >= 3:
                yield "base64", s
            break
    for m in HEX_RX.finditer(text):
        try:
            s = binascii.unhexlify(m.group(1)).decode("utf-8")
            if printable_ratio(s) > 0.95 and len(s.split()) >= 3:
                yield "hex", s
        except Exception:
            pass
    for m in ESC_RX.finditer(text):
        blob = m.group(1)
        try:
            import html
            import urllib.parse
            s = html.unescape(blob)
            s = urllib.parse.unquote(s)
            s = codecs.decode(s.encode("latin-1", "backslashreplace"), "unicode_escape")
            if printable_ratio(s) > 0.9 and len(s.split()) >= 3:
                yield "escaped", s
        except Exception:
            pass


def rot13_check(text: str):
    if len(text) < 30:
        return None
    r = codecs.decode(text, "rot13")
    hits = match_patterns(r)
    if hits and not match_patterns(text):
        return r
    return None


# --------------------------------------------------------------------------------------
# File-type routing
# --------------------------------------------------------------------------------------

CODE_EXT = {".py", ".pyw", ".ipynb", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".java", ".kt", ".kts",
            ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".cs", ".go", ".rs", ".rb", ".php", ".pl",
            ".pm", ".swift", ".m", ".mm", ".scala", ".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1",
            ".bat", ".cmd", ".lua", ".r", ".jl", ".hs", ".ml", ".fs", ".ex", ".exs", ".erl", ".clj",
            ".dart", ".vue", ".svelte", ".sql", ".asm", ".s", ".v", ".sv", ".vhd", ".vhdl", ".zig",
            ".nim", ".groovy", ".gradle", ".cmake", ".mk", ".makefile", ".dockerfile", ".tf", ".hcl",
            ".proto", ".sol", ".ada", ".adb", ".f90", ".f", ".pas", ".lisp", ".scm", ".rkt", ".coq",
            ".lean", ".thy", ".tla", ".dfy", ".agda", ".idr", ".prolog", ".pro"}
MARKUP_EXT = {".md", ".markdown", ".mdx", ".rst", ".txt", ".text", ".adoc", ".org", ".tex", ".bib",
              ".sty", ".cls", ".html", ".htm", ".xhtml", ".xml", ".svg", ".json", ".jsonl", ".yaml",
              ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".csv", ".tsv", ".properties", ".log",
              ".css", ".scss", ".less", ".rtf", ".srt", ".vtt", ".gitignore", ".gitattributes",
              ".editorconfig", ".lock", ".po", ".pot", ".tex", ".lst"}
OOXML_EXT = {".docx", ".docm", ".dotx", ".dotm", ".pptx", ".pptm", ".potx", ".ppsx", ".xlsx", ".xlsm",
             ".xltx", ".xltm"}
ODF_EXT = {".odt", ".ods", ".odp", ".ott", ".epub"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic"}
ARCHIVE_EXT = {".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".tbz2", ".txz", ".jar", ".whl", ".7z", ".rar"}
LEGACY_OFFICE = {".doc", ".ppt", ".xls", ".rtf"}

AGENT_FILES = {
    "claude.md", "agents.md", "agent.md", "gemini.md", ".cursorrules", ".windsurfrules", ".clinerules",
    "copilot-instructions.md", ".mcp.json", "mcp.json", ".aider.conf.yml", "codex.md", ".roorules",
    "conventions.md",
}
AGENT_DIRS = {".claude", ".cursor", ".github", ".windsurf", ".vscode", ".idea", ".devcontainer", ".husky",
              ".continue", ".roo", ".clinerules"}
AUTORUN_NAMES = {"package.json", "setup.py", "setup.cfg", "pyproject.toml", "makefile", "gnumakefile",
                 "conftest.py", "tasks.json", "launch.json", "settings.json", "devcontainer.json",
                 ".pre-commit-config.yaml", "noxfile.py", "tox.ini", "build.gradle", "pom.xml",
                 "cmakelists.txt", "dockerfile", "docker-compose.yml", "justfile", "rakefile",
                 "__init__.py", "sitecustomize.py", "usercustomize.py", ".envrc"}
VENDOR_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", "env", ".tox", ".mypy_cache",
               ".pytest_cache", "dist", "build", "target", ".gradle", ".next", "site-packages", ".idea"}


def ext_of(p: Path) -> str:
    n = p.name.lower()
    if n.endswith((".tar.gz", ".tar.bz2", ".tar.xz")):
        return ".tar"
    if n in ("makefile", "dockerfile", "gnumakefile", "justfile", "rakefile", "vagrantfile"):
        return "." + n
    return p.suffix.lower()


def is_binary(data: bytes) -> bool:
    if not data:
        return False
    if data.startswith((b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf")):
        return False
    return b"\x00" in data[:8192]


def decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1255", "latin-1"):
        try:
            if enc == "utf-16" and not data.startswith((b"\xff\xfe", b"\xfe\xff")):
                continue
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", "replace")


# --------------------------------------------------------------------------------------
# Plain text / code
# --------------------------------------------------------------------------------------

HIDE_STYLE_RX = re.compile(
    r"(display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0*(?:\.\d+)?(?:px|pt|em|rem)?\s*[;\"']|"
    r"font-size\s*:\s*[01](?:\.\d+)?px|opacity\s*:\s*0(?:\.0\d*)?\s*[;\"']|"
    r"color\s*:\s*(?:white|#fff(?:fff)?\b|rgba?\(\s*255\s*,\s*255\s*,\s*255)|"
    r"(?:left|top|text-indent|margin-left)\s*:\s*-\d{3,}|clip\s*:\s*rect\(0|height\s*:\s*0(?:px)?\s*;\s*overflow\s*:\s*hidden|"
    r"\bhidden\b(?=[\s>])|aria-hidden\s*=\s*[\"']true|fill\s*=\s*[\"'](?:white|#fff(?:fff)?)[\"']|"
    r"fill-opacity\s*[:=]\s*[\"']?0(?:\.0+)?\b|font-size\s*=\s*[\"']0)", re.IGNORECASE)
LATEX_HIDE_RX = re.compile(
    r"(\\(?:text)?color\s*\{\s*white\s*\}|\\color\[rgb\]\{1,\s*1,\s*1\}|\\phantom\{|\\transparent\{0|"
    r"\\pdfrender\{[^}]*invisible|\\fontsize\{0|\\scalebox\{0(?:\.0\d*)?\}|\\resizebox\{0|"
    r"\\iffalse|\\begin\{comment\}|\\renewcommand\\.*\{\}|\\pdfliteral)", re.IGNORECASE)
HTML_COMMENT_RX = re.compile(r"<!--(.*?)-->", re.DOTALL)
MD_REFCOMMENT_RX = re.compile(r"^\s*\[(?:[^\]]*)\]:\s*(?:#|<>|\S+)\s*[\"'(](.+)[\"')]\s*$", re.MULTILINE)
MD_BEACON_RX = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+[?&][^)\s]*=[^)\s]*)\)")
OFFSCREEN_RX = re.compile(r"\S[ \t]{100,}\S|^[ \t]{150,}\S")


def scan_text_content(file: str, text: str, ext: str, sensitive: bool, hidden_ctx: str | None = None):
    is_code = ext in CODE_EXT
    lines = text.split("\n")
    for i, line in enumerate(lines, 1):
        if len(line) > 20000:
            add("MEDIUM", file, f"line {i}", "Extremely long line (content can sit far off-screen)",
                line[:200], f"{len(line)} characters on one line")
            seg = line
        else:
            seg = line
        unicode_scan(file, i, seg[:20000], is_code)
        clean = strip_invisible(seg)
        hits = match_patterns(clean)
        if hits:
            hidden = bool(hidden_ctx)
            sev = classify(hits, hidden, sensitive or is_code)
            ctx = "code comment / string" if is_code else "text"
            add(sev, file, f"line {i}",
                f"Injection-style language in {hidden_ctx or ctx}", clean.strip(),
                "", [f"{n}: “{clip(h, 80)}”" for n, h in hits])
        if OFFSCREEN_RX.search(seg):
            add("MEDIUM", file, f"line {i}", "Text pushed off-screen by long whitespace run",
                seg.strip()[:400], "Editors/viewers often won't show text after hundreds of spaces")
        for kind, dec in decode_payloads(seg):
            h = match_patterns(dec)
            add("CRITICAL" if h else "LOW", file, f"line {i}", f"Encoded text ({kind}) decodes to readable text",
                dec, "", [f"{n}: “{clip(x, 80)}”" for n, x in h])
        r13 = rot13_check(clean)
        if r13:
            add("HIGH", file, f"line {i}", "ROT13-encoded instruction", r13)

    # multi-line constructs
    if ext in {".md", ".markdown", ".mdx", ".html", ".htm", ".xhtml", ".svg", ".xml", ".txt", ".rst",
               ".vue", ".svelte", ".jsx", ".tsx", ".php"} or ext in {".ipynb"}:
        for m in HTML_COMMENT_RX.finditer(text):
            body = m.group(1).strip()
            if len(body.split()) < 3:
                continue
            ln = text.count("\n", 0, m.start()) + 1
            hits = match_patterns(body)
            if hits:
                add(classify(hits, True), file, f"line {ln}", "HTML/Markdown comment (not rendered)", body,
                    "", [f"{n}: “{clip(h, 80)}”" for n, h in hits])
            elif ext in {".md", ".markdown", ".mdx", ".rst", ".txt"} and len(body.split()) >= 6:
                add("LOW", file, f"line {ln}", "HTML comment in Markdown (invisible when rendered)", body)
        for m in MD_REFCOMMENT_RX.finditer(text):
            ln = text.count("\n", 0, m.start()) + 1
            report_text(file, f"line {ln}", m.group(1), "Markdown reference-style comment (not rendered)",
                        True, base_sev="LOW")
        for m in MD_BEACON_RX.finditer(text):
            ln = text.count("\n", 0, m.start()) + 1
            add("MEDIUM", file, f"line {ln}", "Remote image with query parameters (possible exfiltration beacon)",
                m.group(1), "If an AI renders this image, data placed in the URL is sent to that server")
    if ext in {".md", ".markdown", ".mdx", ".html", ".htm", ".xhtml", ".svg", ".txt", ".rst", ".xml"}:
        for i, line in enumerate(lines, 1):
            m = HIDE_STYLE_RX.search(line)
            if m:
                visible_words = re.sub(r"<[^>]+>", " ", line)
                words = len(re.findall(r"[^\W\d_]{2,}", visible_words))
                if ext in {".html", ".htm", ".xhtml"} and words < 4 and i < len(lines):
                    nxt = re.sub(r"<[^>]+>", " ", " ".join(lines[i:i + 3]))
                    words = len(re.findall(r"[^\W\d_]{2,}", nxt))
                    if words < 4:
                        continue
                body = re.sub(r"<[^>]+>", " ", " ".join(lines[i - 1:i + 3]))
                hits = match_patterns(body)
                add(classify(hits, True) if hits else "LOW", file, f"line {i}",
                    f"Content styled to be invisible ({m.group(1).strip()})", body.strip(),
                    "", [f"{n}: “{clip(h, 80)}”" for n, h in hits])
    if ext in {".tex", ".sty", ".cls", ".bib"}:
        for i, line in enumerate(lines, 1):
            m = LATEX_HIDE_RX.search(line)
            if m:
                body = " ".join(lines[i - 1:i + 3])
                hits = match_patterns(body)
                add(classify(hits, True) if hits else "MEDIUM", file, f"line {i}",
                    f"LaTeX hiding construct ({m.group(1)})", body.strip(), "Renders invisibly in the PDF",
                    [f"{n}: “{clip(h, 80)}”" for n, h in hits])


def scan_plain(path: Path, data: bytes, display: str):
    text = decode_text(data)
    ext = ext_of(path)
    name = path.name.lower()
    parts = {p.lower() for p in path.parts}
    sensitive = False
    if name in AGENT_FILES or (parts & AGENT_DIRS) or "/.git/hooks/" in str(path).replace("\\", "/"):
        sensitive = True
        add("MEDIUM", display, "whole file",
            "AI-agent / IDE configuration file (read automatically by coding agents)",
            text[:500], "Files like CLAUDE.md, AGENTS.md, .cursorrules, .claude/*, .vscode/*, .github/copilot-"
                        "instructions.md are loaded as instructions by agents. Read the whole file.")
    if name in AUTORUN_NAMES:
        sensitive = True
        if name == "package.json":
            try:
                j = json.loads(text)
                sc = j.get("scripts", {}) or {}
                for k in ("preinstall", "install", "postinstall", "prepare", "prepublish", "pretest"):
                    if k in sc:
                        add("MEDIUM", display, f"scripts.{k}", "Auto-run npm lifecycle script", sc[k],
                            "Runs automatically on npm install/test")
            except Exception:
                pass
        if name == "tasks.json" and "folderOpen" in text:
            add("HIGH", display, "runOn", "VS Code task set to run automatically when the folder opens",
                text[:400])
    if path.suffix.lower() == ".rtf":
        for m in re.finditer(r"\\v(?![a-z])\s?(.{0,400}?)\\v0", text, re.DOTALL):
            report_text(display, "rtf", m.group(1), "RTF hidden text (\\v)", True, base_sev="MEDIUM")
    if path.suffix.lower() == ".ipynb":
        return scan_notebook(path, text, display)
    scan_text_content(display, text, ext, sensitive)


# --------------------------------------------------------------------------------------
# Notebooks
# --------------------------------------------------------------------------------------

def scan_notebook(path: Path, text: str, display: str):
    try:
        nb = json.loads(text)
    except Exception:
        return scan_text_content(display, text, ".json", False)
    dump = []
    md = json.dumps(nb.get("metadata", {}), ensure_ascii=False)
    report_text(display, "notebook metadata", md, "Notebook metadata (not shown in the UI)", True)
    for ci, cell in enumerate(nb.get("cells", [])):
        src = "".join(cell.get("source", [])) if isinstance(cell.get("source"), list) else cell.get("source", "")
        ctype = cell.get("cell_type", "?")
        dump.append(f"\n===== cell {ci} [{ctype}] =====\n{src}")
        sub_ext = ".md" if ctype == "markdown" else ".py"
        before = len(FINDINGS)
        scan_text_content(f"{display} › cell {ci}", src, sub_ext, False)
        meta = cell.get("metadata", {})
        if meta:
            if meta.get("jupyter", {}).get("source_hidden") or meta.get("collapsed") or \
                    "hide-input" in json.dumps(meta) or "remove-cell" in json.dumps(meta):
                report_text(display, f"cell {ci}", src, "Notebook cell marked hidden/collapsed", True,
                            base_sev="MEDIUM")
            report_text(display, f"cell {ci} metadata", json.dumps(meta, ensure_ascii=False),
                        "Cell metadata (not shown in the UI)", True)
        for oi, out in enumerate(cell.get("outputs", []) or []):
            blob = []
            for k in ("text",):
                if k in out:
                    blob.append("".join(out[k]) if isinstance(out[k], list) else str(out[k]))
            for mime, v in (out.get("data") or {}).items():
                if mime.startswith("text/") or mime.endswith("json"):
                    blob.append("".join(v) if isinstance(v, list) else str(v))
            s = "\n".join(blob)
            if s.strip():
                dump.append(f"--- cell {ci} output {oi} ---\n{s}")
                scan_text_content(f"{display} › cell {ci} output {oi}", s,
                                  ".html" if "<" in s else ".txt", False, hidden_ctx="stored cell output")
    write_extracted(display, "\n".join(dump))


# --------------------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------------------

def _to_rgb(color, cs):
    if color is None:
        return (0, 0, 0)
    if isinstance(color, (int, float)):
        color = (color,)
    color = tuple(color)
    if len(color) == 1:
        return (color[0],) * 3
    if len(color) == 3:
        return color
    if len(color) == 4:
        c, m, y, k = color
        return ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
    return (0, 0, 0)


def _lum(rgb):
    def ch(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def have_tesseract():
    return shutil.which("tesseract") is not None


def tess_langs():
    try:
        out = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=20).stdout
        langs = set(out.split()[1:]) if out else set()
        use = [l for l in ("eng", "heb") if l in langs]
        return "+".join(use) or "eng"
    except Exception:
        return "eng"


def ocr_png(png_bytes: bytes) -> str:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "p.png"
        p.write_bytes(png_bytes)
        try:
            r = subprocess.run(["tesseract", str(p), "stdout", "-l", tess_langs(), "--psm", "3"],
                               capture_output=True, text=True, timeout=120)
            return r.stdout
        except Exception:
            return ""


def words_of(s):
    return [w.lower() for w in re.findall(r"[^\W\d_]{3,}", s)]


def scan_pdf(path: Path, data: bytes, display: str):
    if fitz is None:
        return scan_pdf_fallback(path, data, display)
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        MANUAL.append(f"{display}: could not open PDF ({e})")
        return
    if doc.needs_pass:
        MANUAL.append(f"{display}: encrypted PDF — open it yourself or provide the password")
        return
    dump = []
    # metadata
    meta = {k: v for k, v in (doc.metadata or {}).items() if v}
    if meta:
        dump.append("===== METADATA =====\n" + json.dumps(meta, ensure_ascii=False, indent=1))
        for k, v in meta.items():
            report_text(display, f"metadata:{k}", str(v), "PDF metadata field (not shown on the page)", True)
    try:
        xmp = doc.get_xml_metadata()
        if xmp:
            txt = re.sub(r"<[^>]+>", " ", xmp)
            report_text(display, "XMP metadata", " ".join(txt.split()), "PDF XMP metadata", True)
    except Exception:
        pass
    # JavaScript / auto actions / embedded files / hidden layers
    try:
        js_hits = []
        for x in range(1, doc.xref_length()):
            try:
                o = doc.xref_object(x, compressed=False)
            except Exception:
                continue
            if "/JavaScript" in o or "/JS " in o or "/JS(" in o or "/JS<" in o:
                js_hits.append(x)
            if "/Launch" in o or "/SubmitForm" in o or "/ImportData" in o:
                add("HIGH", display, f"xref {x}", "PDF action that launches/submits/imports", o[:300])
        if js_hits:
            add("MEDIUM", display, f"xrefs {js_hits[:10]}", "Embedded JavaScript in PDF",
                doc.xref_object(js_hits[0])[:400])
    except Exception:
        pass
    try:
        for name in doc.embfile_names():
            emb = doc.embfile_get(name)
            add("MEDIUM", display, f"embedded file '{name}'", "File embedded inside the PDF",
                f"{len(emb)} bytes", "Scanned recursively below")
            scan_bytes(Path(name), emb, f"{display} › {name}")
    except Exception:
        pass
    try:
        ocgs = doc.get_ocgs() or {}
        off = [v.get("name") for v in ocgs.values() if not v.get("on", True)]
        if off:
            add("MEDIUM", display, "optional content", "PDF layers switched off (hidden layers)", ", ".join(map(str, off)))
    except Exception:
        pass
    try:
        if doc.is_form_pdf:
            for page in doc:
                for w in page.widgets() or []:
                    v = f"{w.field_name}: {w.field_value}"
                    report_text(display, f"page {page.number + 1} form field", v, "PDF form field value", True)
    except Exception:
        pass

    do_ocr = have_tesseract() and not OPTS.no_ocr
    if not do_ocr:
        MANUAL.append(f"{display}: OCR cross-check skipped (no tesseract or --no-ocr) — text hidden behind "
                      f"images/shapes may be missed; render pages and look at them")
    flagged_pages = set()
    for page in doc:
        pno = page.number + 1
        if pno > OPTS.max_pages:
            MANUAL.append(f"{display}: only first {OPTS.max_pages} pages deeply scanned")
            break
        prect = page.rect
        dump.append(f"\n===== page {pno} =====")
        try:
            trace = page.get_texttrace()
        except Exception:
            trace = []
        # background sampling
        scale = 2
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            samples, pw, ph, n = pix.samples, pix.width, pix.height, pix.n
        except Exception:
            pix = None
        # images covering page (scanned PDF → invisible OCR layer is normal)
        try:
            img_area = sum(fitz.Rect(i["bbox"]).get_area() for i in page.get_image_info())
        except Exception:
            img_area = 0
        scanned_like = img_area > 0.6 * prect.get_area()
        try:
            draws = [d for d in page.get_drawings() if d.get("fill") is not None]
        except Exception:
            draws = []

        ocr_words = None
        if do_ocr and trace:
            try:
                ocr_words = set(words_of(ocr_png(page.get_pixmap(dpi=200).tobytes("png"))))
            except Exception:
                ocr_words = None

        page_lines = []
        invisible_ocr_chars = 0
        for sp in trace:
            txt = "".join(chr(c[0]) for c in sp.get("chars", []) if c[0] >= 0)
            if not txt.strip():
                continue
            bbox = fitz.Rect(sp["bbox"])
            reasons = []
            rmode = sp.get("type", 0)
            size = sp.get("size", 10)
            opacity = sp.get("opacity", 1)
            rgb = _to_rgb(sp.get("color"), sp.get("colorspace"))
            if rmode == 3:
                if scanned_like:
                    invisible_ocr_chars += len(txt)
                    # still check for directives inside an OCR layer
                    if match_patterns(txt):
                        reasons.append("invisible render mode (inside scanned-page OCR layer)")
                else:
                    reasons.append("invisible text render mode (Tr 3)")
            if opacity is not None and opacity < 0.1:
                reasons.append(f"opacity {opacity:.2f}")
            if size < 3:
                reasons.append(f"tiny font {size:.1f}pt")
            inter = bbox & prect
            if bbox.get_area() > 0 and (inter.is_empty or inter.get_area() < 0.2 * bbox.get_area()):
                reasons.append("positioned outside the visible page")
            if pix is not None and rmode != 3 and not bbox.is_empty:
                x0, y0 = max(0, int(bbox.x0 * scale)), max(0, int(bbox.y0 * scale))
                x1, y1 = min(pw, int(bbox.x1 * scale) + 1), min(ph, int(bbox.y1 * scale) + 1)
                if x1 > x0 and y1 > y0:
                    cnt = Counter()
                    step = max(1, (x1 - x0) * (y1 - y0) // 400)
                    k = 0
                    for yy in range(y0, y1):
                        row = yy * pw * n
                        for xx in range(x0, x1):
                            k += 1
                            if k % step:
                                continue
                            o = row + xx * n
                            cnt[(samples[o] // 8, samples[o + 1] // 8, samples[o + 2] // 8)] += 1
                    if cnt:
                        (br, bg_, bb), _ = cnt.most_common(1)[0]
                        bgc = ((br * 8 + 4) / 255, (bg_ * 8 + 4) / 255, (bb * 8 + 4) / 255)
                        cr = contrast(rgb, bgc)
                        # if text is visible its own pixels differ from bg; if all pixels == bg the text vanished
                        distinct = len(cnt)
                        if cr < 1.35:
                            reasons.append(f"text colour ≈ background (contrast {cr:.2f}:1)")
                        elif distinct == 1 and len(txt.strip()) > 3:
                            reasons.append("no glyph pixels visible where the text sits")
            # covered by a filled shape drawn later
            seq = sp.get("seqno", 0)
            for d in draws:
                r = d.get("rect")
                if r is None:
                    continue
                if d.get("seqno", -1) > seq and (bbox & r).get_area() > 0.8 * max(bbox.get_area(), 1e-6) \
                        and (d.get("fill_opacity") or 1) > 0.9:
                    reasons.append("covered by a shape drawn on top")
                    break
            if ocr_words is not None and not reasons and not scanned_like:
                ws = words_of(txt)
                if len(ws) >= 4:
                    found = sum(1 for w in ws if w in ocr_words)
                    if found / len(ws) < 0.25:
                        reasons.append(f"not visible in rendered page (OCR found {found}/{len(ws)} words)")
            if reasons:
                page_lines.append(f"[[HIDDEN: {'; '.join(reasons)}]] {txt} [[/HIDDEN]]")
                flagged_pages.add(pno)
                if not (len(reasons) == 1 and reasons[0].startswith("not visible") and False):
                    sev_hits = match_patterns(txt)
                    sev = classify(sev_hits, True) if sev_hits else ("HIGH" if len(words_of(txt)) >= 5 else "MEDIUM")
                    add(sev, display, f"page {pno}, bbox ({bbox.x0:.0f},{bbox.y0:.0f},{bbox.x1:.0f},{bbox.y1:.0f})",
                        "Hidden text in PDF: " + "; ".join(reasons), txt,
                        f"font {sp.get('font')}, size {size:.1f}, colour rgb{tuple(round(c, 2) for c in rgb)}",
                        [f"{nn}: “{clip(h, 80)}”" for nn, h in sev_hits])
            else:
                page_lines.append(txt)
        if invisible_ocr_chars:
            add("INFO", display, f"page {pno}", "Scanned page with invisible OCR text layer (normally benign)",
                f"{invisible_ocr_chars} chars", "Checked for directives anyway")
        # visible text: run language patterns line by line (visible directives still matter)
        try:
            visible = page.get_text("text")
        except Exception:
            visible = ""
        for i, ln in enumerate(visible.split("\n"), 1):
            unicode_scan(display, i, ln, False)
            h = match_patterns(ln)
            if h:
                # skip if already reported as hidden
                if any(f.file == display and ln.strip()[:40] in f.text for f in FINDINGS):
                    continue
                add(classify(h, False), display, f"page {pno}, line {i}",
                    "Injection-style language in visible PDF text", ln.strip(), "",
                    [f"{nn}: “{clip(x, 80)}”" for nn, x in h])
        for kind, dec in decode_payloads(visible):
            h = match_patterns(dec)
            add("CRITICAL" if h else "LOW", display, f"page {pno}", f"Encoded text ({kind}) in PDF", dec)
        dump.extend(page_lines)
        # annotations & links
        try:
            for a in page.annots() or []:
                info = a.info or {}
                content = " ".join(str(info.get(k, "")) for k in ("content", "title", "subject")).strip()
                hidden_flag = bool(a.flags & (1 | 2 | 32))  # invisible / hidden / nview
                if content:
                    dump.append(f"[[ANNOTATION {a.type[1]}{' hidden' if hidden_flag else ''}]] {content}")
                    report_text(display, f"page {pno} annotation ({a.type[1]})", content,
                                "PDF annotation/comment" + (" (flagged hidden)" if hidden_flag else ""),
                                True, base_sev="MEDIUM" if hidden_flag else "LOW")
        except Exception:
            pass
        try:
            for l in page.get_links():
                uri = l.get("uri")
                if uri and (re.search(r"[?&][^=]+=", uri) or uri.lower().startswith(("javascript:", "file:"))):
                    add("LOW", display, f"page {pno}", "Link with parameters / script / file scheme", uri)
        except Exception:
            pass
    write_extracted(display, "\n".join(dump))
    if flagged_pages:
        rd = OUT / "renders"
        rd.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w.-]+", "_", display)[:80]
        for pno in sorted(flagged_pages)[:20]:
            try:
                doc[pno - 1].get_pixmap(dpi=110).save(str(rd / f"{safe}_p{pno}.png"))
            except Exception:
                pass


def scan_pdf_fallback(path, data, display):
    MANUAL.append(f"{display}: PyMuPDF not installed — only plain text/metadata extraction was possible. "
                  f"Install with: pip install pymupdf   (then re-run for colour/size/position/OCR checks)")
    text = ""
    try:
        import pypdf
        r = pypdf.PdfReader(io.BytesIO(data))
        for k, v in (r.metadata or {}).items():
            report_text(display, f"metadata {k}", str(v), "PDF metadata", True)
        text = "\n".join(f"\n===== page {i + 1} =====\n" + (p.extract_text() or "") for i, p in enumerate(r.pages))
    except Exception:
        if shutil.which("pdftotext"):
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / "f.pdf"
                p.write_bytes(data)
                text = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout
    write_extracted(display, text)
    scan_text_content(display, text, ".txt", False)


# --------------------------------------------------------------------------------------
# Office Open XML (docx / pptx / xlsx) and ODF
# --------------------------------------------------------------------------------------

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def hex_rgb(h):
    try:
        h = h.strip().lstrip("#")
        if len(h) == 8:
            h = h[2:]
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except Exception:
        return None


HIGHLIGHT = {"white": "FFFFFF", "black": "000000", "yellow": "FFFF00", "green": "00FF00", "cyan": "00FFFF",
             "magenta": "FF00FF", "blue": "0000FF", "red": "FF0000", "darkBlue": "000080", "darkCyan": "008080",
             "darkGreen": "008000", "darkMagenta": "800080", "darkRed": "800000", "darkYellow": "808000",
             "darkGray": "808080", "lightGray": "C0C0C0"}


def _on(el):
    if el is None:
        return False
    v = el.get(W + "val")
    return v not in ("0", "false", "off")


def docx_rpr_props(rpr):
    p = {}
    if rpr is None:
        return p
    for tag in ("vanish", "specVanish", "webHidden"):
        e = rpr.find(W + tag)
        if e is not None:
            p[tag] = _on(e)
    c = rpr.find(W + "color")
    if c is not None and c.get(W + "val") and c.get(W + "val") != "auto":
        p["color"] = c.get(W + "val")
    sz = rpr.find(W + "sz")
    if sz is not None and sz.get(W + "val", "").isdigit():
        p["sz"] = int(sz.get(W + "val"))
    hl = rpr.find(W + "highlight")
    if hl is not None:
        p["bg"] = HIGHLIGHT.get(hl.get(W + "val"), None)
    shd = rpr.find(W + "shd")
    if shd is not None and shd.get(W + "fill") not in (None, "auto"):
        p["bg"] = shd.get(W + "fill")
    rs = rpr.find(W + "rStyle")
    if rs is not None:
        p["rStyle"] = rs.get(W + "val")
    pos = rpr.find(W + "position")
    if pos is not None:
        try:
            p["position"] = int(pos.get(W + "val"))
        except Exception:
            pass
    return p


def scan_docx(z: zipfile.ZipFile, display: str):
    styles = {}
    default = {}
    if "word/styles.xml" in z.namelist():
        try:
            st = ET.fromstring(z.read("word/styles.xml"))
            dd = st.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")
            default = docx_rpr_props(dd)
            for s in st.findall(W + "style"):
                sid = s.get(W + "styleId")
                pr = docx_rpr_props(s.find(W + "rPr"))
                bo = s.find(W + "basedOn")
                if bo is not None:
                    pr["_based"] = bo.get(W + "val")
                styles[sid] = pr
        except Exception:
            pass

    def resolve(sid, depth=0):
        if not sid or sid not in styles or depth > 8:
            return {}
        b = styles[sid]
        base = resolve(b.get("_based"), depth + 1)
        return {**base, **{k: v for k, v in b.items() if not k.startswith("_")}}

    page_bg = "FFFFFF"
    parts = [n for n in z.namelist() if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes|glossary/document)\.xml$", n)]
    dump = []
    for part in parts:
        try:
            root = ET.fromstring(z.read(part))
        except Exception:
            continue
        bgel = root.find(W + "background")
        if bgel is not None and bgel.get(W + "color"):
            page_bg = bgel.get(W + "color")
        dump.append(f"\n===== {part} =====")
        for pi, para in enumerate(root.iter(W + "p"), 1):
            ppr = para.find(W + "pPr")
            pstyle = None
            if ppr is not None:
                ps = ppr.find(W + "pStyle")
                pstyle = ps.get(W + "val") if ps is not None else None
            pprops = {**default, **resolve(pstyle),
                      **docx_rpr_props(ppr.find(W + "rPr") if ppr is not None else None)}
            segs = []
            hidden_buf = []
            for r in para.iter(W + "r"):
                t = "".join((e.text or "") for e in r if e.tag in (W + "t", W + "delText", W + "instrText"))
                t += "\t" * len(r.findall(W + "tab"))
                if not t:
                    continue
                rp = docx_rpr_props(r.find(W + "rPr"))
                props = {**pprops, **resolve(rp.get("rStyle")), **rp}
                reasons = []
                if props.get("vanish") or props.get("specVanish"):
                    reasons.append("hidden-text attribute (w:vanish)")
                if props.get("webHidden"):
                    reasons.append("webHidden")
                col = hex_rgb(props["color"]) if props.get("color") else None
                bg = hex_rgb(props.get("bg") or page_bg) or (1, 1, 1)
                if col and contrast(col, bg) < 1.35:
                    reasons.append(f"font colour #{props['color']} on background #{props.get('bg') or page_bg}")
                if props.get("sz") is not None and props["sz"] < 6:
                    reasons.append(f"tiny font {props['sz'] / 2}pt")
                if props.get("position") is not None and abs(props["position"]) > 200:
                    reasons.append(f"raised/lowered by {props['position'] / 2}pt (off-line)")
                if r.find(W + "delText") is not None:
                    reasons.append("tracked deletion (invisible in final view)")
                if r.find(W + "instrText") is not None:
                    reasons.append("field code")
                if reasons:
                    hidden_buf.append((t, tuple(reasons)))
                    segs.append(f"[[HIDDEN: {'; '.join(reasons)}]]{t}[[/HIDDEN]]")
                else:
                    segs.append(t)
            line = "".join(segs)
            dump.append(line)
            if hidden_buf:
                # merge consecutive hidden runs by reason
                groups = {}
                for t, rs in hidden_buf:
                    groups.setdefault(rs, []).append(t)
                for rs, ts in groups.items():
                    txt = "".join(ts)
                    if not txt.strip():
                        continue
                    if rs == ("field code",):
                        report_text(display, f"{part} paragraph {pi}", txt, "Word field code", False)
                        continue
                    hits = match_patterns(txt)
                    sev = classify(hits, True) if hits else ("HIGH" if len(words_of(txt)) >= 5 else "MEDIUM")
                    if rs == ("tracked deletion (invisible in final view)",) and not hits:
                        sev = "LOW"
                    add(sev, display, f"{part} paragraph {pi}", "Hidden text in Word document: " + "; ".join(rs),
                        txt, "", [f"{n}: “{clip(h, 80)}”" for n, h in hits])
            plain = re.sub(r"\[\[/?HIDDEN[^\]]*\]\]", "", line)
            hits = match_patterns(plain)
            if hits and not hidden_buf:
                add(classify(hits, False), display, f"{part} paragraph {pi}",
                    "Injection-style language in visible document text", plain, "",
                    [f"{n}: “{clip(h, 80)}”" for n, h in hits])
            unicode_scan(display, pi, plain, False)
    # comments
    for part in [n for n in z.namelist() if re.match(r"word/comments\w*\.xml$", n)]:
        try:
            root = ET.fromstring(z.read(part))
            for c in root.findall(W + "comment"):
                txt = " ".join((t.text or "") for t in c.iter(W + "t"))
                if txt.strip():
                    dump.append(f"[[COMMENT by {c.get(W + 'author')}]] {txt}")
                    report_text(display, f"{part} (author {c.get(W + 'author')})", txt, "Word comment (review pane)",
                                True, base_sev="INFO")
        except Exception:
            pass
    write_extracted(display, "\n".join(dump))
    if any(n.lower().endswith("vbaproject.bin") for n in z.namelist()):
        add("HIGH", display, "vbaProject.bin", "Document contains VBA macros", "", "Do not enable macros")


def scan_pptx(z: zipfile.ZipFile, display: str):
    names = z.namelist()
    sw, shh = 12192000, 6858000
    try:
        pres = ET.fromstring(z.read("ppt/presentation.xml"))
        s = pres.find(P + "sldSz")
        if s is not None:
            sw, shh = int(s.get("cx")), int(s.get("cy"))
    except Exception:
        pass
    dump = []
    slides = sorted([n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)],
                    key=lambda n: int(re.findall(r"\d+", n)[-1]))
    for sl in slides:
        sno = int(re.findall(r"\d+", sl)[-1])
        root = ET.fromstring(z.read(sl))
        hidden_slide = root.get("show") == "0"
        dump.append(f"\n===== slide {sno}{' [HIDDEN SLIDE]' if hidden_slide else ''} =====")
        all_txt = " ".join((t.text or "") for t in root.iter(A + "t"))
        if hidden_slide and all_txt.strip():
            report_text(display, f"slide {sno}", all_txt, "Hidden slide (not shown in slideshow)", True,
                        base_sev="MEDIUM")
        for sp in root.iter(P + "sp"):
            off = sp.find(f".//{A}xfrm/{A}off")
            ext = sp.find(f".//{A}xfrm/{A}ext")
            offslide = False
            if off is not None:
                x, y = int(off.get("x", 0)), int(off.get("y", 0))
                cx = int(ext.get("cx", 0)) if ext is not None else 0
                cy = int(ext.get("cy", 0)) if ext is not None else 0
                if x >= sw or y >= shh or x + cx <= 0 or y + cy <= 0:
                    offslide = True
            for para in sp.iter(A + "p"):
                segs, hid = [], []
                for r in para.iter(A + "r"):
                    t = "".join((e.text or "") for e in r.iter(A + "t"))
                    if not t:
                        continue
                    rpr = r.find(A + "rPr")
                    reasons = []
                    if offslide:
                        reasons.append("shape positioned outside the slide")
                    if rpr is not None:
                        szv = rpr.get("sz")
                        if szv and szv.isdigit() and int(szv) < 300:
                            reasons.append(f"tiny font {int(szv) / 100}pt")
                        sf = rpr.find(f"{A}solidFill/{A}srgbClr")
                        if sf is not None:
                            c = hex_rgb(sf.get("val"))
                            if c and min(c) > 0.93:
                                reasons.append("white text (check against slide background)")
                            alpha = sf.find(A + "alpha")
                            if alpha is not None and int(alpha.get("val", 100000)) < 10000:
                                reasons.append("transparent text")
                        if rpr.find(A + "noFill") is not None:
                            reasons.append("text with no fill")
                    if reasons:
                        hid.append((t, reasons))
                        segs.append(f"[[HIDDEN: {'; '.join(reasons)}]]{t}[[/HIDDEN]]")
                    else:
                        segs.append(t)
                line = "".join(segs)
                if line.strip():
                    dump.append(line)
                for t, rs in hid:
                    hits = match_patterns(t)
                    sev = classify(hits, True) if hits else ("MEDIUM" if len(words_of(t)) >= 4 else "LOW")
                    add(sev, display, f"slide {sno}", "Hidden text in slide: " + "; ".join(rs), t, "",
                        [f"{n}: “{clip(h, 80)}”" for n, h in hits])
                plain = re.sub(r"\[\[/?HIDDEN[^\]]*\]\]", "", line)
                if not hid:
                    h = match_patterns(plain)
                    if h:
                        add(classify(h, False), display, f"slide {sno}", "Injection-style language in slide text",
                            plain, "", [f"{n}: “{clip(x, 80)}”" for n, x in h])
        for pic in root.iter():
            if pic.tag.endswith("}cNvPr") and (pic.get("descr") or pic.get("title")):
                report_text(display, f"slide {sno} alt-text", f"{pic.get('title') or ''} {pic.get('descr') or ''}",
                            "Alt-text / shape description (not visible)", True)
    for n in sorted(x for x in names if re.match(r"ppt/notesSlides/notesSlide\d+\.xml$", x)):
        root = ET.fromstring(z.read(n))
        txt = "\n".join((t.text or "") for t in root.iter(A + "t")).strip()
        if txt and not re.fullmatch(r"\d+", txt):
            dump.append(f"\n===== speaker notes ({n}) =====\n{txt}")
            report_text(display, n, txt, "Speaker notes (not shown on slides)", True, base_sev="INFO")
    for n in [x for x in names if re.match(r"ppt/comments/.*\.xml$", x)]:
        txt = " ".join(t for t in re.findall(r">([^<]{3,})<", z.read(n).decode("utf-8", "ignore")))
        report_text(display, n, txt, "PowerPoint comment", True, base_sev="INFO")
    write_extracted(display, "\n".join(dump))


def scan_xlsx(z: zipfile.ZipFile, display: str):
    names = z.namelist()
    shared = []
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(S + "si"):
            shared.append("".join((t.text or "") for t in si.iter(S + "t")))
    white_xf, tiny_xf = set(), set()
    if "xl/styles.xml" in names:
        st = ET.fromstring(z.read("xl/styles.xml"))
        fonts = st.find(S + "fonts")
        font_flags = []
        for f in (fonts.findall(S + "font") if fonts is not None else []):
            c = f.find(S + "color")
            sz = f.find(S + "sz")
            white = c is not None and c.get("rgb") and (hex_rgb(c.get("rgb")) or (0, 0, 0)) > (0.93, 0.93, 0.93)
            tiny = sz is not None and float(sz.get("val", 11)) < 3
            font_flags.append((white, tiny))
        xfs = st.find(S + "cellXfs")
        for i, xf in enumerate(xfs.findall(S + "xf") if xfs is not None else []):
            fid = int(xf.get("fontId", 0))
            if fid < len(font_flags):
                if font_flags[fid][0]:
                    white_xf.add(i)
                if font_flags[fid][1]:
                    tiny_xf.add(i)
    sheet_names = {}
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rmap = {r.get("Id"): r.get("Target") for r in rels}
        for s in wb.iter(S + "sheet"):
            rid = s.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            tgt = rmap.get(rid, "")
            tgt = "xl/" + tgt.lstrip("/").replace("xl/", "") if tgt else ""
            sheet_names[tgt] = (s.get("name"), s.get("state", "visible"))
        for dn in wb.iter(S + "definedName"):
            report_text(display, f"defined name {dn.get('name')}", dn.text or "", "Workbook defined name", True)
    except Exception:
        pass
    dump = []
    for part in sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n)):
        nm, state = sheet_names.get(part, (part, "visible"))
        root = ET.fromstring(z.read(part))
        dump.append(f"\n===== sheet '{nm}' [{state}] =====")
        hidden_cols = set()
        for col in root.iter(S + "col"):
            if col.get("hidden") in ("1", "true"):
                for k in range(int(col.get("min")), int(col.get("max")) + 1):
                    hidden_cols.add(k)
        sheet_text = []
        for row in root.iter(S + "row"):
            row_hidden = row.get("hidden") in ("1", "true")
            for c in row.findall(S + "c"):
                v = c.find(S + "v")
                isel = c.find(S + "is")
                if c.get("t") == "s" and v is not None:
                    try:
                        val = shared[int(v.text)]
                    except Exception:
                        val = v.text or ""
                elif isel is not None:
                    val = "".join((t.text or "") for t in isel.iter(S + "t"))
                else:
                    val = v.text if v is not None else ""
                f = c.find(S + "f")
                if f is not None and f.text:
                    val = f"={f.text}  →  {val}"
                if not val:
                    continue
                ref = c.get("r", "?")
                colnum = 0
                for ch in re.match(r"[A-Z]+", ref).group(0) if re.match(r"[A-Z]+", ref) else "":
                    colnum = colnum * 26 + ord(ch) - 64
                reasons = []
                if state != "visible":
                    reasons.append(f"{state} sheet")
                if row_hidden:
                    reasons.append("hidden row")
                if colnum in hidden_cols:
                    reasons.append("hidden column")
                s_idx = int(c.get("s", 0))
                if s_idx in white_xf:
                    reasons.append("white font")
                if s_idx in tiny_xf:
                    reasons.append("tiny font")
                sheet_text.append(val)
                if reasons:
                    dump.append(f"{ref}: [[HIDDEN: {'; '.join(reasons)}]]{val}[[/HIDDEN]]")
                    hits = match_patterns(val)
                    sev = classify(hits, True) if hits else ("MEDIUM" if len(words_of(val)) >= 5 else "LOW")
                    add(sev, display, f"sheet '{nm}' {ref}", "Hidden spreadsheet cell: " + "; ".join(reasons),
                        val, "", [f"{n}: “{clip(h, 80)}”" for n, h in hits])
                else:
                    dump.append(f"{ref}: {val}")
                    h = match_patterns(val)
                    if h:
                        add(classify(h, False), display, f"sheet '{nm}' {ref}",
                            "Injection-style language in cell", val, "", [f"{n}: “{clip(x, 80)}”" for n, x in h])
    for n in [x for x in names if re.match(r"xl/(comments\d*|threadedComments/.*)\.xml$", x)]:
        txt = " ".join(re.findall(r">([^<]{3,})<", z.read(n).decode("utf-8", "ignore")))
        dump.append(f"\n===== {n} =====\n{txt}")
        report_text(display, n, txt, "Cell comments/notes", True, base_sev="INFO")
    write_extracted(display, "\n".join(dump))
    if any(n.lower().endswith("vbaproject.bin") for n in names):
        add("HIGH", display, "vbaProject.bin", "Workbook contains VBA macros", "", "Do not enable macros")


def scan_zip_office(path: Path, data: bytes, display: str):
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except Exception as e:
        MANUAL.append(f"{display}: could not open as zip-based document ({e})")
        return
    names = z.namelist()
    ext = ext_of(path)
    if "word/document.xml" in names:
        scan_docx(z, display)
    elif "ppt/presentation.xml" in names:
        scan_pptx(z, display)
    elif "xl/workbook.xml" in names:
        scan_xlsx(z, display)
    meta_lines: list[str] = []
    # Generic sweep of every XML part: metadata, alt text, custom XML, charts, anything the
    # specific parsers above don't model. Ensures nothing in the container goes unread.
    for n in names:
        if n.endswith("/"):
            continue
        low = n.lower()
        raw = z.read(n)
        if low.endswith((".xml", ".rels", ".xhtml", ".html", ".opf", ".ncx", ".txt", ".json")):
            s = raw.decode("utf-8", "ignore")
            for m in re.finditer(r'(?:descr|title|name|alt)="([^"]{12,})"', s):
                report_text(display, f"{n} attribute", m.group(1), "Alt-text / object description / attribute",
                            True)
            txt = " ".join(re.findall(r">([^<>]+)<", s))
            is_meta = low.startswith(("docprops/", "customxml/", "meta")) or "custom" in low
            if is_meta and txt.strip():
                try:
                    for el in ET.fromstring(raw).iter():
                        val = (el.text or "").strip()
                        if len(val) >= 3 and not re.fullmatch(r"[\d\s:TZ.+-]+", val):
                            tag = el.tag.split("}")[-1]
                            meta_lines.append(f"{n} <{tag}>: {val}")
                            report_text(display, f"{n} <{tag}>", val,
                                        "Document properties / custom XML (not shown in the document)", True)
                except Exception:
                    report_text(display, n, txt, "Document properties / custom XML (not shown in the document)", True)
            elif ext in ODF_EXT and low in ("content.xml",) or low.endswith((".xhtml", ".html")):
                scan_text_content(f"{display} › {n}", s, ".html", False)
                # ODF hidden text
                for m in re.finditer(r'text:display="none"[^>]*>(.*?)</', s, re.DOTALL):
                    report_text(display, n, re.sub(r"<[^>]+>", "", m.group(1)), "ODF hidden text", True,
                                base_sev="MEDIUM")
            else:
                for line_txt in re.findall(r">([^<>]{20,})<", s):
                    h = match_patterns(line_txt)
                    if h and not any(line_txt.strip()[:50] in f.text for f in FINDINGS):
                        add(classify(h, True), display, n, "Injection-style text inside document XML part",
                            line_txt, "", [f"{nn}: “{clip(x, 80)}”" for nn, x in h])
        elif not low.endswith((".png", ".jpg", ".jpeg", ".gif", ".emf", ".wmf", ".bmp", ".tiff", ".svg",
                               ".ttf", ".odttf", ".fntdata", "vbaproject.bin", ".bin", ".sigs", ".jfif")):
            scan_bytes(Path(n), raw, f"{display} › {n}")
        elif low.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".jfif")) and len(raw) > 2000:
            scan_image(Path(n), raw, f"{display} › {n}")
        elif low.endswith(".bin") and "embeddings" in low:
            add("MEDIUM", display, n, "Embedded OLE object", f"{len(raw)} bytes", "Open manually if relevant")
    if meta_lines:
        safe = re.sub(r"[^\w.\-]+", "_", display)[:150]
        f = OUT / "extracted" / f"{safe}.txt"
        prev = f.read_text(encoding="utf-8") if f.exists() else ""
        write_extracted(display, "===== DOCUMENT PROPERTIES / METADATA =====\n" + "\n".join(meta_lines) + "\n\n" + prev)


# --------------------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------------------

def scan_image(path: Path, data: bytes, display: str):
    meta_txt = []
    if Image is not None:
        try:
            im = Image.open(io.BytesIO(data))
            for k, v in (im.info or {}).items():
                if isinstance(v, (str, bytes)) and k not in ("icc_profile", "exif", "dpi"):
                    vv = v.decode("utf-8", "ignore") if isinstance(v, bytes) else v
                    if len(vv.strip()) > 3:
                        meta_txt.append(f"{k}: {vv}")
            try:
                ex = im.getexif()
                for tag, v in ex.items():
                    if isinstance(v, (str, bytes)):
                        vv = v.decode("utf-8", "ignore") if isinstance(v, bytes) else v
                        if len(vv.strip()) > 3:
                            meta_txt.append(f"EXIF {tag}: {vv}")
            except Exception:
                pass
        except Exception:
            im = None
    else:
        im = None
    for m in meta_txt:
        report_text(display, "image metadata", m, "Text inside image metadata (EXIF/PNG chunk)", True)
    xmp = re.search(rb"<x:xmpmeta.*?</x:xmpmeta>", data, re.DOTALL)
    if xmp:
        t = " ".join(re.findall(r">([^<>]{4,})<", xmp.group(0).decode("utf-8", "ignore")))
        if t.strip():
            report_text(display, "XMP", t, "Image XMP metadata", True)
    tail = data.rfind(b"\xff\xd9") if data[:2] == b"\xff\xd8" else data.rfind(b"IEND")
    if tail > 0 and len(data) - tail > 64:
        extra = data[tail + 8:]
        s = extra.decode("utf-8", "ignore")
        add("MEDIUM", display, "after end-of-image marker", "Data appended after the image ends",
            s[:300] if printable_ratio(s) > 0.8 else f"{len(extra)} bytes of binary")
    if have_tesseract() and not OPTS.no_ocr and im is not None:
        try:
            buf = io.BytesIO()
            im.convert("RGB").save(buf, "PNG")
            normal = ocr_png(buf.getvalue())
            g = ImageOps.equalize(ImageOps.autocontrast(im.convert("L"), cutoff=1))
            buf2 = io.BytesIO()
            g.save(buf2, "PNG")
            enhanced = ocr_png(buf2.getvalue())
            if normal.strip():
                write_extracted(display, "OCR (as displayed):\n" + normal + "\n\nOCR (contrast-enhanced):\n" + enhanced)
            report_text(display, "OCR text", normal, "Text visible in image (OCR)", False)
            nw = set(words_of(normal))
            new = [w for w in words_of(enhanced) if w not in nw]
            if len(new) >= 4:
                report_text(display, "OCR after contrast boost", enhanced,
                            "Low-contrast text in image (only readable after contrast enhancement)", True,
                            base_sev="HIGH", detail=f"new words: {' '.join(new[:30])}")
        except Exception:
            pass
    else:
        MANUAL.append(f"{display}: image not OCR'd — look at it (Read the image) for embedded/low-contrast text")


# --------------------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------------------

def write_extracted(display: str, text: str):
    d = OUT / "extracted"
    d.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]+", "_", display)[:150]
    (d / f"{safe}.txt").write_text(text, encoding="utf-8")
    for inv in INVENTORY[::-1]:
        if inv["file"] == display:
            inv["extracted"] = f"extracted/{safe}.txt"
            break


# --------------------------------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------------------------------

def scan_bytes(path: Path, data: bytes, display: str, depth: int = 0):
    ext = ext_of(path)
    INVENTORY.append({"file": display, "bytes": len(data), "type": ext or "(none)", "method": ""})
    inv = INVENTORY[-1]
    try:
        if data[:5] == b"%PDF-" or ext == ".pdf":
            inv["method"] = "pdf"
            scan_pdf(path, data, display)
        elif ext in OOXML_EXT or ext in ODF_EXT:
            inv["method"] = "office-xml"
            scan_zip_office(path, data, display)
        elif ext in IMAGE_EXT:
            inv["method"] = "image"
            scan_image(path, data, display)
        elif ext in ARCHIVE_EXT or data[:4] == b"PK\x03\x04":
            inv["method"] = "archive"
            scan_archive(path, data, display, depth)
        elif ext in LEGACY_OFFICE - {".rtf"}:
            inv["method"] = "legacy-office"
            convert_legacy(path, data, display)
        elif not is_binary(data):
            inv["method"] = "text"
            scan_plain(path, data, display)
        else:
            inv["method"] = "binary (strings only)"
            strs = re.findall(rb"[\x20-\x7e]{24,}", data)
            txt = "\n".join(s.decode() for s in strs[:5000])
            for s in strs:
                h = [x for x in match_patterns(s.decode()) if x[0] in STRONG]
                if h:
                    add(classify(h, True), display, "binary strings", "Instruction-like text inside a binary file",
                        s.decode(), "", [f"{n}: “{x}”" for n, x in h])
            if ext in {".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".pyc", ".o", ".a"}:
                MANUAL.append(f"{display}: compiled binary — not executed; only printable strings were checked")
    except Exception as e:
        MANUAL.append(f"{display}: scanner error {type(e).__name__}: {e}")


def convert_legacy(path, data, display):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        MANUAL.append(f"{display}: legacy Office format and LibreOffice not available — convert to .docx/.pptx/.xlsx "
                      f"and re-scan, or open it yourself")
        return
    target = {".doc": "docx", ".ppt": "pptx", ".xls": "xlsx"}[path.suffix.lower()]
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / ("in" + path.suffix.lower())
        src.write_bytes(data)
        subprocess.run([soffice, "--headless", "--convert-to", target, "--outdir", td, str(src)],
                       capture_output=True, timeout=180)
        out = Path(td) / f"in.{target}"
        if out.exists():
            scan_zip_office(Path("x." + target), out.read_bytes(), display)
        else:
            MANUAL.append(f"{display}: LibreOffice conversion failed — open manually")


def scan_archive(path, data, display, depth):
    if depth >= 4:
        MANUAL.append(f"{display}: nested archive depth limit reached")
        return
    try:
        if data[:4] == b"PK\x03\x04":
            z = zipfile.ZipFile(io.BytesIO(data))
            if z.comment:
                report_text(display, "zip comment", z.comment.decode("utf-8", "ignore"), "ZIP archive comment", True)
            for info in z.infolist():
                if info.is_dir() or info.file_size > 200 * 1024 * 1024:
                    continue
                if info.comment:
                    report_text(display, f"{info.filename} comment", info.comment.decode("utf-8", "ignore"),
                                "ZIP entry comment", True)
                inner = Path(info.filename)
                if any(p in VENDOR_DIRS for p in inner.parts) and not OPTS.include_vendor:
                    continue
                scan_bytes(inner, z.read(info), f"{display} › {info.filename}", depth + 1)
        else:
            try:
                t = tarfile.open(fileobj=io.BytesIO(data))
            except tarfile.ReadError:
                import gzip
                import bz2
                import lzma
                for opener in (gzip.decompress, bz2.decompress, lzma.decompress):
                    try:
                        inner = opener(data)
                        return scan_bytes(Path(path.stem), inner, f"{display} › {path.stem}", depth + 1)
                    except Exception:
                        continue
                MANUAL.append(f"{display}: unsupported archive format (7z/rar?) — extract and re-scan")
                return
            for m in t.getmembers():
                if not m.isfile() or m.size > 200 * 1024 * 1024:
                    continue
                inner = Path(m.name)
                if any(p in VENDOR_DIRS for p in inner.parts) and not OPTS.include_vendor:
                    continue
                f = t.extractfile(m)
                if f:
                    scan_bytes(inner, f.read(), f"{display} › {m.name}", depth + 1)
    except Exception as e:
        MANUAL.append(f"{display}: could not read archive ({e})")


def walk(root: Path):
    if root.is_file():
        yield root
        return
    for dp, dns, fns in os.walk(root):
        dpp = Path(dp)
        keep = []
        for d in dns:
            if d == ".git":
                GIT_REPOS.append(dpp)  # nested repos (starter code inside a course folder) get scan_git too
            if d in VENDOR_DIRS and not OPTS.include_vendor:
                if d == ".git":
                    hooks = dpp / d / "hooks"
                    if hooks.is_dir():
                        for h in hooks.iterdir():
                            if h.is_file() and not h.name.endswith(".sample"):
                                yield h
                    for cfg in ("config", "info/attributes"):
                        if (dpp / d / cfg).is_file():
                            yield dpp / d / cfg
                SKIPPED.append(str((dpp / d)))
                continue
            keep.append(d)
        dns[:] = keep
        for f in fns:
            yield dpp / f


SKIPPED: list[str] = []
GIT_REPOS: list[Path] = []


def scan_git(root: Path):
    """Commit messages, tags, notes and other branches are invisible in the working tree but
    agents often read them. Read-only git plumbing; no hooks run, fsmonitor/pager disabled."""
    if not (root / ".git").exists() or not shutil.which("git"):
        return
    base = ["git", "-c", "core.fsmonitor=", "-c", "core.pager=cat", "-c", f"safe.directory={root}",
            "--no-pager", "-C", str(root)]
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"}
    try:
        log = subprocess.run(base + ["log", "--all", "--format=%h%x00%an%x00%B%x1e"], capture_output=True,
                             text=True, timeout=60, env=env).stdout
        notes = subprocess.run(base + ["notes", "list"], capture_output=True, text=True, timeout=30, env=env).stdout
        branches = subprocess.run(base + ["for-each-ref", "--format=%(refname)"], capture_output=True,
                                  text=True, timeout=30, env=env).stdout
    except Exception as e:
        MANUAL.append(f"{root.name}/.git: could not read git history ({e})")
        return
    INVENTORY.append({"file": f"{root.name}/.git (history)", "bytes": len(log), "type": "git",
                      "method": "git log --all"})
    dump = []
    for rec in log.split("\x1e"):
        parts = rec.strip("\n").split("\x00")
        if len(parts) < 3:
            continue
        h, author, body = parts[0], parts[1], parts[2]
        dump.append(f"--- commit {h} ({author}) ---\n{body}")
        scan_text_content(f"{root.name}/.git commit {h}", body, ".txt", True)
    if notes.strip():
        add("MEDIUM", f"{root.name}/.git", "git notes", "Repository has git notes (hidden from normal log view)",
            notes[:300])
    refs = [r for r in branches.split() if not r.startswith(("refs/heads/main", "refs/heads/master",
                                                              "refs/remotes/origin/HEAD"))]
    if refs:
        dump.append("--- refs ---\n" + "\n".join(refs))
        if len(refs) <= 40:
            add("INFO", f"{root.name}/.git", "refs", "Other branches/tags/stashes exist (not in working tree)",
                "\n".join(refs), "Content on other branches was not file-scanned; check if relevant")
    write_extracted(f"{root.name}/.git (history)", "\n".join(dump))


def render_report(targets):
    FINDINGS.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.file, f.location))
    # de-duplicate identical (file, location, text)
    seen, uniq = set(), []
    norm = lambda t: re.sub(r"<!--|-->|\s+", " ", t).strip()[:200]
    for f in FINDINGS:
        k = (f.file, f.location, f.text[:120], f.technique[:40])
        if k in seen:
            continue
        # same spot already reported at higher/equal severity with overlapping text → drop
        nf = norm(f.text)
        dup = next((u for u in uniq if u.file == f.file and u.location == f.location and nf and
                    (norm(u.text) in nf or nf in norm(u.text))), None)
        if dup is not None:
            if f.technique not in dup.technique and f.technique not in dup.detail:
                dup.detail = (dup.detail + "; " if dup.detail else "") + "also: " + f.technique
            continue
        seen.add(k)
        uniq.append(f)
    counts = Counter(f.severity for f in uniq)
    L = []
    L.append("# Prompt-injection scan report\n")
    L.append(f"Scanned: {', '.join(map(str, targets))}  ")
    L.append(f"Files examined: {len(INVENTORY)}  ")
    L.append("Findings: " + ", ".join(f"{s} {counts.get(s, 0)}" for s in SEVERITY_ORDER) + "\n")
    L.append("> Automated pass only. Every file must still be read by the reviewer; see SKILL.md.\n")
    for sev in SEVERITY_ORDER:
        group = [f for f in uniq if f.severity == sev]
        if not group:
            continue
        L.append(f"\n## {sev} ({len(group)})\n")
        for i, f in enumerate(group, 1):
            L.append(f"### {sev[0]}{i}. {f.technique}")
            L.append(f"- **File:** `{f.file}`")
            L.append(f"- **Where:** {f.location}")
            if f.patterns:
                L.append(f"- **Matched:** " + "; ".join(f.patterns))
            if f.detail:
                L.append(f"- **Detail:** {f.detail}")
            L.append("- **Content:**\n")
            L.append("```text\n" + f.text.replace("```", "ʼʼʼ") + "\n```\n")
    L.append("\n## Needs manual inspection\n")
    L.extend(f"- {m}" for m in sorted(set(MANUAL))) if MANUAL else L.append("- (nothing)")
    L.append("\n## Skipped directories\n")
    L.extend(f"- {s}" for s in SKIPPED) if SKIPPED else L.append("- (none)")
    L.append("\n## File inventory\n")
    L.append("| # | File | Bytes | Method | Extracted text |")
    L.append("|---|------|-------|--------|----------------|")
    for i, inv in enumerate(INVENTORY, 1):
        L.append(f"| {i} | `{inv['file']}` | {inv['bytes']} | {inv['method']} | {inv.get('extracted', '')} |")
    (OUT / "report.md").write_text("\n".join(L), encoding="utf-8")
    (OUT / "findings.json").write_text(json.dumps({
        "counts": counts, "findings": [asdict(f) for f in uniq], "inventory": INVENTORY,
        "manual": sorted(set(MANUAL)), "skipped": SKIPPED}, ensure_ascii=False, indent=1), encoding="utf-8")
    return uniq, counts


def main():
    global OUT, OPTS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", default="injection-scan")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--include-vendor", action="store_true", help="also scan node_modules/.venv/build dirs")
    ap.add_argument("--max-pages", type=int, default=150)
    OPTS = ap.parse_args()
    OUT = Path(OPTS.out).resolve()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    targets = [Path(p).resolve() for p in OPTS.paths]
    ROOTS.extend(targets)
    for t in targets:
        if not t.exists():
            print(f"!! not found: {t}", file=sys.stderr)
            continue
        base = t.parent if t.is_file() else t
        for f in walk(t):
            if f.resolve().is_relative_to(OUT):
                continue
            try:
                data = f.read_bytes()
            except Exception as e:
                MANUAL.append(f"{f}: unreadable ({e})")
                continue
            disp = str(f.relative_to(base)) if f.is_relative_to(base) else str(f)
            if t.is_dir():
                disp = f"{t.name}/{disp}"
            scan_bytes(f, data, disp)
    for repo in dict.fromkeys(GIT_REPOS):
        scan_git(repo)
    uniq, counts = render_report(targets)
    print(f"Scanned {len(INVENTORY)} files. Findings: " +
          ", ".join(f"{s}={counts.get(s, 0)}" for s in SEVERITY_ORDER))
    for f in uniq[:25]:
        if f.severity in ("CRITICAL", "HIGH"):
            print(f"  [{f.severity}] {f.file} @ {f.location}: {f.technique} :: {clip(f.text, 140)}")
    print(f"Report: {OUT / 'report.md'}")
    print(f"Extracted full text (incl. hidden layers): {OUT / 'extracted'}")
    if MANUAL:
        print(f"Manual checks needed: {len(set(MANUAL))} (see report)")


if __name__ == "__main__":
    main()
