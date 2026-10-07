"""Memory-bounded unique-value counting for text columns.

Tier 1 keeps an exact ``set`` per column. When the shared exact total exceeds
the budget, the largest column is converted to Tier 2: 128-bit blake2b digests
stored in 256 buckets of ``array("Q")`` pairs. Collision probability for n
distinct values is about n**2 / 2**129 (below 1e-21 at n = 1e8).
"""

from __future__ import annotations

import sys
from array import array
from hashlib import blake2b

_BUCKETS = 256
_ENTRY_OVERHEAD = 100  # set slot, resize and fragmentation allowance per entry


class UniqueBudget:
    """Limits for the unique counter (both injectable).

    Defaults (confirmed by the large-file test): ``exact_limit_bytes`` = 48 MiB
    shared by all exact sets, and ``pending_limit`` = 2,000,000 uncompacted
    digests across all hashed columns.
    """

    def __init__(
        self, exact_limit_bytes: int = 48 * 2**20, pending_limit: int = 2_000_000
    ) -> None:
        self.exact_limit_bytes = exact_limit_bytes
        self.pending_limit = pending_limit


class UniqueCounter:
    """Exact (Tier 1) or digest-based (Tier 2) distinct counts per column."""

    def __init__(self, n_columns: int, budget: UniqueBudget | None = None) -> None:
        self._budget = budget or UniqueBudget()
        self._sets: list[set[str] | None] = [set() for _ in range(n_columns)]
        self._charge = [0] * n_columns
        self._total = 0
        self._buckets: list[list[tuple[array, array]] | None] = [None] * n_columns
        self._pending = 0
        self._compacted = 0
        self._counting = False

    def is_hashed(self, column_index: int) -> bool:
        return self._buckets[column_index] is not None

    def add(self, column_index: int, value: str) -> None:
        """Record a non-null, un-stripped value. Illegal after ``count``."""
        if self._counting:
            raise RuntimeError("add() called after count()")
        values = self._sets[column_index]
        if values is None:
            self._add_hashed(column_index, value)
            return
        if value in values:
            return
        values.add(value)
        cost = sys.getsizeof(value) + _ENTRY_OVERHEAD
        self._charge[column_index] += cost
        self._total += cost
        if self._total > self._budget.exact_limit_bytes:
            self._evict()

    def count(self, column_index: int) -> int:
        """Distinct count; idempotent."""
        self._counting = True
        values = self._sets[column_index]
        if values is not None:
            return len(values)
        self._compact()
        buckets = self._buckets[column_index]
        assert buckets is not None
        return sum(len(hi) for hi, _ in buckets)

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _digest(value: str) -> tuple[int, int, int]:
        raw = blake2b(value.encode("utf-8", "surrogatepass"), digest_size=16).digest()
        return raw[0], int.from_bytes(raw[:8], "big"), int.from_bytes(raw[8:], "big")

    def _add_hashed(self, column_index: int, value: str) -> None:
        buckets = self._buckets[column_index]
        assert buckets is not None
        b, hi, lo = self._digest(value)
        buckets[b][0].append(hi)
        buckets[b][1].append(lo)
        self._pending += 1
        self._maybe_compact()

    def _evict(self) -> None:
        limit = self._budget.exact_limit_bytes
        while self._total > limit:
            candidates = [i for i, s in enumerate(self._sets) if s is not None]
            if not candidates:
                return
            self._convert(max(candidates, key=lambda i: (self._charge[i], -i)))

    def _convert(self, column_index: int) -> None:
        values = self._sets[column_index]
        assert values is not None
        buckets = [(array("Q"), array("Q")) for _ in range(_BUCKETS)]
        self._buckets[column_index] = buckets
        for value in values:
            b, hi, lo = self._digest(value)
            buckets[b][0].append(hi)
            buckets[b][1].append(lo)
        self._pending += len(values)
        self._sets[column_index] = None
        self._total -= self._charge[column_index]
        self._charge[column_index] = 0
        self._maybe_compact()

    def _maybe_compact(self) -> None:
        threshold = max(self._budget.pending_limit, self._compacted // 4)
        if self._pending > threshold:
            self._compact()

    def _compact(self) -> None:
        if self._pending == 0:
            return
        compacted = 0
        for buckets in self._buckets:
            if buckets is None:
                continue
            for index, (hi, lo) in enumerate(buckets):
                unique = set(zip(hi, lo))
                new_hi, new_lo = array("Q"), array("Q")
                for h, low in unique:
                    new_hi.append(h)
                    new_lo.append(low)
                buckets[index] = (new_hi, new_lo)
                compacted += len(unique)
        self._compacted = compacted
        self._pending = 0
