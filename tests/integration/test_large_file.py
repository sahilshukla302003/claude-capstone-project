"""AC-16 / NFR-1 / NFR-2: 100 MB files. Run with ``pytest -m slow``."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.helpers.gen_large_csv import generate_variant_a, generate_variant_b

ROOT = Path(__file__).resolve().parents[2]
TARGET_BYTES = 100 * 1_000_000
MAX_PEAK = 512 * 2**20
MAX_SECONDS = 120


def run_with_peak(path: Path) -> tuple[subprocess.CompletedProcess, float, int]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    script = str(ROOT / "tests" / "helpers" / "run_with_peak.py")
    start = time.perf_counter()
    proc = subprocess.run([sys.executable, script, str(path)], capture_output=True,
                          text=True, env=env, check=False)
    elapsed = time.perf_counter() - start
    peak = int(proc.stderr.strip().splitlines()[-1].split("=")[1])
    return proc, elapsed, peak


def check(path: Path, label: str) -> str:
    proc, elapsed, peak = run_with_peak(path)
    print(f"\nMEASURED {label}: peak={peak / 2**20:.0f} MiB wall={elapsed:.1f} s")
    assert proc.returncode == 0, proc.stderr
    assert peak <= MAX_PEAK
    assert elapsed <= MAX_SECONDS
    return proc.stdout.replace("\r\n", "\n")


@pytest.mark.slow
def test_ac16_variant_a_all_distinct_column(tmp_path) -> None:
    """AC-16 variant A: numeric, date, low-cardinality and all-distinct text."""
    path = tmp_path / "a.csv"
    info = generate_variant_a(path, TARGET_BYTES)
    out = check(path, "variant A")
    assert f"Rows: {info['rows']}" in out
    assert "Type: text\n  Unique: 50\n" in out
    assert f"Type: text\n  Unique: {info['uid']}\n" in out


@pytest.mark.slow
def test_ac16_variant_b_multi_column_high_cardinality(tmp_path) -> None:
    """AC-16 variant B: several high-cardinality text columns."""
    path = tmp_path / "b.csv"
    info = generate_variant_b(path, TARGET_BYTES)
    out = check(path, "variant B")
    assert out.count(f"Type: text\n  Unique: {info['per_column']}\n") == info["columns"]
