"""Argument handling, the error boundary and exit codes."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from .errors import CsvSummaryError, escape_control
from .profiler import profile_file
from .report import render_report


def _configure_stdout() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        pass


def _error(message: str) -> None:
    try:
        sys.stderr.write(f"error: {message}\n")
    except OSError:
        pass


def _silence_stdout() -> None:
    """After a broken pipe, avoid the interpreter's shutdown message."""
    try:
        fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(fd, sys.stdout.fileno())
    except (OSError, ValueError):
        pass


def _write_stdout(text: str) -> int:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        _silence_stdout()
        return 1
    except OSError as exc:
        _error(f"cannot write output: {exc.strerror or exc}")
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="csv_summary", description="Print a summary report for a CSV file."
    )
    parser.add_argument("path", help="path to a UTF-8, comma-delimited CSV file")
    args = parser.parse_args(argv)
    _configure_stdout()
    try:
        text = render_report(profile_file(args.path))
    except CsvSummaryError as exc:
        _error(exc.message)
        return exc.exit_code
    except MemoryError:
        _error(f"out of memory while processing {escape_control(args.path)}")
        return 1
    except KeyboardInterrupt:
        return 130
    return _write_stdout(text)
