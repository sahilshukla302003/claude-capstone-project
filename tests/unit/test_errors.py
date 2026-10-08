import pytest

from csv_summary.errors import CsvSummaryError, escape_control


def test_str_is_message_and_default_exit_code() -> None:
    err = CsvSummaryError("boom")
    assert str(err) == "boom"
    assert err.message == "boom"
    assert err.exit_code == 1


def test_custom_exit_code() -> None:
    assert CsvSummaryError("x", exit_code=7).exit_code == 7


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a\nb", "a\\nb"),
        ("a\rb", "a\\rb"),
        ("a\tb", "a\\tb"),
        ("\x1b[31m", "\\x1b[31m"),
        ("a\x00b", "a\\x00b"),
        ("a\x7fb", "a\\x7fb"),
        ("café", "café"),
        ("plain text", "plain text"),
    ],
)
def test_escape_control(raw: str, expected: str) -> None:
    assert escape_control(raw) == expected
