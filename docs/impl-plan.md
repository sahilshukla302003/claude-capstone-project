# Implementation Plan: CSV Summary Report Generator

Inputs: `docs/architecture.md`, `docs/design-review.md` (no blockers; the four Major and all Minor findings are carried into the tasks below). Requirement IDs refer to `docs/requirements.md`. Complexity: S (under 2 h), M (2-4 h), L (4-8 h, at most one day). No task exceeds one day.

## 1. Planning Decisions (resolve under-specified design points)

These come from the design review recommendations and are binding on the implementation tasks.

| # | Decision | Source finding |
|---|---|---|
| D1 | `UniqueBudget` defaults: `exact_limit_bytes = 48 MiB` (down from 96 MiB). Tier 1 charge per new entry is `sys.getsizeof(value) + 100` (realistic set-slot, resize and fragmentation overhead). Both limits stay constructor-injectable. The final defaults are confirmed or tuned in T16 from the measured peak. | Major: memory margin |
| D2 | Eviction loops: while the shared exact total exceeds the limit, convert the column with the largest exact total, crediting its charge, until under budget. | Minor: eviction policy |
| D3 | `pending_limit` is global (all hashed columns together). Compaction triggers when total pending exceeds `max(pending_limit, 25% of compacted entries)`. | Minor: eviction policy |
| D4 | `UniqueCounter.count(i)` is idempotent. `add` after any `count` call raises `RuntimeError` (programmer error, documented). | Minor: eviction policy |
| D5 | Non-regular files (FIFO, `/dev/stdin`, device, anything where `stat.S_ISREG` is false) are rejected in `reader.open_records` with `error: cannot read <path>: not a regular file`. The check runs after the `isdir` check and before the content is read. | Major: non-regular files |
| D6 | Pass 2 counts the records it reads. If the count differs from pass 1 `row_count`, the profiler raises `CsvSummaryError("<path>: file changed while being read")`. | Major: non-regular files |
| D7 | `ColumnAccumulator.observe` fast path: try `float(token)` first. Only on success run the numeric regex (to exclude `nan`, `inf`, `_`, hex and non-ASCII digits) and the finiteness check. Per-column state is cached in local variables inside the hot loop. | Major: time budget |
| D8 | `profiler` fills `unique_count` with `dataclasses.replace(col_summary, unique_count=n)`. | Minor: finish/replace |
| D9 | Mean overflow: if the running sum becomes non-finite, `finish` returns `mean = inf` or `-inf` (by sign of overflow) or `nan` if undefined, and never raises. `format_mean` prints `inf`, `-inf`, `nan` literally. For finite values with `abs(x) >= 1e15` it prints exponent notation (`format(x, ".4e")` with mantissa zeros trimmed), so no line exceeds a few dozen characters. | Minor: overflow |
| D10 | The 80-column claim is reworded in docs and docstrings to "short lines for typical data; long names and tokens are not truncated". No truncation logic. | Minor: 80 columns |
| D11 | `main` guards `sys.stdout.reconfigure` with `hasattr`, wraps it in a try, and catches `BrokenPipeError` and `OSError` around the single stdout write (return 1, no traceback; for `BrokenPipeError` also redirect stdout to devnull to avoid the interpreter's shutdown message). | Minor: stdout failures |
| D12 | One shared `escape_control(text: str) -> str` helper (repr-style escapes for control characters, no surrounding quotes) lives in `errors.py` so `reader`, `profiler`, `cli` and `report` use it without import cycles. It is applied to column names, to the path in every error message, and to min/max/earliest/latest tokens. | Minor: sanitization |
| D13 | `csv.field_size_limit(10 * 1024 * 1024)` is set once at module import in `reader.py` (idempotent, not inside `open_records`). | Minor: global state |
| D14 | Blank lines are skipped (not counted as rows) and this is covered by an explicit test and a user-documentation note. Section 8 Q1 (hashed counts reported as exact above the exact-set budget) is surfaced in the final docs (README caveat) and flagged to the user at approval. | Minor: blank lines, hashed counts |
| D15 | `"a"b` (strict-mode `csv.Error`) stays an error with exit 1. The message keeps the path and line number and is covered by a test. | Minor: strict mode |
| D16 | `tests/helpers/` is part of the layout: `tests/helpers/__init__.py`, `gen_large_csv.py`, `run_with_peak.py`, `bench_inference.py`. | Minor: helper location |
| D17 | `pytest -m slow` is a mandatory part of Verification, enforced by T17 (a verification script and a traceability check that fails if AC-16 did not run). | Major: slow test |

## 2. Target Layout

```
pyproject.toml                       (pytest config, markers, dev extras; no runtime deps)
src/csv_summary/
    __init__.py  __main__.py  cli.py  errors.py  models.py
    reader.py  inference.py  uniques.py  profiler.py  report.py
tests/
    conftest.py
    unit/        test_errors.py test_models.py test_reader.py test_inference_parsers.py
                 test_accumulator.py test_uniques.py test_profiler.py test_report.py test_cli.py
    integration/ test_cli_end_to_end.py test_large_file.py
    fixtures/    small hand-written CSVs (see T13)
    helpers/     __init__.py gen_large_csv.py run_with_peak.py bench_inference.py
scripts/verify.py                    (T17; runs default suite then `pytest -m slow`, checks AC traceability)
src/csv_summary/README.md            (T18; usage and caveats; root README.md documents the pipeline and is not touched)
```

## 3. Task Table

| ID | Task Name | Description | Depends On | Complexity | File(s) Affected |
|---|---|---|---|---|---|
| T1 | Project scaffold | Create `pyproject.toml` (Python >= 3.10, no runtime deps, dev extras `pytest>=7.0`, `pytest-cov>=4.0`; `pythonpath = ["src"]`; register the `slow` marker; default `addopts = -m "not slow"`). Create empty package `src/csv_summary/__init__.py` (version string only), `tests/conftest.py`, `tests/helpers/__init__.py`, and the `tests/unit`, `tests/integration`, `tests/fixtures` directories. DoD: `pytest` collects zero errors; `python -c "import csv_summary"` works with `PYTHONPATH=src`; `pytest --markers` lists `slow`. | none | S | `pyproject.toml`, `src/csv_summary/__init__.py`, `tests/conftest.py`, `tests/helpers/__init__.py` |
| T2 | `errors.py` | `CsvSummaryError(message, exit_code=1)` with `.message` and `.exit_code`, plus `escape_control` (D12). DoD: exception str equals message; default exit code 1; custom code honoured; `escape_control` escapes `\n`, `\r`, `\t`, `\x1b`, `\x00`, DEL and leaves printable non-ASCII (e.g. `é`) unchanged. | T1 | S | `src/csv_summary/errors.py` |
| T2-test | Tests for `errors.py` | Unit tests for the DoD of T2 incl. escape table. | T2 | S | `tests/unit/test_errors.py` |
| T3 | `models.py` | `ColumnType(str, Enum)`, frozen `ColumnSummary`, frozen `Summary` exactly as in architecture 3.2. No logic. DoD: instances are immutable (assigning raises `FrozenInstanceError`); `dataclasses.replace` works; enum values are `"numeric"`, `"text"`, `"date"`. | T1 | S | `src/csv_summary/models.py` |
| T3-test | Tests for `models.py` | Immutability, defaults (`None` stats), `replace` usage (D8), enum string values. | T3 | S | `tests/unit/test_models.py` |
| T4 | `reader.py` | `open_records(path)` generator per architecture 3.3: `isdir` check, then regular-file check (D5), `open(..., "r", encoding="utf-8-sig", newline="")`, `csv.reader(strict=True)`, field-size limit set once at import (D13), header then padded records, blank lines skipped (D14), wide row error, `UnicodeDecodeError`, `csv.Error`, `OSError`, `FileNotFoundError` mapped to the architecture 4.3 messages with `escape_control(path)` (D12) and 1-based line number. File closed on exhaustion or `.close()`. DoD: all messages match the 4.3 table; 0-byte file yields nothing; a FIFO or `/dev/stdin` style path yields `not a regular file` (POSIX; skipped on Windows). | T2 | M | `src/csv_summary/reader.py` |
| T4-test | Tests for `reader.py` | Cases: padded short rows (AC-15), wide row error with line number, blank-line skipping including before the header and in a single-column file (D14), BOM, quoted `"a,b"`, embedded newline (AC-14), invalid UTF-8 (AC-17), directory, missing path, `"a"b` strict error (D15), unterminated quote hits the field-size limit quickly, path with control characters is escaped in the message, non-regular file rejected (`os.mkfifo`, `skipif` on Windows), generator closes the file handle, import has no side effect other than the field-size limit. | T4 | M | `tests/unit/test_reader.py`, `tests/fixtures/*.csv` (as needed) |
| T5 | Parsers in `inference.py` | `is_null`, `parse_number`, `parse_date` with compiled ASCII regexes and a `float()` fast path (D7): `float()` in try/except first, regex and finiteness check only on success. `parse_date` uses the date regex then `datetime.date`/`datetime.time` validation, returns the sort key tuple `(y, m, d, H, M, S, us)`. DoD: behaviour table in the test task passes; no use of `fromisoformat`. | T1 | M | `src/csv_summary/inference.py` |
| T5-test | Tests for parsers | Table-driven: numbers `1`, `-1.5`, `+.5`, `1e3`, `007` accepted; `nan`, `inf`, `-inf`, `0x10`, `1_000`, `1e999`, `""`, `" "` (after strip), Arabic-Indic digits rejected. Dates `2024-02-29` ok; `2023-02-29`, `2024-02-30`, `2024-01-15T25:00`, `...Z`, `+05:00` offset, `20240115` rejected; `T10:30`, `T10:30:00`, `T10:30:00.123456` accepted; date-only equals midnight in the key. `is_null` for whitespace-only. | T5 | M | `tests/unit/test_inference_parsers.py` |
| T6 | `ColumnAccumulator` | `observe`, `finish`, `needs_unique_pass` per 3.4: independent numeric/date candidacy, demoted-column null-only fast path, min/max with source token (first occurrence wins ties), Neumaier sum, date min/max keys and tokens, type decision order, mean overflow rule (D9), token tracking returns stripped tokens. DoD: AC-8, AC-10..AC-13 behaviours hold; `finish` never raises on overflowing sums. | T3, T5 | L | `src/csv_summary/inference.py` |
| T6-test | Tests for accumulator | Mixed values demote to text (AC-11), whitespace-only cells are nulls (AC-12), all-null column is text with 0 non-null (AC-13), tie handling (`1` then `1.0` keeps `1`), min/max source token for `1e3`, negative and leading-zero values, Neumaier accuracy (for example 1e6 copies of `0.1`, and a cancellation case), date min/max incl. mixed date-only and datetime, `[1e308, 1e308]` gives `inf` mean without exception and `[1e308, -1e308]` is finite (D9), `needs_unique_pass` truth table. | T6 | M | `tests/unit/test_accumulator.py` |
| T7 | Early performance benchmark | Standalone script that feeds N (default 3 M) synthetic cells through `ColumnAccumulator.observe` for numeric, date, text and mixed columns and prints microseconds per cell for each. Run it once the accumulator exists and record the numbers in a comment block in the script header and in the T16 report. DoD: script runs on Windows and POSIX; numeric cell cost and date cell cost are reported separately; if numeric cost exceeds about 4 us/cell, optimise `observe` (local-variable caching, fewer attribute lookups) before continuing to T11. This is the "benchmark early" check from the review. | T6 | S | `tests/helpers/bench_inference.py` |
| T8 | `uniques.py` Tier 1 and budget | `UniqueBudget` (defaults per D1) and `UniqueCounter.add/count/is_hashed` with the exact-set tier, charge `getsizeof + 100` per new unique entry (duplicate adds charge nothing), per-column accounting, D4 semantics. No eviction yet (the limit check calls a stub that T9 completes). DoD: counts exact for low-cardinality columns across multiple columns; `is_hashed` false. | T1 | M | `src/csv_summary/uniques.py` |
| T8-test | Tests for Tier 1 | Counts equal `len(set(values))`; duplicates; empty string and whitespace-padded values are distinct (assumption Q3); `add` after `count` raises `RuntimeError`; `count` twice returns the same value (D4); charge accounting verified through a tiny injected budget. | T8 | S | `tests/unit/test_uniques.py` |
| T9 | `uniques.py` Tier 2 hashed store | Eviction loop (D2), conversion of the largest column to 256-bucket `array("Q")` hi/lo storage using `blake2b(digest_size=16)`, credit of the exact charge, global pending counter and compaction rule (D3), compaction one bucket at a time, `count()` compacts and sums bucket sizes, `is_hashed`. DoD: results equal the `len(set())` oracle after forced conversions. | T8 | L | `src/csv_summary/uniques.py` |
| T9-test | Tests for Tier 2 | With tiny injected budgets: conversion flips `is_hashed`; multiple compactions (low `pending_limit`); multiple columns with forced eviction of the largest first and repeated eviction until under budget (D2); duplicates before and after conversion; random data with many duplicates equals oracle; same input gives the same count across two runs in separate processes (determinism, NFR-4); credit after conversion lets other columns stay exact. | T9 | M | `tests/unit/test_uniques.py` |
| T10 | `profiler.py` | `profile_file(path, *, budget=None)` per 4.1: pass 1 over `open_records`, header-only and 0-byte give `None`, `finish` per column, pass 2 only for `needs_unique_pass` columns and non-null values, skip pass 2 entirely when none, all-null text column gets 0 without pass 2, `dataclasses.replace` (D8), pass-2 record count compared to `row_count` with `CsvSummaryError` on mismatch (D6). DoD: returns a correct `Summary` for all AC data shapes; the reader is opened exactly once when no text column has data. | T4, T6, T9 | M | `src/csv_summary/profiler.py` |
| T10-test | Tests for profiler | Header-only and empty file give `None` (AC-5); numeric/date-only file opens the reader once (monkeypatch counter); text unique counts exact (AC-9) incl. with a tiny injected budget forcing Tier 2; mixed column demoted to text gets uniques from pass 2; all-null column unique 0 (FR-17); pass-2 mismatch: monkeypatch `open_records` so the second call yields fewer rows and assert `CsvSummaryError`; errors from the reader propagate. | T10 | M | `tests/unit/test_profiler.py` |
| T11 | `report.py` | `NO_DATA_MESSAGE`, `render_report`, `format_mean` per 3.7 with D9 (non-finite literals, exponent notation for very large magnitudes, `-0` to `0`, up to 4 decimals trimmed, `format(x, ".4f")` never `repr`), `escape_control` on names and tokens (D12), output ends with `\n`, docstrings use D10 wording. DoD: golden outputs for every column type match the architecture layout. | T3, T2 | M | `src/csv_summary/report.py` |
| T11-test | Tests for report | Golden strings for numeric, text and date blocks; `Rows:` line; `No data rows found`; `format_mean` table (`2.0` to `2`, `0.12345` to `0.1235`, `-0.00001` to `0`, `1e300` short exponent output, `inf`, `-inf`, `nan`); control characters in column names and tokens escaped; empty and duplicate names printed per Q6; long name not truncated and block still single-line per field; two renders of one `Summary` are byte-identical. | T11 | M | `tests/unit/test_report.py` |
| T12 | `cli.py` and `__main__.py` | `main(argv)` with `argparse(prog="csv_summary")` (exit 2 on usage error), guarded `stdout.reconfigure` (D11), error boundary for `CsvSummaryError`, `MemoryError`, `KeyboardInterrupt` (130), single stdout write guarded for `BrokenPipeError`/`OSError` (D11), path escaped in the out-of-memory message, `__main__.py` as in 3.8. DoD: `python -m csv_summary file.csv` works; failures leave stdout empty with one stderr line and no traceback. | T10, T11 | M | `src/csv_summary/cli.py`, `src/csv_summary/__main__.py` |
| T12-test | Unit tests for `cli.main` | In-process via `capsys` or injected streams: success returns 0; missing and extra args raise `SystemExit(2)` with usage (AC-2); `CsvSummaryError` returns its exit code and prints `error: ...`; monkeypatched `MemoryError` returns 1 with the memory message; `KeyboardInterrupt` returns 130; `BrokenPipeError` and `OSError` on write return 1 without traceback; `main` works when stdout lacks `reconfigure` or when pytest capture replaces it (D11); calling `main` twice in one process does not break the csv field-size limit (D13). | T12 | M | `tests/unit/test_cli.py` |
| T13 | Fixtures and test data builders | Small fixture CSVs and shared `conftest.py` helpers (write-text-to-`tmp_path`, `run_cli(path)` subprocess wrapper with `PYTHONPATH=src`). Fixtures: typical mixed file, empty, header-only, BOM, quoted/embedded newline, short/wide rows, invalid UTF-8 bytes, all-null column, mixed numeric/text column, date column, blank lines. DoD: each fixture is referenced by at least one test; `run_cli` returns `(returncode, stdout, stderr)`. | T1 | S | `tests/fixtures/*.csv`, `tests/conftest.py` |
| T14 | Integration tests | Subprocess tests for AC-1..AC-15, AC-17, AC-18 asserting stdout, stderr (no `Traceback`) and return code: success, usage exit 2, not found, directory, invalid UTF-8, wide row, `"a"b`, empty and header-only (`No data rows found`, exit 0), non-regular file (POSIX only, `skipif` Windows), permission denied (skipped where it cannot be simulated), blank lines in a single-column file counted as not rows (D14), run twice and compare bytes (AC-18), `python -m csv_summary file | head -0` style broken pipe on POSIX. Each test name or docstring contains its AC id. | T12, T13 | L | `tests/integration/test_cli_end_to_end.py` |
| T15 | Large-file helpers | `gen_large_csv.py`: streaming generator (never holds the file in memory) for about 100 MB with a numeric, a date, a low-cardinality text and an all-distinct text column; variant B with several high-cardinality text columns (about 20 M distinct values total); returns the expected unique counts. `run_with_peak.py`: subprocess wrapper that calls `main()` and prints peak memory on stderr as a single parseable line (`ru_maxrss` on POSIX normalised KiB/bytes; `ctypes` `GetProcessMemoryInfo` `PeakWorkingSetSize` on Windows). DoD: both tools run standalone on a 1 MB sample; peak line parses on the current OS. | T12 | M | `tests/helpers/gen_large_csv.py`, `tests/helpers/run_with_peak.py` |
| T15-test | Tests for helpers | Fast unit-level checks (marker-free): generator output size, row count and expected unique counts on a few thousand rows; peak wrapper prints a parseable positive number and passes through the child exit code. | T15 | S | `tests/unit/test_helpers.py` |
| T16 | Large-file test and memory tuning | `@pytest.mark.slow` tests for AC-16/NFR-1/NFR-2: variant A (all-distinct single column) and variant B (multi-column high cardinality, mandatory per review) each assert exit 0, peak <= 512 MB, wall time <= 120 s, exact expected unique counts. The measured peak and wall time for both variants and for the T7 benchmark are written to the test output (and later copied into the verification report). If variant B peak exceeds 400 MB, tune `exact_limit_bytes`/`pending_limit` defaults (D1) or the per-entry charge, keeping them injectable; do not change the design. DoD: both variants pass on the dev OS and the final default budget values are recorded in the `UniqueBudget` docstring. | T14, T15 | L | `tests/integration/test_large_file.py`, `src/csv_summary/uniques.py` (defaults only, if tuning is needed) |
| T17 | Verification script and traceability gate | `scripts/verify.py`: runs the default suite with coverage (`--cov=csv_summary`, fail under 90), then runs `pytest -m slow` as a separate mandatory step and fails if zero slow tests were executed or any was skipped (D17). Includes an AC traceability check that every AC-1..AC-18 id appears in a test name or docstring, and that AC-16 specifically ran in the slow step (parsed from the junit or `-rA` output). Writes nothing outside `output/`. DoD: script exits non-zero when the slow step is deselected, and zero on a full pass. | T14, T16 | M | `scripts/verify.py` |
| T17-test | Test for the gate | Tests that call the verify helper functions with synthetic pytest result data: missing AC id fails; skipped slow test fails; AC-16 absent fails; all present passes. | T17 | S | `tests/unit/test_verify_script.py` |
| T18 | User docs and caveats | `src/csv_summary/README.md` with usage, exit codes, supported inference rules, and the documented caveats: hashed unique counts above the exact-set budget (collision probability below 10^-21, Q1), blank lines skipped (D14), strict CSV quoting (D15), float precision above 2**53 (Q5), no time-zone support, non-regular files rejected, `pytest -m slow` required for AC-16 (D17). | T16 | S | `src/csv_summary/README.md` |

## 4. Dependency Graph

```
T1 ──┬─> T2 ──┬─> T4 ──────────────┐
     │        │                    │
     │        └─────────────┐      │
     ├─> T3 ──┬─────────────┼──┐   │
     │        │             │  │   │
     ├─> T5 ──┴─> T6 ─> T7  │  │   │
     │            │         │  │   │
     │            │         v  v   v
     ├─> T8 ─> T9 ┼───────> T10 (needs T4, T6, T9)
     │            │           │
     │            │           v
     │            └──> T11 (needs T2, T3) ─> T12 (needs T10, T11)
     │                                          │
     └─> T13 ───────────────────────────────────┤
                                                v
                              T14 (T12, T13)   T15 (T12)
                                   │              │
                                   └──────┬───────┘
                                          v
                                         T16 ─> T17 ─> T17-test
                                          │
                                          └──> T18
```

Edge list (authoritative, topological order): T1; T2, T3, T5, T8, T13 (all after T1); T4 (T2); T6 (T3, T5); T7 (T6); T9 (T8); T11 (T2, T3); T10 (T4, T6, T9); T12 (T10, T11); T14 (T12, T13); T15 (T12); T16 (T14, T15); T17 (T14, T16); T18 (T16). Each `-test` task depends only on its implementation task and is delivered in the same sitting; T-test tasks for T4, T5, T6, T8, T9, T10, T11 must pass before any downstream task starts. No cycles. T2, T3, T5, T8 and T13 can run in parallel after T1.

Suggested sequence: T1, T2/T2-test, T3/T3-test, T4/T4-test, T5/T5-test, T6/T6-test, T7 (benchmark gate), T8/T8-test, T9/T9-test, T10/T10-test, T11/T11-test, T12/T12-test, T13, T14, T15/T15-test, T16, T17/T17-test, T18.

## 5. Architecture Coverage

| Component | Task(s) |
|---|---|
| `errors.py` | T2 |
| `models.py` | T3 |
| `reader.py` | T4 |
| `inference.py` | T5, T6, T7 |
| `uniques.py` | T8, T9, T16 (tuning) |
| `profiler.py` | T10 |
| `report.py` | T11 |
| `cli.py`, `__main__.py` | T12 |
| `tests/helpers/` | T7, T15, T13 (`run_cli` in conftest) |
| Packaging, test config | T1 |
| Verification gate, docs | T17, T18 |

## 6. Design-Review Findings Traceability

| Finding | Severity | Where carried |
|---|---|---|
| Memory estimate understates peak | Major | D1; T8 (charge), T9 (eviction), T16 (variant B peak measured, defaults tuned and recorded), T17 (peak recorded in verification) |
| Time budget optimistic | Major | D7; T5 (fast path), T6 (local caching), T7 (early benchmark gate), T16 (wall-time assert) |
| Non-regular files and file changed between passes | Major | D5, D6; T4 + T4-test (FIFO rejected), T10 + T10-test (pass-2 count mismatch), T14 |
| Slow test excluded by default | Major | D17; T1 (marker, default deselect), T16, T17 (mandatory `pytest -m slow`, AC-16 must have run), T18 |
| Hashed counts vs requirements question 12 | Minor | D14; T18 README caveat; orchestrator surfaces architecture Q1 at approval |
| Eviction policy underspecified | Minor | D2, D3, D4; T8, T9 and their tests |
| Overflow and non-finite mean | Minor | D9; T6 + T6-test, T11 + T11-test |
| 80-column wording | Minor | D10; T11 docstrings, T18 |
| Unhandled stdout failures, `reconfigure` guard | Minor | D11; T12 + T12-test, T14 |
| Path and token sanitization | Minor | D12; T2, T4, T11, T12 |
| `finish` plus `replace` mechanism | Minor | D8; T10 |
| Blank-line semantics | Minor | D14; T4-test, T14, T18 |
| Strict CSV `"a"b` | Minor | D15; T4-test, T14 |
| Helper location in layout | Minor | D16; Section 2, T1, T7, T13, T15 |
| `field_size_limit` global | Minor | D13; T4, T12-test |

## 7. Blocked Tasks

None. No task needs credentials, network access or an external decision. Two items need user attention at approval but do not block work:

- Architecture section 8 Q1 (hashed unique counts reported as exact above the exact-set budget) differs from requirements question 12. The plan proceeds with the documented assumption; the caveat is documented in T18.
- T16 memory defaults (D1) may change after measurement. The values stay injectable, so no replan is needed.

Platform notes (not blockers): FIFO and permission-denied tests are `skipif` on Windows; the peak-memory helper has separate POSIX and Windows paths, so T16 must be run on the target verification OS.

## 8. Definition of Done (full implementation)

- All tasks T1-T18 complete and their tests passing.
- Default suite (`pytest`) green with line coverage of `src/csv_summary` at or above 90% (the pipeline-wide floor of 80% is exceeded).
- `pytest -m slow` executed as part of Verification and green: AC-16 variants A and B pass with measured peak <= 512 MB and wall time <= 120 s; the measured numbers are recorded in `output/test-results/results.md`. A verification run in which the slow tests were deselected or skipped counts as failed (D17).
- Every AC-1..AC-18 id appears in at least one test name or docstring.
- No file or network write by the tool; runtime imports are standard library only; Python 3.10 compatible syntax and APIs.
- No traceback on any expected failure; stdout empty on every failure path.
- No open Critical or Major code-review findings; the four Major design-review items and all Minor items are closed per the traceability table in section 6.
- `src/csv_summary/README.md` documents the caveats listed in T18.
