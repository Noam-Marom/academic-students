"""The benchmark is reproducible from a seed and reports recall per technique and the false-positive rate."""
import csv
import json
import pathlib

from conftest import load_module

BENCH = pathlib.Path(__file__).resolve().parents[1] / "benchmark"


def test_generate_writes_labelled_corpus(tmp_path):
    gen = load_module(BENCH / "generate.py", "scanner_bench_generate")
    labels = gen.generate(tmp_path / "corpus", seed=42, n_per_cell=1)
    rows = list(csv.DictReader(open(tmp_path / "corpus" / "labels.csv", encoding="utf-8")))
    assert rows and set(rows[0]) == {"path", "technique", "filetype", "language", "intent", "label"}
    assert {r["label"] for r in rows} == {"injection", "canary", "benign"}
    assert {r["language"] for r in rows} >= {"en", "he"}
    for r in rows:
        assert (tmp_path / "corpus" / r["path"]).exists(), r["path"]
    assert len(labels) == len(rows)


def test_generate_is_deterministic_for_a_seed(tmp_path):
    gen = load_module(BENCH / "generate.py", "scanner_bench_generate2")
    a = gen.generate(tmp_path / "a", seed=7, n_per_cell=1)
    b = gen.generate(tmp_path / "b", seed=7, n_per_cell=1)
    assert [r["path"] for r in a] == [r["path"] for r in b]
    for ra in a:
        pa, pb = tmp_path / "a" / ra["path"], tmp_path / "b" / ra["path"]
        if pa.is_file() and pa.suffix != ".pdf":  # PDF writers embed a random /ID and timestamps
            assert pa.read_bytes() == pb.read_bytes(), ra["path"]


def test_run_benchmark_reports_recall_and_fpr(tmp_path):
    gen = load_module(BENCH / "generate.py", "scanner_bench_generate3")
    run = load_module(BENCH / "run_benchmark.py", "scanner_bench_run")
    gen.generate(tmp_path / "corpus", seed=1, n_per_cell=1)
    result = run.run(tmp_path / "corpus", tmp_path / "corpus" / "labels.csv", quick=True, out_dir=tmp_path / "out")
    assert set(result) >= {"recall_by_technique", "false_positive_rate", "n", "recall_overall", "md_table"}
    assert 0.0 <= result["false_positive_rate"] <= 1.0
    assert result["n"]["benign"] > 0 and result["n"]["injection"] > 0
    assert "| Technique |" in result["md_table"]
    (tmp_path / "table.md").write_text(result["md_table"], encoding="utf-8")
    json.dumps(result)  # serialisable
