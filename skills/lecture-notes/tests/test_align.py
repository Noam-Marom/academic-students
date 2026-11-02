"""align.py: map transcript segments to slides by weighted token overlap, preferring a monotonic path."""
import json
import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "align.py"


def slide(n, title, text, notes="", hidden=False):
    return {"n": n, "title": title, "text": text, "notes": notes, "hidden": hidden}


def seg(start, text):
    return {"start": float(start), "end": float(start) + 5.0, "text": text}


SLIDES = [
    slide(1, "תהליכים וחוטים", "תהליך (process) הוא תוכנית בריצה\nחוט (thread) חולק כתובות עם התהליך"),
    slide(2, "תזמון", "FCFS לפי סדר הגעה\nSJF בוחר את העבודה הקצרה\nRound Robin עם קוונטום"),
    slide(3, "זיכרון וירטואלי", "paging מחלק את הזיכרון לדפים\nטבלת דפים (page table) ממפה דף למסגרת"),
]

SEGMENTS = [
    seg(0, "נתחיל ממה זה תהליך: תהליך הוא תוכנית בריצה"),
    seg(5, "חוט, thread, חולק את הכתובות עם התהליך שלו"),
    seg(10, "אוקיי, שאלות?"),
    seg(15, "עכשיו תזמון. FCFS מתזמן לפי סדר ההגעה"),
    seg(20, "SJF בוחר את העבודה הקצרה ביותר, ו-Round Robin נותן קוונטום"),
    seg(25, "paging מחלק את הזיכרון הוירטואלי לדפים, וטבלת הדפים ממפה דף למסגרת"),
]


def as_map(aligned):
    return {a["slide"]: a["segments"] for a in aligned}


def test_distinct_vocabulary_maps_segments_to_their_slides(align):
    m = as_map(align.align(SLIDES, SEGMENTS))
    assert m[1] == [0, 1, 2]  # segment 2 ("אוקיי, שאלות?") has no overlap and attaches to the previous slide
    assert m[2] == [3, 4]
    assert m[3] == [5]


def test_output_lists_every_slide_in_order_including_empty_ones(align):
    aligned = align.align(SLIDES, SEGMENTS[:2])
    assert [a["slide"] for a in aligned] == [1, 2, 3]
    assert aligned[1]["segments"] == [] and aligned[2]["segments"] == []
    for a in aligned:
        assert set(a) == {"slide", "segments"}


def test_skipped_slide_allows_jump_from_one_to_three(align):
    segments = [SEGMENTS[0], SEGMENTS[1], SEGMENTS[5], seg(30, "טבלת הדפים ממפה כל דף למסגרת פיזית")]
    m = as_map(align.align(SLIDES, segments))
    assert m[1] == [0, 1]
    assert m[2] == []
    assert m[3] == [2, 3]


def test_filler_before_any_match_goes_to_first_slide(align):
    m = as_map(align.align(SLIDES, [seg(0, "בוקר טוב לכולם"), SEGMENTS[3]]))
    assert m[1] == [0]
    assert m[2] == [1]


def test_tie_breaks_by_proximity_to_previous_slide(align):
    slides = [slide(1, "A", "alpha beta"), slide(2, "B", "gamma delta"), slide(3, "C", "epsilon zeta")]
    segments = [seg(0, "alpha beta"), seg(5, "alpha epsilon"), seg(10, "epsilon zeta"), seg(15, "alpha epsilon")]
    m = as_map(align.align(slides, segments))
    assert 1 in m[1] and 1 not in m[3]  # tie resolved toward slide 1, the previous assignment
    assert 3 in m[3] and 3 not in m[1]  # same text later, now slide 3 is the previous assignment


def test_backward_jump_is_allowed_when_the_overlap_is_clear(align):
    segments = [SEGMENTS[0], SEGMENTS[5], seg(30, "נחזור רגע לתהליך ולחוט: חוט חולק כתובות עם התהליך")]
    m = as_map(align.align(SLIDES, segments))
    assert m[1] == [0, 2]
    assert m[3] == [1]


def test_nikud_and_case_do_not_block_matching(align):
    slides = [slide(1, "זִכָּרוֹן", "Paging וְדַפִּים"), slide(2, "אחר", "משהו אחר לגמרי")]
    m = as_map(align.align(slides, [seg(0, "paging מחלק את הזיכרון לדפים")]))
    assert m[1] == [0]


def test_cli_writes_aligned_json(tmp_path):
    s = tmp_path / "slides.json"
    t = tmp_path / "transcript.json"
    out = tmp_path / "aligned.json"
    s.write_text(json.dumps(SLIDES, ensure_ascii=False), encoding="utf-8")
    t.write_text(json.dumps(SEGMENTS, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(s), str(t), "--out", str(out), "--json"],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert as_map(data)[2] == [3, 4]
    summary = json.loads(r.stdout)
    assert summary["slides_without_speech"] == 0 and summary["segments"] == 6


def test_cli_missing_file_exits_2(tmp_path):
    r = subprocess.run([sys.executable, "-I", str(SCRIPT), str(tmp_path / "no.json"), str(tmp_path / "no2.json")],
                       capture_output=True, text=True, cwd=tmp_path)
    assert r.returncode == 2
