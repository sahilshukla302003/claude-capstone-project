import csv
import os
from pathlib import Path

import pytest

from csv_summary import reader
from csv_summary.errors import CsvSummaryError
from csv_summary.reader import open_records


def records(path: Path) -> list[list[str]]:
    return list(open_records(str(path)))


def test_short_rows_are_padded_ac15(fixture_path) -> None:
    assert records(fixture_path("short_rows.csv")) == [
        ["a", "b", "c"], ["1", "2", ""], ["3", "4", "5"],
    ]


def test_wide_row_is_error_with_line_number_ac15(fixture_path) -> None:
    with pytest.raises(CsvSummaryError, match=r"line 3: row has 3 fields but header has 2"):
        records(fixture_path("wide_row.csv"))


def test_blank_lines_skipped(fixture_path) -> None:
    assert records(fixture_path("blank_lines.csv")) == [["a"], ["1"], ["2"]]


def test_blank_lines_before_header(write_csv) -> None:
    assert records(write_csv("\n\na,b\n1,2\n")) == [["a", "b"], ["1", "2"]]


def test_bom_is_stripped(fixture_path) -> None:
    assert records(fixture_path("bom.csv"))[0] == ["a", "b"]


def test_quoted_and_embedded_newline_ac14(fixture_path) -> None:
    assert records(fixture_path("quoted.csv")) == [
        ["a", "b"], ["x,y", "1"], ["line1\nline2", "2"],
    ]


def test_invalid_utf8_ac17(fixture_path) -> None:
    with pytest.raises(CsvSummaryError, match="invalid UTF-8 encoding"):
        records(fixture_path("invalid_utf8.csv"))


def test_directory(tmp_path) -> None:
    with pytest.raises(CsvSummaryError, match="is a directory"):
        records(tmp_path)


def test_missing_path(tmp_path) -> None:
    with pytest.raises(CsvSummaryError, match="file not found: .*nope.csv"):
        records(tmp_path / "nope.csv")


def test_strict_quote_error_has_line_number(fixture_path) -> None:
    with pytest.raises(CsvSummaryError, match=r"line 2: "):
        records(fixture_path("bad_quote.csv"))


def test_unterminated_quote_hits_field_limit(write_csv) -> None:
    big = '"' + "x" * (11 * 1024 * 1024)
    with pytest.raises(CsvSummaryError, match="field larger than field limit"):
        records(write_csv("a\n" + big))


def test_empty_file_yields_nothing(fixture_path) -> None:
    assert records(fixture_path("empty.csv")) == []


def test_path_control_characters_escaped(tmp_path) -> None:
    with pytest.raises(CsvSummaryError) as info:
        records(tmp_path / "bad\nname.csv")
    assert "\n" not in info.value.message
    assert "bad\\nname.csv" in info.value.message


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs POSIX FIFOs")
def test_fifo_rejected(tmp_path) -> None:
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(CsvSummaryError, match="not a regular file"):
        records(fifo)


def test_non_regular_file_rejected_via_stat(monkeypatch, write_csv) -> None:
    path = write_csv("a\n1\n")
    monkeypatch.setattr(reader.stat, "S_ISREG", lambda mode: False)
    with pytest.raises(CsvSummaryError, match="not a regular file"):
        records(path)


def test_oserror_on_open_is_mapped(monkeypatch, write_csv) -> None:
    path = write_csv("a\n1\n")

    def deny(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr("builtins.open", deny)
    with pytest.raises(CsvSummaryError, match="cannot read .*Permission denied"):
        records(path)


def test_stat_oserror_is_mapped(monkeypatch, write_csv) -> None:
    path = write_csv("a\n1\n")

    def deny(p):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(reader.os, "stat", deny)
    with pytest.raises(CsvSummaryError, match="cannot read .*Permission denied"):
        records(path)


def test_generator_closes_file(monkeypatch, write_csv) -> None:
    path = write_csv("a\n1\n2\n")
    opened = []
    real_open = open

    def tracking(*args, **kwargs):
        handle = real_open(*args, **kwargs)
        opened.append(handle)
        return handle

    monkeypatch.setattr("builtins.open", tracking)
    gen = open_records(str(path))
    next(gen)
    assert not opened[0].closed
    gen.close()
    assert opened[0].closed


def test_import_sets_field_size_limit_only() -> None:
    assert csv.field_size_limit() == 10 * 1024 * 1024
