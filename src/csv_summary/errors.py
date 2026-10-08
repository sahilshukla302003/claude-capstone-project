"""Exception type for expected failures and a shared sanitising helper."""

from __future__ import annotations


class CsvSummaryError(Exception):
    """An expected, user-facing failure (reported as one line, no traceback)."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def escape_control(text: str) -> str:
    """Escape control and other non-printable characters (repr style, no quotes).

    Printable characters, including non-ASCII ones such as ``e`` with acute,
    are left unchanged.
    """
    if text.isprintable():
        return text
    return "".join(
        ch if ch.isprintable() else ch.encode("unicode_escape").decode("ascii")
        for ch in text
    )
