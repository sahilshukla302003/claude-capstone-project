"""Two-pass profiling: types and statistics first, unique counts second."""

from __future__ import annotations

from dataclasses import replace

from .errors import CsvSummaryError, escape_control
from .inference import ColumnAccumulator
from .models import ColumnSummary, ColumnType, Summary
from .reader import open_records
from .uniques import UniqueBudget, UniqueCounter


def _pass1(path: str) -> tuple[list[ColumnAccumulator], int] | None:
    records = open_records(path)
    try:
        header = next(records, None)
        if header is None:
            return None
        accs = [ColumnAccumulator(name) for name in header]
        rows = 0
        for record in records:
            rows += 1
            for acc, raw in zip(accs, record):
                acc.observe(raw)
    finally:
        records.close()
    return accs, rows


def _pass2(
    path: str, indices: list[int], row_count: int, budget: UniqueBudget | None
) -> list[int]:
    counter = UniqueCounter(len(indices), budget)
    records = open_records(path)
    rows = 0
    try:
        next(records, None)
        slots = list(enumerate(indices))
        for record in records:
            rows += 1
            for slot, index in slots:
                value = record[index]
                if value.strip():
                    counter.add(slot, value)
    finally:
        records.close()
    if rows != row_count:
        raise CsvSummaryError(f"{escape_control(path)}: file changed while being read")
    return [counter.count(slot) for slot in range(len(indices))]


def profile_file(path: str, *, budget: UniqueBudget | None = None) -> Summary | None:
    """Return None if the file has no data rows (0 bytes or header only)."""
    first = _pass1(path)
    if first is None or first[1] == 0:
        return None
    accs, row_count = first
    summaries: list[ColumnSummary] = [a.finish(row_count) for a in accs]
    indices = [i for i, a in enumerate(accs) if a.needs_unique_pass]
    counts = _pass2(path, indices, row_count, budget) if indices else []
    for index, number in zip(indices, counts):
        summaries[index] = replace(summaries[index], unique_count=number)
    for index, summary in enumerate(summaries):
        if summary.type is ColumnType.TEXT and summary.unique_count is None:
            summaries[index] = replace(summary, unique_count=0)
    return Summary(row_count, tuple(summaries))
