#!/usr/bin/env python3
"""Turn a lecture recording, or a subtitle file the student already has, into `transcript.json`.

Output shape: [{"start": float, "end": float, "text": str}, ...]  (seconds, in order)

Audio/video (.mp3 .m4a .wav .mp4 .mkv .webm .ogg .flac ...) is transcribed **locally** with
`faster-whisper` when it is installed. Nothing is uploaded anywhere: the model runs on this machine. When
`faster-whisper` is missing the script exits 2 and prints the install line and the manual alternative:
export the transcript from Zoom, YouTube, Panopto or Teams as `.vtt` / `.srt` and run this script on that
file instead — subtitle files need no model and are converted with the standard library.

Usage:
    transcribe.py lecture.mp4 [--language he] [--model small] [--out transcript.json] [--json]
    transcribe.py lecture.vtt|lecture.srt [--out transcript.json] [--json]

Exit codes: 0 = written · 2 = usage, unreadable input, or faster-whisper not installed for an audio file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SUBTITLE_SUFFIXES = {".vtt", ".srt"}
AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".mp4", ".mkv", ".webm", ".ogg", ".oga", ".flac", ".aac", ".mov", ".wma", ".opus"}

INSTALL_LINE = "pip install faster-whisper"
MANUAL_ALTERNATIVE = (
    "Or skip the model: export the transcript from where the recording lives — Zoom (Recordings → "
    "Audio transcript), YouTube (… → Show transcript, or download the .srt), Panopto / Teams (Download "
    "captions) — save it as .vtt or .srt and run this script on that file; subtitle files need nothing installed."
)


class MissingDependency(RuntimeError):
    """faster-whisper is not importable; the message carries the install line and the manual alternative."""


_TIME = re.compile(r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
_CUE_LINE = re.compile(r"^\s*((?:\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*((?:\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{1,3})")
_TAG = re.compile(r"<[^>]+>")


def _parse_time(s: str) -> float:
    m = _TIME.fullmatch(s.strip())
    if not m:
        raise ValueError(f"bad timestamp {s!r}")
    h, mi, se, frac = m.groups()
    ms = int(frac.ljust(3, "0"))
    return float(int(h or 0) * 3600 + int(mi) * 60 + int(se)) + ms / 1000.0


def _clean(text: str) -> str:
    text = _TAG.sub("", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def convert_subtitles(path: Path) -> list[dict]:
    """Parse a WebVTT or SubRip file into transcript segments. Comments, headers and cue settings are dropped."""
    path = Path(path)
    if path.suffix.lower() not in SUBTITLE_SUFFIXES:
        raise ValueError(f"{path.name}: not a subtitle file (.vtt or .srt)")
    raw = path.read_bytes().decode("utf-8-sig", errors="replace")
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    segments: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _CUE_LINE.match(line)
        if not m:
            i += 1
            continue
        start, end = _parse_time(m.group(1)), _parse_time(m.group(2))
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1
        text = _clean(" ".join(text_lines))
        if text:
            segments.append({"start": start, "end": end, "text": text})
    return segments


def transcribe(path: Path, language: str = "he", model: str = "small") -> list[dict]:
    """Transcribe locally with faster-whisper. Raises MissingDependency when it is not installed."""
    path = Path(path)
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:  # ImportError, or a broken install raising something else
        raise MissingDependency(
            f"faster-whisper is not installed ({exc}). Install it with `{INSTALL_LINE}` "
            f"(CPU is fine; the '{model}' model is ~500 MB and runs locally, nothing is uploaded). {MANUAL_ALTERNATIVE}"
        ) from exc
    whisper = WhisperModel(model, device="auto", compute_type="default")
    segments_iter, _info = whisper.transcribe(str(path), language=language, vad_filter=True)
    out: list[dict] = []
    for seg in segments_iter:
        text = _clean(str(seg.text))
        if text:
            out.append({"start": float(seg.start), "end": float(seg.end), "text": text})
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="audio/video file, or a .vtt/.srt subtitle file")
    parser.add_argument("--language", default="he", help="ISO code of the spoken language (default he)")
    parser.add_argument("--model", default="small", help="faster-whisper model size: tiny|base|small|medium|large-v3")
    parser.add_argument("--out", default="transcript.json")
    parser.add_argument("--json", action="store_true", help="print a one-line JSON summary")
    args = parser.parse_args(argv)
    src = Path(args.source)
    if not src.exists():
        print(f"no such file: {src}", file=sys.stderr)
        return 2
    suffix = src.suffix.lower()
    try:
        if suffix in SUBTITLE_SUFFIXES:
            segments = convert_subtitles(src)
            how = "subtitles"
        elif suffix in AUDIO_SUFFIXES or suffix == "":
            segments = transcribe(src, language=args.language, model=args.model)
            how = f"faster-whisper {args.model}"
        else:
            print(f"unsupported input {suffix!r}: give an audio/video file or a .vtt/.srt transcript", file=sys.stderr)
            return 2
    except MissingDependency as exc:
        print(f"skipped: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(segments, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    duration = segments[-1]["end"] if segments else 0.0
    summary = {"out": args.out, "segments": len(segments), "duration_seconds": duration, "source": how}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"wrote {args.out}: {len(segments)} segment(s), {duration / 60:.1f} minutes, from {how}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
