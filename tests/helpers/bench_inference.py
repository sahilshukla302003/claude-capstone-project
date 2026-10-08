"""Micro-benchmark: microseconds per cell for ColumnAccumulator.observe.

Run: PYTHONPATH=src python tests/helpers/bench_inference.py [n_cells]
Gate: if the numeric figure exceeds about 4 us/cell, optimise observe.
"""

from __future__ import annotations

import sys
import time

from csv_summary.inference import ColumnAccumulator


def _cells(kind: str, n: int) -> list[str]:
    if kind == "numeric":
        return [f"{i}.{i % 100}" for i in range(n)]
    if kind == "date":
        return [f"2024-{i % 12 + 1:02d}-{i % 28 + 1:02d}T10:30:00" for i in range(n)]
    if kind == "text":
        return [f"value{i}" for i in range(n)]
    return [str(i) if i % 1000 else "x" for i in range(n)]  # mixed -> demoted


def bench(kind: str, n: int) -> float:
    cells = _cells(kind, n)
    acc = ColumnAccumulator(kind)
    start = time.perf_counter()
    for cell in cells:
        acc.observe(cell)
    return (time.perf_counter() - start) / n * 1e6


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3_000_000
    for kind in ("numeric", "date", "text", "mixed"):
        print(f"{kind}: {bench(kind, n):.3f} us/cell")


if __name__ == "__main__":
    main()
