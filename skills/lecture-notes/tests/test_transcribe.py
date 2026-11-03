"""transcribe.py: local faster-whisper when installed, else subtitle import (.vtt/.srt) and a clear exit 2."""
import builtins
import json
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "transcribe.py"

VTT = """WEBVTT
Kind: captions
Language: he

00:00:01.000 --> 00:00:04.500
שלום לכולם, היום נדבר על תזמון תהליכים.

00:00:04.500 --> 00:00:09.250 align:start position:0%
<v Lecturer>המתזמן (scheduler) בוחר איזה process רץ.</v>

NOTE this is a comment block and must be skipped

00:01:02.000 --> 00:01:05.000
שאלות?
"""

SRT = """1
00:00:01,000 --> 00:00:04,500
Hello everyone, today we talk about
process scheduling.

2
00:00:04,500 --> 00:00:09,250
<i>The scheduler</i> picks which process runs.

3
01:02:03,000 --> 01:02:05,500
Questions?
"""


def test_vtt_conversion(tmp_path, transcribe):
    p = tmp_path / "lecture.vtt"
    p.write_text(VTT, encoding="utf-8")
    segs = transcribe.convert_subtitles(p)
    assert segs == [
        {"start": 1.0, "end": 4.5, "text": "שלום לכולם, היום נדבר על תזמון תהליכים."},
        {"start": 4.5, "end": 9.25, "text": "המתזמן (scheduler) בוחר איזה process רץ."},
        {"start": 62.0, "end": 65.0, "text": "שאלות?"},
    ]


def test_srt_conversion_joins_multiline_cues_and_strips_tags(tmp_path, transcribe):
    p = tmp_path / "lecture.srt"
    p.write_text(SRT, encoding="utf-8")
    segs = transcribe.convert_subtitles(p)
    assert segs[0] == {"start": 1.0, "end": 4.5, "text": "Hello everyone, today we talk about process scheduling."}
    assert segs[1]["text"] == "The scheduler picks which process runs."
    assert segs[2] == {"start": 3723.0, "end": 3725.5, "text": "Questions?"}


def test_segments_have_exactly_the_interchange_keys(tmp_path, transcribe):
    p = tmp_path / "x.vtt"
    p.write_text(VTT, encoding="utf-8")
    for s in transcribe.convert_subtitles(p):
        assert set(s) == {"start", "end", "text"}
        assert isinstance(s["start"], float) and isinstance(s["end"], float) and s["end"] >= s["start"]


def test_utf8_bom_and_crlf_subtitles(tmp_path, transcribe):
    p = tmp_path / "bom.srt"
    p.write_bytes(b"\xef\xbb\xbf" + SRT.replace("\n", "\r\n").encode("utf-8"))
    segs = transcribe.convert_subtitles(p)
    assert len(segs) == 3 and segs[0]["start"] == 1.0


def test_unknown_subtitle_extension_raises(tmp_path, transcribe):
    p = tmp_path / "notes.txt"
    p.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        transcribe.convert_subtitles(p)


def test_transcribe_without_faster_whisper_raises_missing_dependency(tmp_path, transcribe, monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "faster_whisper" or name.startswith("faster_whisper."):
            raise ImportError("No module named 'faster_whisper'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"\x00" * 16)
    with pytest.raises(transcribe.MissingDependency) as info:
        transcribe.transcribe(audio, language="he", model="small")
    msg = str(info.value)
    assert "pip install faster-whisper" in msg
    assert ".vtt" in msg and ".srt" in msg


def test_transcribe_uses_local_model_when_available(tmp_path, transcribe, monkeypatch):
    import types

    calls = {}

    class FakeSegment:
        def __init__(self, s, e, t):
            self.start, self.end, self.text = s, e, t

    class FakeModel:
        def __init__(self, model_size, **kwargs):
            calls["model"] = model_size
            calls["kwargs"] = kwargs

        def transcribe(self, path, language=None, **kwargs):
            calls["path"] = path
            calls["language"] = language
            return iter([FakeSegment(0.0, 2.5, " שלום "), FakeSegment(2.5, 4.0, "עולם")]), types.SimpleNamespace(language=language)

    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = FakeModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake)
    audio = tmp_path / "lecture.m4a"
    audio.write_bytes(b"\x00" * 16)
    segs = transcribe.transcribe(audio, language="he", model="small")
    assert segs == [{"start": 0.0, "end": 2.5, "text": "שלום"}, {"start": 2.5, "end": 4.0, "text": "עולם"}]
    assert calls["model"] == "small" and calls["language"] == "he" and calls["path"] == str(audio)


def run(*args, cwd):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, cwd=cwd)


def test_cli_subtitle_file_writes_transcript_json(tmp_path):
    p = tmp_path / "lecture.vtt"
    p.write_text(VTT, encoding="utf-8")
    out = tmp_path / "transcript.json"
    r = run(str(p), "--out", str(out), "--json", cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 3 and data[0]["text"].startswith("שלום")
    assert json.loads(r.stdout)["segments"] == 3


def test_cli_audio_without_backend_exits_2_with_instructions(tmp_path):
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"\x00" * 16)
    env_block = tmp_path / "block"
    env_block.mkdir()
    # a stub package that fails to import stands in for "not installed", whatever the host has
    (env_block / "faster_whisper.py").write_text("raise ImportError('not installed')\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(audio), "--out", str(tmp_path / "t.json")],
                       capture_output=True, text=True, cwd=tmp_path,
                       env={"PYTHONPATH": str(env_block), "PATH": "/usr/bin:/bin"})
    assert r.returncode == 2
    assert "pip install faster-whisper" in r.stderr
    assert "Zoom" in r.stderr or "YouTube" in r.stderr
