import pytest

from csv_summary.models import ColumnSummary, ColumnType, Summary
from csv_summary.report import NO_DATA_MESSAGE, format_mean, render_report


def test_no_data() -> None:
    assert render_report(None) == "No data rows found\n"
    assert NO_DATA_MESSAGE == "No data rows found"


def test_golden_all_types() -> None:
    summary = Summary(10, (
        ColumnSummary("n", ColumnType.NUMERIC, 1, min="1", max="3", mean=2.0),
        ColumnSummary("t", ColumnType.TEXT, 0, unique_count=4),
        ColumnSummary("d", ColumnType.DATE, 2, min="2023-06-01", max="2024-12-31"),
    ))
    assert render_report(summary) == (
        "Rows: 10\n"
        "\n"
        "Column 1: n\n  Type: numeric\n  Min: 1\n  Max: 3\n  Mean: 2\n  Nulls: 1\n"
        "\n"
        "Column 2: t\n  Type: text\n  Unique: 4\n  Nulls: 0\n"
        "\n"
        "Column 3: d\n  Type: date\n  Earliest: 2023-06-01\n  Latest: 2024-12-31\n"
        "  Nulls: 2\n"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2.0, "2"), (0.12345, "0.1235"), (-0.00001, "0"), (0.0, "0"),
        (-1.5, "-1.5"), (1234.5, "1234.5"), (1e300, "1e+300"),
        (-1.25e20, "-1.25e+20"), (float("inf"), "inf"), (float("-inf"), "-inf"),
        (float("nan"), "nan"), (1e14, "100000000000000"),
    ],
)
def test_format_mean(value: float, expected: str) -> None:
    assert format_mean(value) == expected


def test_control_characters_escaped() -> None:
    summary = Summary(1, (ColumnSummary("a\nb\x1b[0m", ColumnType.TEXT, 0, unique_count=1),))
    out = render_report(summary)
    assert "Column 1: a\\nb\\x1b[0m\n" in out
    assert out.count("\n") == 6


def test_empty_duplicate_and_long_names_not_truncated() -> None:
    long = "x" * 200
    summary = Summary(1, (
        ColumnSummary("", ColumnType.TEXT, 0, unique_count=1),
        ColumnSummary("dup", ColumnType.TEXT, 0, unique_count=1),
        ColumnSummary("dup", ColumnType.TEXT, 0, unique_count=1),
        ColumnSummary(long, ColumnType.TEXT, 0, unique_count=1),
    ))
    out = render_report(summary)
    assert "Column 1: \n" in out
    assert out.count("dup\n") == 2
    assert f"Column 4: {long}\n" in out


def test_render_is_deterministic() -> None:
    summary = Summary(1, (ColumnSummary("n", ColumnType.NUMERIC, 0, "1", "1", 1.0),))
    assert render_report(summary).encode() == render_report(summary).encode()
