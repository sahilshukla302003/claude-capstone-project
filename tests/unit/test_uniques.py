import os
import random
import subprocess
import sys

import pytest

from pathlib import Path

from csv_summary.uniques import UniqueBudget, UniqueCounter

SRC = Path(__file__).resolve().parents[2] / "src"


def feed(counter: UniqueCounter, data: dict[int, list[str]]) -> None:
    longest = max(len(v) for v in data.values())
    for pos in range(longest):
        for col, values in data.items():
            if pos < len(values):
                counter.add(col, values[pos])


def test_tier1_exact_counts_multiple_columns() -> None:
    data = {0: ["a", "b", "a", "c"], 1: ["x", "x", "x"], 2: []}
    counter = UniqueCounter(3)
    feed(counter, {k: v for k, v in data.items() if v})
    assert [counter.count(i) for i in range(3)] == [3, 1, 0]
    assert not any(counter.is_hashed(i) for i in range(3))


def test_empty_and_padded_values_are_distinct() -> None:
    counter = UniqueCounter(1)
    for v in ["a", " a", "a ", "a"]:
        counter.add(0, v)
    assert counter.count(0) == 3


def test_add_after_count_raises_and_count_is_idempotent() -> None:
    counter = UniqueCounter(1)
    counter.add(0, "a")
    assert counter.count(0) == counter.count(0) == 1
    with pytest.raises(RuntimeError):
        counter.add(0, "b")


def test_charge_accounting_via_tiny_budget() -> None:
    counter = UniqueCounter(1, UniqueBudget(exact_limit_bytes=10**9))
    counter.add(0, "abc")
    counter.add(0, "abc")  # duplicates are free
    first = counter._total
    assert first > 100
    counter.add(0, "abd")
    assert counter._total == 2 * first
    assert not counter.is_hashed(0)


def test_conversion_flips_is_hashed_and_counts_match() -> None:
    counter = UniqueCounter(1, UniqueBudget(exact_limit_bytes=2000, pending_limit=10))
    values = [f"v{i % 700}" for i in range(3000)]
    for v in values:
        counter.add(0, v)
    assert counter.is_hashed(0)
    assert counter.count(0) == 700


def test_multiple_compactions_and_duplicates_after_conversion() -> None:
    rng = random.Random(1)
    values = [str(rng.randrange(5000)) for _ in range(30000)]
    counter = UniqueCounter(1, UniqueBudget(exact_limit_bytes=500, pending_limit=50))
    for v in values:
        counter.add(0, v)
    assert counter.is_hashed(0)
    assert counter.count(0) == len(set(values))


def test_largest_column_evicted_first_and_credit_keeps_others_exact() -> None:
    counter = UniqueCounter(2, UniqueBudget(exact_limit_bytes=6000, pending_limit=100))
    small = [f"s{i}" for i in range(5)]
    big = [f"big-value-{i}" for i in range(200)]
    for v in small:
        counter.add(0, v)
    for v in big:
        counter.add(1, v)
    assert counter.is_hashed(1) and not counter.is_hashed(0)
    assert counter.count(0) == 5 and counter.count(1) == 200


def test_repeated_eviction_until_under_budget() -> None:
    counter = UniqueCounter(3, UniqueBudget(exact_limit_bytes=1, pending_limit=5))
    data = {0: ["a", "b"], 1: ["c"], 2: ["d", "e", "f"]}
    feed(counter, data)
    assert all(counter.is_hashed(i) for i in range(3))
    assert [counter.count(i) for i in range(3)] == [2, 1, 3]


def test_random_many_duplicates_matches_oracle() -> None:
    rng = random.Random(7)
    data = {c: [str(rng.randrange(3000)) for _ in range(8000)] for c in range(3)}
    counter = UniqueCounter(3, UniqueBudget(exact_limit_bytes=60_000, pending_limit=200))
    feed(counter, data)
    for c, values in data.items():
        assert counter.count(c) == len(set(values))


def test_determinism_across_processes() -> None:
    code = (
        "from csv_summary.uniques import UniqueBudget, UniqueCounter\n"
        "c = UniqueCounter(1, UniqueBudget(1, 3))\n"
        "[c.add(0, str(i % 97)) for i in range(1000)]\n"
        "print(c.count(0))\n"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    outs = {
        subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       check=True, env=env).stdout.strip()
        for _ in range(2)
    }
    assert outs == {"97"}
