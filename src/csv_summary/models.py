"""Immutable data carried from the profiler to the report."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ColumnType(str, Enum):
    NUMERIC = "numeric"
    TEXT = "text"
    DATE = "date"


@dataclass(frozen=True)
class ColumnSummary:
    name: str
    type: ColumnType
    null_count: int
    min: str | None = None  # numeric: source token of the minimum; date: earliest
    max: str | None = None  # numeric: source token of the maximum; date: latest
    mean: float | None = None  # numeric only
    unique_count: int | None = None  # text only


@dataclass(frozen=True)
class Summary:
    row_count: int
    columns: tuple[ColumnSummary, ...]  # file order
