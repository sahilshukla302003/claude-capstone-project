import csv
import os
import subprocess
import sys
from pathlib import Path

from tests.helpers.gen_large_csv import generate_variant_a, generate_variant_b

ROOT = Path(__file__).resolve().parents[2]


def read_columns(path: Path) -> tuple[list[str], list[list[str]]]:
    with open(path, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    return rows[0], rows[1:]


def test_variant_a_counts(tmp_path) -> None:
    path = tmp_path / "a.csv"
    info = generate_variant_a(path, 200_000)
    header, rows = read_columns(path)
    assert header == ["id", "day", "category", "uid"]
    assert len(rows) == info["rows"] >= 1
    assert len({r[3] for r in rows}) == info["uid"] == len(rows)
    assert len({r[2] for r in rows}) == min(50, len(rows))
    assert path.stat().st_size >= 200_000


def test_variant_b_counts(tmp_path) -> None:
    path = tmp_path / "b.csv"
    info = generate_variant_b(path, 100_000)
    header, rows = read_columns(path)
    assert len(header) == info["columns"]
    for col in range(len(header)):
        assert len({r[col] for r in rows}) == info["per_column"] == len(rows)


def test_peak_wrapper_prints_parseable_number_and_passes_exit_code(tmp_path) -> None:
    sample = tmp_path / "s.csv"
    generate_variant_a(sample, 20_000)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    script = str(ROOT / "tests" / "helpers" / "run_with_peak.py")
    ok = subprocess.run([sys.executable, script, str(sample)], capture_output=True,
                        text=True, env=env, check=False)
    assert ok.returncode == 0
    peak = int(ok.stderr.strip().splitlines()[-1].split("=")[1])
    assert peak > 0
    bad = subprocess.run([sys.executable, script, str(tmp_path / "none.csv")],
                         capture_output=True, text=True, env=env, check=False)
    assert bad.returncode == 1
