import math

import pytest

from csv_summary.inference import ColumnAccumulator
from csv_summary.models import ColumnType


def run(values: list[str]) -> tuple[ColumnAccumulator, object]:
    acc = ColumnAccumulator("c")
    for v in values:
        acc.observe(v)
    return acc, acc.finish(len(values))


def test_numeric_stats_ac8() -> None:
    _, s = run(["1", "2", "3", ""])
    assert (s.type, s.min, s.max, s.mean, s.null_count) == (
        ColumnType.NUMERIC, "1", "3", 2.0, 1)


def test_mixed_demotes_to_text_ac11() -> None:
    acc, s = run(["1", "2", "abc"])
    assert s.type is ColumnType.TEXT and s.min is None and s.mean is None
    assert acc.needs_unique_pass


def test_whitespace_is_null_ac12() -> None:
    _, s = run(["1", "  ", "\t", "3"])
    assert s.type is ColumnType.NUMERIC and s.null_count == 2 and s.mean == 2.0


def test_all_null_is_text_ac13() -> None:
    acc, s = run(["", " ", "", ""])
    assert s.type is ColumnType.TEXT and s.null_count == 4
    assert not acc.needs_unique_pass


def test_ties_keep_first_token() -> None:
    _, s = run(["1", "1.0", "1.00"])
    assert (s.min, s.max) == ("1", "1")


def test_min_max_source_tokens_and_signs() -> None:
    _, s = run([" 1e3 ", "-5", "007", "+2.5"])
    assert (s.min, s.max) == ("-5", "1e3")


def test_numeric_then_date_demotes() -> None:
    _, s = run(["1", "2024-01-01"])
    assert s.type is ColumnType.TEXT


def test_date_then_number_demotes() -> None:
    _, s = run(["2024-01-01", "5"])
    assert s.type is ColumnType.TEXT


def test_dates_ac10() -> None:
    _, s = run(["2024-01-15", "2023-06-01", "2024-12-31", ""])
    assert (s.type, s.min, s.max, s.null_count) == (
        ColumnType.DATE, "2023-06-01", "2024-12-31", 1)


def test_dates_mixed_date_only_and_datetime() -> None:
    _, s = run(["2024-01-15T10:00", "2024-01-15", "2024-01-15T23:59:59", "2024-01-15"])
    assert (s.min, s.max) == ("2024-01-15", "2024-01-15T23:59:59")


def test_neumaier_accuracy() -> None:
    _, s = run(["0.1"] * 1_000_000)
    assert abs(s.mean - 0.1) < 1e-15
    _, s = run(["1e16", "1", "-1e16", "1"])
    assert s.mean == pytest.approx(0.5)


def test_overflow_gives_inf_without_exception() -> None:
    _, s = run(["1e308", "1e308"])
    assert s.mean == math.inf
    _, s = run(["-1e308", "-1e308"])
    assert s.mean == -math.inf


def test_cancelling_large_values_finite() -> None:
    _, s = run(["1e308", "-1e308"])
    assert s.mean == 0.0


def test_nan_inf_make_text() -> None:
    assert run(["1", "nan"])[1].type is ColumnType.TEXT
    assert run(["inf"])[1].type is ColumnType.TEXT


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["a"], True), (["1"], False), (["2024-01-01"], False),
        ([""], False), (["1", "a"], True), ([], False),
    ],
)
def test_needs_unique_pass(values: list[str], expected: bool) -> None:
    assert run(values)[0].needs_unique_pass is expected


def test_demoted_column_still_counts_nulls() -> None:
    _, s = run(["a", "", "b", " "])
    assert s.null_count == 2 and s.type is ColumnType.TEXT
