# Architecture: CSV Summary Report Generator

Source: `docs/requirements.md` (FR-1..FR-20, NFR-1..NFR-9, AC-1..AC-18). All assumptions A1-A11 and open questions 12-15 in the requirements are approved by the user and are treated as fixed.

## 1. System Overview

`csv_summary` is a single-process, standard-library-only command-line tool, run as `python -m csv_summary <path-to-csv>`. It streams the CSV twice with the `csv` module: pass 1 infers column types and computes numeric/date statistics in O(columns) memory. Pass 2 runs only if a text column has non-null values, and computes exact unique counts for those columns using a memory-bounded two-tier structure. A formatter then prints a deterministic plain-text report to stdout, and a single error boundary in the CLI maps every expected failure to a one-line stderr message and exit code 1.

## 2. Component Diagram

```
 argv
  |
  v
+---------------------------+   raises CsvSummaryError    +----------------+
| cli.py                    |<----------------------------|  errors.py     |
|  main(argv) -> int        |                             |  CsvSummaryErr |
|  parse args, error        |                             +----------------+
|  boundary, stdout/stderr  |                                    ^
+------+--------------+-----+                                    | raised by
       | path         | Summary                                  | all below
       v              v
+---------------+   +----------------+
| profiler.py   |   | report.py      |
| profile_file  |   | render_report  |
| (2 passes)    |   | (Summary->str) |
+--+---+---+----+   +-------+--------+
   |   |   |                |
   |   |   +----------------+--------------+
   |   |                                   |
   |   v                                   v
   | +---------------------+        +--------------+
   | | inference.py        |        | models.py    |
   | |  parse_number       |------->|  ColumnType  |
   | |  parse_date         |        |  ColumnSumm. |
   | |  ColumnAccumulator  |        |  Summary     |
   | +---------------------+        +--------------+
   |
   +--------------------+
   |                    v
   |           +----------------------+
   |           | uniques.py           |
   |           |  UniqueBudget        |
   |           |  UniqueCounter       |
   |           |  (exact set -> 128-bit|
   |           |   hashed buckets)    |
   |           +----------------------+
   v
+---------------------------+
| reader.py                 |
|  open_records(path)       |  -> generator of padded rows
|  (utf-8-sig, csv.reader)  |
+-------------+-------------+
              |
              v
        [ CSV file on disk, read-only ]
```

Package layout: `src/csv_summary/{__init__,__main__,cli,errors,models,reader,inference,uniques,profiler,report}.py` plus the tool README `src/csv_summary/README.md`. Tests live in `tests/unit`, `tests/integration`, `tests/fixtures`, `tests/helpers`; `scripts/verify.py` is the verification gate (default suite, `pytest -m slow`, coverage >= 90%, AC traceability).

## 3. Component Descriptions

### 3.1 `errors.py`
Responsibility: the single exception type for expected failures, plus the shared sanitiser used by `reader`, `profiler`, `cli` and `report` (kept here to avoid import cycles).
```python
class CsvSummaryError(Exception):
    def __init__(self, message: str, exit_code: int = 1) -> None: ...
    message: str
    exit_code: int

def escape_control(text: str) -> str:   # repr-style escapes for non-printable chars, no quotes;
                                        # printable non-ASCII is left unchanged
```
FRs: FR-3, FR-4, FR-20 (error path), NFR-3, NFR-5.

### 3.2 `models.py`
Responsibility: immutable data carried from profiler to report. No logic.
```python
class ColumnType(str, Enum):  NUMERIC = "numeric"; TEXT = "text"; DATE = "date"

@dataclass(frozen=True)
class ColumnSummary:
    name: str
    type: ColumnType
    null_count: int
    min: str | None = None          # numeric: source token of the minimum; date: earliest as written
    max: str | None = None          # numeric: source token of the maximum; date: latest as written
    mean: float | None = None       # numeric only
    unique_count: int | None = None # text only

@dataclass(frozen=True)
class Summary:
    row_count: int
    columns: tuple[ColumnSummary, ...]   # file order
```
FRs: FR-8, FR-9, FR-14, FR-15, FR-16, FR-17 (data shape).

### 3.3 `reader.py`
Responsibility: open the file and yield well-formed records; nothing else knows about the file system or `csv`.
```python
def open_records(path: str) -> Iterator[list[str]]:
    """Generator. First item is the header (list of names); every later item is a
    data record padded with "" to header width. Blank lines (csv yields []) are skipped.
    Raises CsvSummaryError for: not found, directory, non-regular file (FIFO, device,
    /dev/stdin), permission/OS error, UnicodeDecodeError, csv.Error, record wider than header.
    Yields nothing for a 0-byte file. The file is closed when the generator ends or is closed."""
```
Implementation constraints: `open(path, "r", encoding="utf-8-sig", newline="")` (tolerates a BOM, lets `csv` handle embedded newlines); `csv.reader(f, delimiter=",", strict=True)`; `csv.field_size_limit(10 * 1024 * 1024)` set once at module import so an unterminated quote fails fast with a clear error rather than swallowing the file; `_check_path` runs `os.path.isdir`, then `os.stat` and `stat.S_ISREG` before `open`, so the directory message is identical on all OSes and non-regular files are rejected with `cannot read <path>: not a regular file` (the file is read twice, so pipes cannot work). Error messages include the (escaped) path and the 1-based physical line (`reader.line_num`) where relevant. The header width is the length of the first non-blank row. Wide-row check: `len(row) > header_width` -> error (padding handles `len(row) < header_width`).
FRs: FR-1 (path use), FR-3, FR-4, FR-5 (empty file yields no header), FR-6, FR-19, FR-20; NFR-3, NFR-6, NFR-7.

### 3.4 `inference.py`
Responsibility: pure functions and a per-column accumulator for pass 1.
```python
def is_null(raw: str) -> bool:                       # raw.strip() == ""
def parse_number(token: str) -> float | None:        # token already stripped
def parse_date(token: str) -> tuple[int, ...] | None # sort key (y, m, d, H, M, S, us)

class ColumnAccumulator:
    def __init__(self, name: str) -> None: ...
    def observe(self, raw: str) -> None: ...
    def finish(self, row_count: int) -> ColumnSummary:
        """Final type decision. unique_count is left None for TEXT; the profiler fills it."""
    @property
    def needs_unique_pass(self) -> bool:  # type is TEXT and non-null count > 0
```
Rules (all ASCII-only; compiled `re` patterns with `re.ASCII`):
- Number: `float()` is tried first (fast path); on success the result must be finite (rejects `1e999`) and the token must full-match `[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?` (ASCII). This excludes `nan`, `inf`, hex and `1_000` (which bare `float()` would accept; assumption 13). Leading zeros are numeric (assumption 15).
- Date: `\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d{1,6})?)?)?` full match, then validated by constructing `datetime.date`/`datetime.time` (rejects `2024-02-30`, `25:00`). Offsets and `Z` are not accepted, so such columns are `text` (time zones are out of scope). The regex is used instead of `fromisoformat` because its accepted syntax differs between Python 3.10 and 3.11+ (NFR-7, NFR-4). Date-only compares as midnight.
- Accumulator state: `non_null`, `null_count`, a single mode (undecided / numeric / date / text) set by the first non-null value, running `min/max` (value plus the source token of the extreme; first occurrence wins ties), a Neumaier-compensated float sum, date min/max keys and tokens. The first non-conforming value for the current mode demotes the column to text, discarding stats; a text column only counts nulls afterwards (fast path). Numeric and date patterns are disjoint, so the mode is unambiguous.
- Type decision in `finish`: `non_null == 0` or mode text -> TEXT (FR-17); numeric -> NUMERIC (mean = sum / non_null); date -> DATE. If the running sum overflows, the mean is `inf`/`-inf` (or `nan`), never an exception.
- Numeric stats are held as `float`; integers above 2**53 lose comparison precision (accepted; noted in 8).
FRs: FR-9..FR-14, FR-16, FR-17; AC-8, AC-10..AC-13.

### 3.5 `uniques.py`
Responsibility: exact unique-value counting for text columns within a shared memory budget. See section 4.2.
```python
class UniqueBudget:
    def __init__(self, exact_limit_bytes: int = 48 * 2**20,
                 pending_limit: int = 2_000_000) -> None: ...

class UniqueCounter:
    def __init__(self, n_columns: int, budget: UniqueBudget | None = None) -> None: ...
    def add(self, column_index: int, value: str) -> None:   # value is non-null, un-stripped;
                                                            # RuntimeError if called after count()
    def count(self, column_index: int) -> int:               # exact distinct count; idempotent
    def is_hashed(self, column_index: int) -> bool:          # for tests/diagnostics
```
FRs: FR-15, FR-18; NFR-1; AC-9, AC-16.

### 3.6 `profiler.py`
Responsibility: orchestrate the passes and assemble the `Summary`.
```python
def profile_file(path: str, *, budget: UniqueBudget | None = None) -> Summary | None:
    """Return None if the file has no data rows (0 bytes or header only)."""
```
Steps in section 4.1. Raises `CsvSummaryError` (propagated from `reader`), or `<path>: file changed while being read` if pass 2 reads a different record count than pass 1. `unique_count` is filled with `dataclasses.replace`; text columns without a pass 2 get 0.
FRs: FR-5, FR-6, FR-8, FR-14, FR-15, FR-16, FR-17, FR-18; NFR-1, NFR-2.

### 3.7 `report.py`
Responsibility: format `Summary` as plain text; pure, deterministic, no I/O.
```python
NO_DATA_MESSAGE = "No data rows found"
def render_report(summary: Summary | None) -> str:   # ends with "\n"
def format_mean(value: float) -> str:                # <= 4 decimals, trailing zeros trimmed, "-0" -> "0";
                                                     # abs >= 1e15 -> exponent form; "inf", "-inf", "nan" literal
```
Layout (short lines for typical data, one block per column, file order; long names and tokens are not truncated, so 80 columns is not guaranteed):
```
Rows: 10

Column 1: name
  Type: numeric
  Min: 1
  Max: 3
  Mean: 2
  Nulls: 1
```
Text blocks print `Unique: n` and `Nulls: n`; date blocks print `Earliest`, `Latest`, `Nulls`. Min/max/earliest/latest are printed as the source token (stripped), as stated for dates in A3. Floating-point output uses `format(x, ".4f")` then trims, never `repr`, so output is identical across platforms (NFR-4). Control characters in column names and min/max/earliest/latest tokens are printed as `repr`-style escapes (`errors.escape_control`) to keep the output single-line per field.
FRs: FR-5, FR-7, FR-8, FR-9, FR-14, FR-15, FR-16, FR-17; NFR-4, NFR-5.

### 3.8 `cli.py` and `__main__.py`
Responsibility: argument handling, the error boundary, and exit codes. `__main__.py` is `from .cli import main; raise SystemExit(main())`.
```python
def main(argv: Sequence[str] | None = None) -> int:
```
Behavior: `argparse.ArgumentParser(prog="csv_summary")` with one positional `path`; `parse_args` errors exit with code 2 and usage on stderr (FR-2; also covers extra arguments). `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` (guarded: skipped if unavailable, errors ignored) so non-ASCII names never raise `UnicodeEncodeError` on a legacy Windows console. The report is built fully in memory and written once after profiling succeeds, so a mid-file failure leaves stdout empty (AC-3, AC-17). The single stdout write returns 1 on `BrokenPipeError` (stdout is then redirected to devnull to suppress the interpreter's shutdown message) and on other `OSError` (`error: cannot write output: ...`). Catches `CsvSummaryError` (prints `error: <message>` to stderr, returns `exit_code`), `MemoryError` (`error: out of memory while processing <path>`, 1), `KeyboardInterrupt` (returns 130, no traceback). Any other exception is a bug and is allowed to propagate.
FRs: FR-1, FR-2, FR-3, FR-4, FR-7; NFR-3, NFR-5, NFR-6.

### 3.9 Requirement traceability

| Requirement | Component(s) |
|---|---|
| FR-1, FR-2 | `cli` |
| FR-3, FR-4 | `reader` (raise), `cli` (map to exit 1) |
| FR-5 | `reader` (no header / no rows), `profiler` (None), `report` |
| FR-6, FR-8 | `reader` (header split), `profiler` (row count), `report` |
| FR-7 | `cli`, `report` |
| FR-9 | `inference`, `models`, `report` |
| FR-10, FR-11, FR-12, FR-13 | `inference` |
| FR-14, FR-16 | `inference` (stats), `report` |
| FR-15 | `uniques`, `profiler`, `report` |
| FR-17 | `inference` (`non_null == 0` -> TEXT), `profiler` (unique 0) |
| FR-18, NFR-1 | `reader` (streaming), `uniques` (budget), `profiler` (two passes) |
| FR-19, FR-20 | `reader` |
| NFR-2 | `inference` fast paths, `profiler` pass skipping |
| NFR-3, NFR-5 | `errors`, `cli`, `reader` |
| NFR-4 | `report`, `inference` (Neumaier sum, no set-iteration order dependence) |
| NFR-6 | `reader` (read-only open), whole design (no writes/network/eval) |
| NFR-7, NFR-8 | stdlib only, ASCII regexes instead of version-specific `fromisoformat` |
| NFR-9 | injectable `UniqueBudget`, pure functions (section 5.2) |

## 4. Data Flow

### 4.1 Step by step
1. `main(argv)` parses the single `path`. Wrong arity -> argparse usage on stderr, exit 2.
2. `profile_file(path)` starts **pass 1**: `open_records(path)` is iterated. The first record is the header; if there is none (0-byte file) return `None`.
3. For each data record, increment `row_count` and call `observe(raw)` on each column's `ColumnAccumulator`. Records are padded to header width by `reader`, so short rows yield nulls. A record wider than the header raises `CsvSummaryError` (line number and path in the message).
4. If `row_count == 0` (header only), return `None`. Otherwise call `finish(row_count)` on each accumulator to fix types and numeric/date statistics.
5. If any column `needs_unique_pass`, start **pass 2**: re-open the file with `open_records`, and for each record feed `uniques.add(i, raw)` only for those column indices and only for non-null values (`raw.strip() != ""`). Then set `unique_count = uniques.count(i)`. All-null text columns get 0 without pass 2 (FR-17). If no text column has data, pass 2 is skipped, so an all-numeric/date file is read once.
6. Return `Summary`. `cli` calls `render_report`, writes it to stdout, returns 0. `None` renders `No data rows found` and also returns 0.

Why two passes: a column's type is only known at end of file (`1, 2, abc` is text), and unique values of `1` and `2` are needed in that case. Collecting uniques for every column during pass 1 would hold a set for each numeric ID-like column that is later discarded. Two passes keep pass 1 at O(columns) memory and confine the unique-set cost to columns that are really text. Cost: up to 2x read/parse time, which fits NFR-2 (see 4.2).

### 4.2 Memory strategy: 100 MB CSV under 512 MB with exact unique counts

Pass 1 holds only per-column scalars and one row at a time: tens of MB at most (interpreter ~15-25 MB, `csv` row list and file buffer under 1 MB for normal rows, bounded by the 10 MB field limit). Memory-relevant state is therefore entirely the unique-value structure in pass 2.

A plain `set[str]` costs about `49 + len` bytes per string plus ~30-40 bytes of set slot overhead, around 90-100 bytes per short value. A 100 MB file with one high-cardinality text column (about 9 M distinct 10-character values) would need ~850 MB, so a plain set cannot meet NFR-1. The design uses two tiers inside `UniqueCounter`, per column, under one shared `UniqueBudget`:

- **Tier 1, exact set.** Each column starts with a `set[str]`. Charged cost per new entry is `sys.getsizeof(value) + 100` (set slot, resize and fragmentation allowance) against a shared `exact_limit_bytes` (default 48 MiB). Eviction loops, converting the column with the largest charge (ties: lowest index) until the total is under the limit. Low and medium cardinality columns (the common case) never leave this tier and are exact by construction.
- **Tier 2, 128-bit digest store.** When the shared exact total exceeds the limit, the column holding the largest exact total is converted: each string is hashed with `hashlib.blake2b(value.encode("utf-8"), digest_size=16)`, its set is dropped (budget credited), and it continues as a hashed column. Hashed storage is 256 buckets keyed by the first digest byte, each bucket two `array("Q")` (high and low 64 bits of the digest), i.e. 16 bytes per entry with no per-object overhead. New digests are appended to the bucket (duplicates allowed). Compaction runs when pending (uncompacted) entries exceed `max(pending_limit, 25% of compacted entries)`: each bucket is rebuilt as `set(zip(hi, lo))` then written back to the arrays, so the transient is one bucket (about 1/256 of the data) at a time. `count()` compacts and sums bucket sizes. The 25% rule keeps total compaction work amortized and pending memory bounded.

Why the result is exact in practice: the distinct count of Tier 1 is exact. For Tier 2 a wrong count requires two different values with the same 128-bit digest. For n distinct values the probability is about n^2 / 2^129; for n = 10^8 it is below 10^-21. This is called "exact" for this tool; a deterministic alternative would require spilling raw values to a temporary file, which NFR-6 forbids ("shall not write files"). This is the one place where the "exact counts" assumption is satisfied probabilistically, and it is recorded in 8 (question 1).

Memory budget for the 100 MB test file (assumed shapes):

| Scenario | Unique state | Estimated peak |
|---|---|---|
| Typical (few text columns, low/medium cardinality) | <= 48 MiB exact | ~100 MB |
| One text column, ~9 M all-distinct values | ~144 MB hashed + <= 32 MB pending + transient bucket ~1 MB | ~230 MB |
| ~20 M distinct values over several text columns (about the maximum a 100 MB file can contain, since each distinct value needs at least ~5 bytes of file) | ~320 MB hashed + pending | ~420 MB |

Residual risk: a deliberately constructed file with more than ~25 M distinct short values across many columns could exceed 512 MB; with this design that is outside what 100 MB can contain in realistic data and is not mitigated further. AC-16 is verified with the all-distinct single-column case plus a mixed case (section 5.2).

Time (NFR-2): `csv.reader` plus per-cell Python work is roughly 1-2 us per cell; the pass-1 fast path for demoted (text) columns reduces it to a null check, and pass 2 only touches text columns. A 100 MB file (about 10-20 M cells) is estimated at 30-90 s worst case for both passes, within 120 s. Hashing adds roughly 1 us per value only once a column is in Tier 2. If measurements in verification exceed 120 s, the first optimization is skipping pass 2 `strip()` calls for columns with no whitespace-only values, not changing the design.

### 4.3 Error handling and exit codes

| Exit code | Meaning | Output |
|---|---|---|
| 0 | Success, including empty / header-only file | stdout: report or `No data rows found` |
| 1 | Expected runtime failure | stderr: one line `error: ...`; stdout empty |
| 2 | Usage error (argparse) | stderr: usage and message |
| 130 | Interrupted (Ctrl-C) | none |

| Condition | Detected in | Message (stderr) | Exit |
|---|---|---|---|
| Missing/extra argument | `cli` / argparse | usage + `the following arguments are required: path` | 2 |
| File does not exist (`FileNotFoundError`) | `reader` | `error: file not found: <path>` | 1 |
| Directory (`os.path.isdir`) | `reader` | `error: cannot read <path>: is a directory` | 1 |
| Non-regular file (`stat.S_ISREG` false) | `reader` | `error: cannot read <path>: not a regular file` | 1 |
| File changed between passes | `profiler` | `error: <path>: file changed while being read` | 1 |
| Stdout write failure (`BrokenPipeError`, `OSError`) | `cli` | none / `error: cannot write output: <strerror>` | 1 |
| Permission or other `OSError` | `reader` | `error: cannot read <path>: <strerror>` | 1 |
| Invalid UTF-8 (`UnicodeDecodeError`) | `reader` | `error: <path>: invalid UTF-8 encoding` | 1 |
| Malformed CSV / field too large (`csv.Error`) | `reader` | `error: <path>: line <n>: <csv message>` | 1 |
| Row wider than header | `reader` | `error: <path>: line <n>: row has <k> fields but header has <m>` | 1 |
| `MemoryError` | `cli` | `error: out of memory while processing <path>` | 1 |
| Empty or header-only file | `profiler` returns `None` | stdout `No data rows found` | 0 |

No traceback is printed for any row above. Because the report is written only after both passes succeed, failures never produce partial stdout. Errors raised in pass 2 cannot be new in practice (the same bytes were validated in pass 1) but are handled by the same boundary; if the file is modified between passes the error surfaces normally.

## 5. Technology Choices

### 5.1 Stack

| Choice | Justification |
|---|---|
| Python >= 3.10, stdlib only (NFR-7, NFR-8) | Mandated. Avoids pandas/polars, which would load or chunk differently and break the dependency rule. |
| `csv` module, `strict=True`, `newline=""`, `utf-8-sig` | C-implemented RFC 4180 parser handles quotes, embedded delimiters and newlines (FR-19) and streams row by row (FR-18). `utf-8-sig` tolerates a leading BOM. |
| `argparse` | Provides usage output and exit code 2 for free (FR-2). |
| `re` with `re.ASCII` for number/date | Identical behavior on 3.10-3.13; avoids Unicode digits, `float()` leniency (`nan`, `inf`, `1_0`) and `fromisoformat` version differences. |
| `datetime` | Calendar validity checks only (`date(y, m, d)`, `time(...)`). |
| `hashlib.blake2b(digest_size=16)` | Fast, stdlib, stable across runs and platforms (unlike built-in `hash()` which is salted per process and would break determinism). |
| `array("Q")` buckets | 8 bytes per word with no object overhead, the core of the memory plan. |
| Neumaier compensated sum | Deterministic, O(1) memory, avoids drift on 10 M values without `fsum`'s full list requirement. |
| Dataclasses + enum | Simple, typed, testable data contracts. |
| Two-pass processing | Reasoned in 4.1; the input is a regular file path (stdin is out of scope), so re-reading is always possible. |

### 5.2 Testing approach

Tooling: `pytest` and `pytest-cov` are dev-only dependencies and are not imported by `src/`. Tests use `tmp_path`; fixtures live in `tests/fixtures/`.

- **Unit (`tests/unit/`)**
  - `inference`: table-driven cases for `parse_number` (`1`, `-1.5`, `+.5`, `1e3`, `007`, `nan`, `inf`, `0x10`, `1_000`, `1e999`, Arabic-Indic digits all as expected) and `parse_date` (`2024-02-29`, `2023-02-29` invalid, `2024-01-15T10:30:00`, `2024-01-15T25:00`, `...Z` rejected, `20240115` rejected). Accumulator tests for mixed values (AC-11), whitespace nulls (AC-12), all-null (AC-13), tie handling, and Neumaier accuracy.
  - `uniques`: with a tiny injected `UniqueBudget(exact_limit_bytes=..., pending_limit=...)`, force conversion to Tier 2 and assert counts equal a reference `len(set(values))` on random data with duplicates (multiple compactions, multiple columns, forced eviction of the largest column). Assert `is_hashed` flips.
  - `reader`: padded short rows (AC-15), wide row error, blank-line skipping, BOM, quoted `"a,b"` and embedded newline (AC-14), invalid UTF-8 (AC-17), directory and missing path.
  - `report`: golden-string tests for each column type, `format_mean` rounding, 80-column width, `No data rows found`.
- **Integration (`tests/integration/`)** use `subprocess.run([sys.executable, "-m", "csv_summary", path])` with `PYTHONPATH=src`, asserting stdout, stderr (no `Traceback`) and the return code for AC-1..AC-15, AC-17, AC-18 (run twice, compare bytes). AC-2 asserts exit code 2 and usage text. A Windows-compatible permission-denied case is skipped where it cannot be simulated.
- **Large-file test (AC-16, NFR-1, NFR-2)**, marked `@pytest.mark.slow` and excluded by default (`-m slow` to run): a generator writes a ~100 MB CSV to `tmp_path` with a numeric, a date, a low-cardinality text, and an all-distinct text column (second variant: several high-cardinality text columns). The CLI is run through a small wrapper (`tests/helpers/run_with_peak.py`) in a subprocess that calls `main()` and then prints peak memory on stderr using `resource.getrusage(RUSAGE_SELF).ru_maxrss` on POSIX (KiB on Linux, bytes on macOS, normalised in the helper) or `ctypes` `GetProcessMemoryInfo` `PeakWorkingSetSize` on Windows. The test asserts exit 0, peak <= 512 MB, wall time <= 120 s, and the exact expected unique count (known from the generator).
- **Coverage:** target >= 90% line coverage for `src/csv_summary`; every AC id appears in at least one test name or docstring for the verification step's traceability check.

## 6. External Dependencies

| Dependency | Type | Version constraint |
|---|---|---|
| Python standard library (`argparse`, `csv`, `re`, `datetime`, `hashlib`, `array`, `enum`, `dataclasses`, `os`, `sys`, `math`, `collections.abc`) | Runtime | Python >= 3.10 |
| `pytest` | Dev/test only | >= 7.0 |
| `pytest-cov` | Dev/test only | >= 4.0 |
| Input file | Storage, read-only, one file | UTF-8, comma-delimited |
| Network, databases, services, environment variables, config files | None | n/a |

## 7. Security Considerations

- **Path handling:** `path` is passed only to `os.path.isdir` and `open(..., "r")`. It is never interpolated into a shell command, `eval`, or `exec`, and no subprocess is spawned by the tool. Symlinks are followed by `open` (the user named that path). The tool does not canonicalize or restrict paths, since reading any file the user can read is the purpose.
- **Read-only:** no file is created, modified or deleted; no temporary files (the reason unique counting uses in-memory hashing, 4.2); no network access (NFR-6).
- **Untrusted content:** file content is data only. It is parsed by `csv`, matched by anchored regexes, and passed to `float()` only after the regex check. There is no `eval`, `pickle`, `yaml`, or dynamic import.
- **Resource exhaustion:** field size limit of 10 MB prevents an unterminated quote from buffering the whole file; the unique-value budget bounds memory (4.2). The regexes are linear (no nested quantifiers), so there is no ReDoS risk.
- **Output safety:** column names come from the file and are printed with control characters escaped, so a crafted header cannot inject terminal escape sequences into the report. Error messages echo the user-supplied path only.
- **Secrets:** none handled or logged.
- **Failure behavior:** all expected failures produce a one-line message without a traceback, so internal paths and code are not disclosed (NFR-3).

## 8. Open Design Questions

Each item has the assumption already used in this document; none blocks implementation if the assumption is accepted.

1. **Exactness of unique counts above the exact-set budget.** Strict mathematical exactness for very high-cardinality columns would need spilling to a temp file (prohibited by NFR-6) or a per-value set that cannot meet 512 MB (4.2). *Assumption:* exact sets up to a 48 MiB shared budget, then 128-bit digests (collision probability below 10^-21 at 10^8 values), reported as exact. Confirm this is acceptable, or relax NFR-6 to allow a temp file.
2. **Blank lines.** `csv.reader` returns `[]` for an empty line. For a single-column file this is indistinguishable from a null row. *Assumption:* completely empty lines are skipped and not counted as rows (including before the header); a line with only delimiters (`,,`) is a row of nulls.
3. **Whitespace in text values.** Null detection strips whitespace (FR-13) and numeric/date inference strips before parsing, but should `"a"` and `" a"` be one unique text value? *Assumption:* text values are compared as written, unstripped.
4. **Min/max display.** Requirements fix only mean precision (up to 4 decimals). *Assumption:* numeric min/max print the stripped source token of the extreme value (e.g. `1`, `-0.00001`, `1e3`); the mean is formatted with up to 4 decimals. Equal values (`1` and `1.0`) keep the first occurrence.
5. **Numeric precision.** Values are held as `float`, so integers above 2**53 compare and average with float precision. *Assumption:* acceptable; exact big-integer arithmetic is not required.
6. **Duplicate or empty header names.** *Assumption:* columns are identified by position; names are printed as written, duplicates and empty names allowed, empty name printed as an empty string after `Column N:`.
7. **Strict CSV quoting.** `csv.reader(strict=True)` rejects a closing quote followed by other text (for example `"a"b`) with exit code 1 instead of guessing. *Assumption:* consistent with "malformed row" in NFR-3.
