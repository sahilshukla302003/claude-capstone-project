"""Type inference: parsers and the per-column accumulator used in pass 1."""

from __future__ import annotations

import re
from datetime import date, time
from math import isfinite

from .models import ColumnSummary, ColumnType

_NUMBER_RE = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", re.ASCII)
_DATE_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})"
    r"(?:T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?)?",
    re.ASCII,
)

_UNDECIDED, _NUMERIC, _DATE, _TEXT = 0, 1, 2, 3


def is_null(raw: str) -> bool:
    """A field is null when it is empty or whitespace-only."""
    return raw.strip() == ""


def parse_number(token: str) -> float | None:
    """Parse an already stripped token as a finite decimal number, else None.

    ``float()`` runs first (fast path); the ASCII regex then rejects what
    ``float`` accepts but we do not (nan, inf, hex-like, underscores, non-ASCII
    digits).
    """
    try:
        value = float(token)
    except ValueError:
        return None
    if not isfinite(value) or _NUMBER_RE.fullmatch(token) is None:
        return None
    return value


def parse_date(token: str) -> tuple[int, ...] | None:
    """Parse an ISO 8601 date or datetime (no offset); return a sort key."""
    match = _DATE_RE.fullmatch(token)
    if match is None:
        return None
    y, mo, d, hh, mi, ss, frac = match.groups()
    try:
        date(int(y), int(mo), int(d))
        micro = int(frac.ljust(6, "0")) if frac else 0
        hour, minute, second = int(hh or 0), int(mi or 0), int(ss or 0)
        time(hour, minute, second, micro)
    except ValueError:
        return None
    return (int(y), int(mo), int(d), hour, minute, second, micro)


class ColumnAccumulator:
    """Streaming statistics and type candidacy for one column."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.non_null = 0
        self.null_count = 0
        self._mode = _UNDECIDED
        self._min_v = 0.0
        self._max_v = 0.0
        self._min_tok: str | None = None
        self._max_tok: str | None = None
        self._sum = 0.0
        self._comp = 0.0
        self._min_key: tuple[int, ...] | None = None
        self._max_key: tuple[int, ...] | None = None

    def observe(self, raw: str) -> None:
        token = raw.strip()
        if not token:
            self.null_count += 1
            return
        self.non_null += 1
        mode = self._mode
        if mode == _TEXT:
            return
        if mode != _DATE:
            value = parse_number(token)
            if value is not None:
                self._mode = _NUMERIC
                self._add_number(value, token)
                return
            if mode == _NUMERIC:
                self._demote()
                return
        key = parse_date(token)
        if key is None:
            self._demote()
            return
        self._mode = _DATE
        self._add_date(key, token)

    def _demote(self) -> None:
        self._mode = _TEXT
        self._min_tok = self._max_tok = None
        self._min_key = self._max_key = None

    def _add_number(self, value: float, token: str) -> None:
        if self._min_tok is None:
            self._min_v = self._max_v = value
            self._min_tok = self._max_tok = token
        elif value < self._min_v:
            self._min_v, self._min_tok = value, token
        elif value > self._max_v:
            self._max_v, self._max_tok = value, token
        total = self._sum
        new = total + value
        if abs(total) >= abs(value):
            self._comp += (total - new) + value
        else:
            self._comp += (value - new) + total
        self._sum = new

    def _add_date(self, key: tuple[int, ...], token: str) -> None:
        if self._min_key is None or self._max_key is None:
            self._min_key = self._max_key = key
            self._min_tok = self._max_tok = token
        elif key < self._min_key:
            self._min_key, self._min_tok = key, token
        elif key > self._max_key:
            self._max_key, self._max_tok = key, token

    @property
    def needs_unique_pass(self) -> bool:
        return self.non_null > 0 and self._mode == _TEXT

    def _mean(self) -> float:
        total = self._sum
        if isfinite(total):
            total += self._comp
        if total != total:
            return float("nan")
        return total / self.non_null

    def finish(self, row_count: int) -> ColumnSummary:
        """Final type decision. unique_count stays None; the profiler fills it."""
        del row_count  # nulls are counted directly
        if self.non_null == 0 or self._mode == _TEXT:
            return ColumnSummary(self.name, ColumnType.TEXT, self.null_count)
        if self._mode == _NUMERIC:
            return ColumnSummary(
                self.name, ColumnType.NUMERIC, self.null_count,
                min=self._min_tok, max=self._max_tok, mean=self._mean(),
            )
        return ColumnSummary(
            self.name, ColumnType.DATE, self.null_count,
            min=self._min_tok, max=self._max_tok,
        )
