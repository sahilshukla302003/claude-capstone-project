# csv_summary

Streaming CSV summary report generator. Standard library only, Python 3.10+.

## Usage

```
python -m csv_summary <path-to-csv>
```

(With the source tree, run with `PYTHONPATH=src`.)

Output is plain text: `Rows: N`, then one block per column in file order.

| Type | Fields |
|---|---|
| numeric | Min, Max (source tokens), Mean (up to 4 decimals), Nulls |
| text | Unique, Nulls |
| date | Earliest, Latest (as written), Nulls |

An empty file or a header-only file prints `No data rows found` and exits 0.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (including no data rows) |
| 1 | Expected failure: one `error: ...` line on stderr, stdout empty |
| 2 | Usage error |
| 130 | Interrupted |

## Inference rules

- Null: empty or whitespace-only field.
- Numeric: every non-null value is a finite decimal (optional sign and exponent, ASCII digits). `nan`, `inf`, hex, `1_000` and overflowing values such as `1e999` make the column text. Leading zeros are numeric.
- Date: every non-null value is `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM[:SS[.ffffff]]` and a real calendar date and time.
- Text: everything else, including mixed columns. An all-null column is text with 0 unique values.

## Caveats

- Unique counts are exact up to a shared in-memory budget (48 MiB of sets). Beyond it, the largest columns switch to 128-bit digests (collision probability below 10^-21 at 10^8 values) and are still reported as exact. Writing temporary files is not allowed, so this is the trade-off for staying under 512 MB.
- Blank lines are skipped and are not counted as rows. A line such as `,,` is a row of nulls.
- Strict CSV quoting: a closing quote followed by other text (`"a"b`) is an error (exit 1).
- Numbers are held as floats; integers above 2**53 lose precision. A mean that overflows prints `inf` or `-inf`; very large means use exponent notation.
- No time zone support: values with `Z` or an offset make the column text.
- Non-regular files (pipes, devices, `/dev/stdin`) are rejected because the file is read twice.
- Lines are short for typical data; long names and tokens are not truncated. Control characters in names, paths and tokens are escaped.
- UTF-8 only (a BOM is tolerated), comma delimiter only.

## Tests

```
pytest                       # default suite (slow tests deselected)
pytest -m slow -s            # 100 MB files: AC-16, NFR-1, NFR-2 (mandatory in verification)
python scripts/verify.py     # full gate: coverage >= 90%, AC trace, slow suite must run
```
