"""Plain-text report formatting (pure, deterministic, no I/O).

Lines are short for typical data; long names and tokens are not truncated.
"""

from __future__ import annotations

from math import isfinite

from .errors import escape_control
from .models import ColumnSummary, ColumnType, Summary

NO_DATA_MESSAGE = "No data rows found"


def format_mean(value: float) -> str:
    """At most 4 decimals, trailing zeros trimmed; huge values use exponent form."""
    if value != value:
        return "nan"
    if not isfinite(value):
        return "inf" if value > 0 else "-inf"
    if abs(value) >= 1e15:
        mantissa, exponent = format(value, ".4e").split("e")
        if "." in mantissa:
            mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{exponent}"
    text = format(value, ".4f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _block(number: int, col: ColumnSummary) -> list[str]:
    lines = [f"Column {number}: {escape_control(col.name)}", f"  Type: {col.type.value}"]
    if col.type is ColumnType.NUMERIC:
        mean = col.mean if col.mean is not None else 0.0
        lines += [
            f"  Min: {escape_control(col.min or '')}",
            f"  Max: {escape_control(col.max or '')}",
            f"  Mean: {format_mean(mean)}",
        ]
    elif col.type is ColumnType.DATE:
        lines += [
            f"  Earliest: {escape_control(col.min or '')}",
            f"  Latest: {escape_control(col.max or '')}",
        ]
    else:
        lines.append(f"  Unique: {col.unique_count or 0}")
    lines.append(f"  Nulls: {col.null_count}")
    return lines


def render_report(summary: Summary | None) -> str:
    """Render the summary; the result always ends with a newline."""
    if summary is None:
        return NO_DATA_MESSAGE + "\n"
    lines = [f"Rows: {summary.row_count}"]
    for number, col in enumerate(summary.columns, start=1):
        lines.append("")
        lines.extend(_block(number, col))
    return "\n".join(lines) + "\n"
