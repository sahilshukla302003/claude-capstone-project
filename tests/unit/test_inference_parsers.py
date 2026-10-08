import pytest

from csv_summary.inference import is_null, parse_date, parse_number


@pytest.mark.parametrize("token", ["1", "-1.5", "+.5", "1e3", "007", "1.", "2E-3"])
def test_numbers_accepted(token: str) -> None:
    assert parse_number(token) == float(token)


@pytest.mark.parametrize(
    "token",
    ["nan", "inf", "-inf", "0x10", "1_000", "1e999", "", "abc", "1,5",
     "١٢", "1 2", "--1", "."],
)
def test_numbers_rejected(token: str) -> None:
    assert parse_number(token) is None


@pytest.mark.parametrize(
    "token",
    ["2024-02-29", "2024-01-15T10:30", "2024-01-15T10:30:00",
     "2024-01-15T10:30:00.123456", "2000-12-31"],
)
def test_dates_accepted(token: str) -> None:
    assert parse_date(token) is not None


@pytest.mark.parametrize(
    "token",
    ["2023-02-29", "2024-02-30", "2024-01-15T25:00", "2024-01-15T10:30:00Z",
     "2024-01-15T10:30:00+05:00", "20240115", "2024-1-5", "0000-01-01",
     "2024-01-15T10", "2024-01-15 10:30", "2024-01-15T10:30:00.1234567",
     "٢٠٢٤-01-15"],
)
def test_dates_rejected(token: str) -> None:
    assert parse_date(token) is None


def test_date_keys() -> None:
    assert parse_date("2024-01-15") == (2024, 1, 15, 0, 0, 0, 0)
    assert parse_date("2024-01-15T00:00:00") == parse_date("2024-01-15")
    assert parse_date("2024-01-15T10:30:05.5") == (2024, 1, 15, 10, 30, 5, 500000)
    assert parse_date("2024-01-15T10:30:00.000001") > parse_date("2024-01-15T10:30")


def test_is_null() -> None:
    assert is_null("") and is_null("  \t") and not is_null(" a ")
