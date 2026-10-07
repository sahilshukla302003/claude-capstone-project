import csv
import io
import sys

import pytest

from csv_summary import cli
from csv_summary.errors import CsvSummaryError


def test_success_returns_zero(capsys, fixture_path) -> None:
    assert cli.main([str(fixture_path("ac8_9.csv"))]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Rows: 4\n")


def test_no_data_message(capsys, fixture_path) -> None:
    assert cli.main([str(fixture_path("empty.csv"))]) == 0
    assert capsys.readouterr().out == "No data rows found\n"


@pytest.mark.parametrize("argv", [[], ["a", "b"]])
def test_usage_errors_exit_2_ac2(argv, capsys) -> None:
    with pytest.raises(SystemExit) as info:
        cli.main(argv)
    assert info.value.code == 2
    assert "usage: csv_summary" in capsys.readouterr().err


def test_csv_summary_error_mapped(capsys, tmp_path) -> None:
    assert cli.main([str(tmp_path / "missing.csv")]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: file not found: ")
    assert captured.err.count("\n") == 1


def test_custom_exit_code(monkeypatch, capsys) -> None:
    def boom(path):
        raise CsvSummaryError("bad", exit_code=3)

    monkeypatch.setattr(cli, "profile_file", boom)
    assert cli.main(["x"]) == 3
    assert capsys.readouterr().err == "error: bad\n"


def test_memory_error(monkeypatch, capsys) -> None:
    def boom(path):
        raise MemoryError

    monkeypatch.setattr(cli, "profile_file", boom)
    assert cli.main(["we\nird.csv"]) == 1
    assert capsys.readouterr().err == "error: out of memory while processing we\\nird.csv\n"


def test_keyboard_interrupt(monkeypatch, capsys) -> None:
    def boom(path):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "profile_file", boom)
    assert cli.main(["x"]) == 130
    assert capsys.readouterr().out == ""


class FailingStdout(io.StringIO):
    def __init__(self, exc: Exception) -> None:
        super().__init__()
        self.exc = exc

    def write(self, text: str) -> int:
        raise self.exc


@pytest.mark.parametrize("exc", [BrokenPipeError(), OSError(28, "No space left")])
def test_stdout_failures_return_1(monkeypatch, capsys, fixture_path, exc) -> None:
    monkeypatch.setattr(sys, "stdout", FailingStdout(exc))
    assert cli.main([str(fixture_path("ac8_9.csv"))]) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_stdout_without_reconfigure(monkeypatch, fixture_path) -> None:
    class Plain:
        def __init__(self) -> None:
            self.parts: list[str] = []

        def write(self, text: str) -> int:
            self.parts.append(text)
            return len(text)

        def flush(self) -> None:
            pass

    plain = Plain()
    monkeypatch.setattr(sys, "stdout", plain)
    assert cli.main([str(fixture_path("ac8_9.csv"))]) == 0
    assert "".join(plain.parts).startswith("Rows: 4")


def test_reconfigure_failure_is_ignored(monkeypatch, fixture_path) -> None:
    class Odd(io.StringIO):
        def reconfigure(self, **kwargs) -> None:
            raise ValueError("nope")

    out = Odd()
    monkeypatch.setattr(sys, "stdout", out)
    assert cli.main([str(fixture_path("ac8_9.csv"))]) == 0
    assert out.getvalue().startswith("Rows: 4")


def test_main_twice_keeps_field_size_limit(capsys, fixture_path) -> None:
    cli.main([str(fixture_path("ac8_9.csv"))])
    cli.main([str(fixture_path("ac8_9.csv"))])
    assert csv.field_size_limit() == 10 * 1024 * 1024
    assert capsys.readouterr().out.count("Rows: 4") == 2
