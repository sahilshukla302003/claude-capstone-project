"""Subprocess tests; each test name or docstring carries its AC id."""

import os
import subprocess
import sys

import pytest

from tests.conftest import ROOT, run_cli


def assert_no_traceback(err: bytes) -> None:
    assert b"Traceback" not in err


def test_ac1_success(fixture_path) -> None:
    """AC-1: row count, names and types, exit 0."""
    rc, out, err = run_cli(str(fixture_path("typical.csv")))
    text = out.decode()
    assert rc == 0 and err == b""
    assert "Rows: 10" in text
    for name, kind in [("id", "numeric"), ("name", "text"), ("joined", "date")]:
        assert f": {name}\n  Type: {kind}\n" in text.replace("\r\n", "\n")


def test_ac2_usage_error() -> None:
    """AC-2: no argument gives usage on stderr and a non-zero exit."""
    rc, out, err = run_cli()
    assert rc == 2 and out == b"" and b"usage:" in err


def test_ac2_extra_argument() -> None:
    """AC-2: extra arguments are rejected."""
    rc, _, err = run_cli("a.csv", "b.csv")
    assert rc == 2 and b"usage:" in err


def test_ac3_not_found(tmp_path) -> None:
    """AC-3: missing file, path in stderr, empty stdout, exit 1."""
    missing = str(tmp_path / "missing.csv")
    rc, out, err = run_cli(missing)
    assert rc == 1 and out == b"" and b"missing.csv" in err
    assert_no_traceback(err)


def test_ac4_directory(tmp_path) -> None:
    """AC-4: a directory is a one-line error without traceback."""
    rc, out, err = run_cli(str(tmp_path))
    assert rc == 1 and out == b"" and b"is a directory" in err
    assert err.count(b"\n") == 1
    assert_no_traceback(err)


def test_ac5_header_only(fixture_path) -> None:
    """AC-5: header-only prints No data rows found."""
    rc, out, _ = run_cli(str(fixture_path("header_only.csv")))
    assert rc == 0 and out.strip() == b"No data rows found"


def test_ac6_empty_file(fixture_path) -> None:
    """AC-6: a 0-byte file prints No data rows found."""
    rc, out, _ = run_cli(str(fixture_path("empty.csv")))
    assert rc == 0 and out.strip() == b"No data rows found"


def test_ac7_row_count(write_csv) -> None:
    """AC-7: header plus 5 rows reports 5."""
    rc, out, _ = run_cli(str(write_csv("a\n1\n2\n3\n4\n5\n")))
    assert rc == 0 and b"Rows: 5" in out


def test_ac8_ac9_numeric_and_text(fixture_path) -> None:
    """AC-8 and AC-9: numeric stats and text unique counts."""
    rc, out, _ = run_cli(str(fixture_path("ac8_9.csv")))
    text = out.decode().replace("\r\n", "\n")
    assert rc == 0
    assert "Min: 1\n  Max: 3\n  Mean: 2\n  Nulls: 1" in text
    assert "Type: text\n  Unique: 2\n  Nulls: 1" in text


def test_ac10_dates(write_csv) -> None:
    """AC-10: earliest, latest and null count."""
    data = "d,k\n2024-01-15,a\n2023-06-01,a\n2024-12-31,a\n,a\n"
    rc, out, _ = run_cli(str(write_csv(data)))
    text = out.decode().replace("\r\n", "\n")
    assert rc == 0
    assert "Earliest: 2023-06-01\n  Latest: 2024-12-31\n  Nulls: 1" in text


def test_ac11_mixed_is_text(fixture_path) -> None:
    """AC-11: 1, 2, abc is text."""
    _, out, _ = run_cli(str(fixture_path("mixed.csv")))
    assert b"Type: text" in out


def test_ac12_whitespace_null(fixture_path) -> None:
    """AC-12: whitespace-only field is null in a numeric column."""
    _, out, _ = run_cli(str(fixture_path("numeric_ws.csv")))
    assert b"Type: numeric" in out and b"Nulls: 1" in out


def test_ac13_all_null(fixture_path) -> None:
    """AC-13: all-empty column is text, unique 0, nulls 4."""
    _, out, _ = run_cli(str(fixture_path("all_null.csv")))
    text = out.decode().replace("\r\n", "\n")
    assert text.count("Type: text\n  Unique: 0\n  Nulls: 4") == 2


def test_ac14_quoted_fields(fixture_path) -> None:
    """AC-14: quoted comma and embedded newline keep the row count at 2."""
    rc, out, _ = run_cli(str(fixture_path("quoted.csv")))
    assert rc == 0 and b"Rows: 2" in out


def test_ac15_short_row_padded(fixture_path) -> None:
    """AC-15: a short row yields nulls."""
    rc, out, _ = run_cli(str(fixture_path("short_rows.csv")))
    assert rc == 0 and b"Rows: 2" in out


def test_ac15_wide_row_error(fixture_path) -> None:
    """AC-15: a wide row is an error, exit 1, empty stdout."""
    rc, out, err = run_cli(str(fixture_path("wide_row.csv")))
    assert rc == 1 and out == b"" and b"row has 3 fields but header has 2" in err
    assert_no_traceback(err)


def test_ac17_invalid_utf8(fixture_path) -> None:
    """AC-17: invalid UTF-8 gives a one-line error."""
    rc, out, err = run_cli(str(fixture_path("invalid_utf8.csv")))
    assert rc == 1 and out == b"" and err.count(b"\n") == 1
    assert b"invalid UTF-8" in err
    assert_no_traceback(err)


def test_strict_quote_error(fixture_path) -> None:
    """D15: a closing quote followed by text is an error with a line number."""
    rc, _, err = run_cli(str(fixture_path("bad_quote.csv")))
    assert rc == 1 and b"line 2" in err


def test_blank_lines_not_counted_single_column(fixture_path) -> None:
    """D14: blank lines in a single-column file are not rows."""
    rc, out, _ = run_cli(str(fixture_path("blank_lines.csv")))
    assert rc == 0 and b"Rows: 2" in out


def test_bom_tolerated(fixture_path) -> None:
    """A UTF-8 BOM is not part of the first column name."""
    _, out, _ = run_cli(str(fixture_path("bom.csv")))
    assert b"Column 1: a\n" in out.replace(b"\r\n", b"\n")


def test_ac18_deterministic(fixture_path) -> None:
    """AC-18: two runs give identical bytes."""
    path = str(fixture_path("typical.csv"))
    assert run_cli(path)[1] == run_cli(path)[1]


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX FIFO semantics")
def test_non_regular_file(tmp_path) -> None:
    """D5: FIFOs are rejected."""
    fifo = tmp_path / "p"
    os.mkfifo(fifo)
    rc, out, err = run_cli(str(fifo))
    assert rc == 1 and b"not a regular file" in err and out == b""


@pytest.mark.skipif(sys.platform == "win32", reason="chmod cannot deny reads on Windows")
def test_permission_denied(write_csv) -> None:
    """AC-4 variant: unreadable file."""
    path = write_csv("a\n1\n")
    path.chmod(0)
    if os.access(path, os.R_OK):
        pytest.skip("running as a user that bypasses permissions")
    rc, _, err = run_cli(str(path))
    assert rc == 1 and b"error:" in err


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX pipe semantics")
def test_broken_pipe(fixture_path) -> None:
    """D11: closed stdout gives no traceback."""
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.run(
        f'"{sys.executable}" -m csv_summary "{fixture_path("typical.csv")}" | head -c 0',
        shell=True, capture_output=True, env=env, cwd=str(ROOT), check=False)
    assert b"Traceback" not in proc.stderr
