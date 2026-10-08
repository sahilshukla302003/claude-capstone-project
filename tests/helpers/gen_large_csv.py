"""Streaming generators for large CSV test files (never held in memory)."""

from __future__ import annotations

import argparse
from pathlib import Path

_CHUNK_ROWS = 50_000
_MULT_A = 0x9E3779B97F4A7C15 | 1  # odd => bijective modulo 2**40
_MULT_B = (0x9E3779B1, 0x85EBCA6B, 0xC2B2AE35, 0x27D4EB2F,
           0x165667B1, 0xD3A2646D, 0xFD7046C5, 0xB55A4F09)  # all odd


def _write_chunks(path: Path, header: str, target_bytes: int, row_fn) -> int:
    """Write rows from ``row_fn(i)`` until the file reaches ``target_bytes``."""
    rows = 0
    written = 0
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(header + "\n")
        written += len(header) + 1
        while written < target_bytes:
            chunk = "".join(row_fn(i) + "\n" for i in range(rows, rows + _CHUNK_ROWS))
            handle.write(chunk)
            written += len(chunk)
            rows += _CHUNK_ROWS
    return rows


def generate_variant_a(path: Path, target_bytes: int) -> dict[str, int]:
    """numeric id, date, low-cardinality text, all-distinct text."""

    def row(i: int) -> str:
        uid = f"{(i * _MULT_A) % 2**40:010x}"
        return f"{i},2024-{i % 12 + 1:02d}-{i % 28 + 1:02d},cat{i % 50},{uid}"

    rows = _write_chunks(Path(path), "id,day,category,uid", target_bytes, row)
    return {"rows": rows, "category": 50, "uid": rows}


def generate_variant_b(path: Path, target_bytes: int) -> dict[str, int]:
    """Eight all-distinct 6-hex-digit text columns (multi-column high cardinality)."""

    def row(i: int) -> str:
        return ",".join(f"{(i * m) % 2**24:06x}" for m in _MULT_B)

    header = ",".join(f"t{k}" for k in range(len(_MULT_B)))
    rows = _write_chunks(Path(path), header, target_bytes, row)
    return {"rows": rows, "per_column": rows, "columns": len(_MULT_B)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a large CSV file.")
    parser.add_argument("path")
    parser.add_argument("--variant", choices=["a", "b"], default="a")
    parser.add_argument("--mb", type=float, default=1.0)
    args = parser.parse_args()
    gen = generate_variant_a if args.variant == "a" else generate_variant_b
    print(gen(Path(args.path), int(args.mb * 1_000_000)))


if __name__ == "__main__":
    main()
