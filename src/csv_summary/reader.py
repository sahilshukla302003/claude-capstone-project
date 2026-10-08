"""The only module that touches the file system and the ``csv`` module."""

from __future__ import annotations

import csv
import os
import stat
from collections.abc import Iterator

from .errors import CsvSummaryError, escape_control

# Set once at import (process-global, idempotent): an unterminated quote fails
# fast instead of buffering the whole file.
csv.field_size_limit(10 * 1024 * 1024)


def _check_path(path: str) -> None:
    shown = escape_control(path)
    if os.path.isdir(path):
        raise CsvSummaryError(f"cannot read {shown}: is a directory")
    try:
        mode = os.stat(path).st_mode
    except FileNotFoundError:
        raise CsvSummaryError(f"file not found: {shown}") from None
    except OSError as exc:
        raise CsvSummaryError(f"cannot read {shown}: {exc.strerror or exc}") from None
    if not stat.S_ISREG(mode):
        raise CsvSummaryError(f"cannot read {shown}: not a regular file")


def open_records(path: str) -> Iterator[list[str]]:
    """Yield the header, then each data record padded with "" to header width.

    Blank lines are skipped. Yields nothing for a 0-byte file. Raises
    CsvSummaryError for every expected failure. The file is closed when the
    generator is exhausted or closed.
    """
    _check_path(path)
    shown = escape_control(path)
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            yield from _read(csv.reader(handle, delimiter=",", strict=True), shown)
    except FileNotFoundError:
        raise CsvSummaryError(f"file not found: {shown}") from None
    except UnicodeDecodeError:
        raise CsvSummaryError(f"{shown}: invalid UTF-8 encoding") from None
    except OSError as exc:
        raise CsvSummaryError(f"cannot read {shown}: {exc.strerror or exc}") from None


def _read(reader: "csv._reader", shown: str) -> Iterator[list[str]]:
    width = -1
    try:
        for row in reader:
            if not row:
                continue
            if width < 0:
                width = len(row)
            elif len(row) > width:
                raise CsvSummaryError(
                    f"{shown}: line {reader.line_num}: "
                    f"row has {len(row)} fields but header has {width}"
                )
            elif len(row) < width:
                row = row + [""] * (width - len(row))
            yield row
    except csv.Error as exc:
        raise CsvSummaryError(f"{shown}: line {reader.line_num}: {exc}") from None
