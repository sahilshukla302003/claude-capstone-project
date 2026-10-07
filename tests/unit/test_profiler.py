import pytest

from csv_summary import profiler
from csv_summary.errors import CsvSummaryError
from csv_summary.models import ColumnType
from csv_summary.profiler import profile_file
from csv_summary.reader import open_records
from csv_summary.uniques import UniqueBudget


def test_empty_and_header_only_give_none_ac5_ac6(fixture_path) -> None:
    assert profile_file(str(fixture_path("empty.csv"))) is None
    assert profile_file(str(fixture_path("header_only.csv"))) is None


def test_numeric_and_text_ac8_ac9(fixture_path) -> None:
    summary = profile_file(str(fixture_path("ac8_9.csv")))
    assert summary.row_count == 4
    num, text = summary.columns
    assert (num.type, num.min, num.max, num.mean, num.null_count) == (
        ColumnType.NUMERIC, "1", "3", 2.0, 1)
    assert (text.type, text.unique_count, text.null_count) == (ColumnType.TEXT, 2, 1)


def test_typical_file_ac1(fixture_path) -> None:
    summary = profile_file(str(fixture_path("typical.csv")))
    assert summary.row_count == 10
    assert [c.type.value for c in summary.columns] == ["numeric", "text", "date"]


def test_reader_opened_once_without_text_columns(monkeypatch, write_csv) -> None:
    calls = []

    def counting(path):
        calls.append(path)
        return open_records(path)

    monkeypatch.setattr(profiler, "open_records", counting)
    profile_file(str(write_csv("n,d\n1,2024-01-01\n2,2024-01-02\n")))
    assert len(calls) == 1


def test_all_null_text_column_zero_without_pass2(monkeypatch, fixture_path) -> None:
    calls = []

    def counting(path):
        calls.append(path)
        return open_records(path)

    monkeypatch.setattr(profiler, "open_records", counting)
    summary = profile_file(str(fixture_path("all_null.csv")))
    assert len(calls) == 1
    assert all(c.type is ColumnType.TEXT and c.unique_count == 0 for c in summary.columns)
    assert all(c.null_count == 4 for c in summary.columns)


def test_mixed_column_gets_uniques_from_pass2(fixture_path) -> None:
    col = profile_file(str(fixture_path("mixed.csv"))).columns[0]
    assert col.type is ColumnType.TEXT and col.unique_count == 3


def test_tiny_budget_forces_tier2(write_csv) -> None:
    rows = "\n".join(f"v{i % 300}" for i in range(2000))
    path = write_csv("t\n" + rows + "\n")
    summary = profile_file(str(path), budget=UniqueBudget(1000, 20))
    assert summary.columns[0].unique_count == 300


def test_pass2_mismatch_raises(monkeypatch, write_csv) -> None:
    path = write_csv("t\na\nb\nc\n")
    calls = []

    def flaky(p):
        calls.append(p)
        records = open_records(p)
        if len(calls) == 1:
            return records
        return iter([next(records), next(records)])

    class Wrapper:
        def __init__(self, it):
            self.it = iter(it)

        def __iter__(self):
            return self

        def __next__(self):
            return next(self.it)

        def close(self):
            pass

    monkeypatch.setattr(profiler, "open_records",
                        lambda p: Wrapper(flaky(p)))
    with pytest.raises(CsvSummaryError, match="file changed while being read"):
        profile_file(str(path))


def test_reader_errors_propagate(fixture_path) -> None:
    with pytest.raises(CsvSummaryError):
        profile_file(str(fixture_path("wide_row.csv")))
