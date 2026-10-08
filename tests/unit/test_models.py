import dataclasses

import pytest

from csv_summary.models import ColumnSummary, ColumnType, Summary


def test_enum_values() -> None:
    assert [t.value for t in ColumnType] == ["numeric", "text", "date"]
    assert ColumnType.TEXT == "text"


def test_defaults_and_immutability() -> None:
    col = ColumnSummary("a", ColumnType.TEXT, 0)
    assert (col.min, col.max, col.mean, col.unique_count) == (None,) * 4
    with pytest.raises(dataclasses.FrozenInstanceError):
        col.name = "b"  # type: ignore[misc]
    summary = Summary(1, (col,))
    with pytest.raises(dataclasses.FrozenInstanceError):
        summary.row_count = 2  # type: ignore[misc]


def test_replace_fills_unique_count() -> None:
    col = ColumnSummary("a", ColumnType.TEXT, 1)
    new = dataclasses.replace(col, unique_count=3)
    assert new.unique_count == 3
    assert col.unique_count is None
