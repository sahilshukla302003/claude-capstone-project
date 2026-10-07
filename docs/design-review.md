# Design Review: CSV Summary Report Generator

Reviewed: `docs/architecture.md` against `docs/requirements.md` (FR-1..FR-20, NFR-1..NFR-9, AC-1..AC-18).

## 1. Summary

No blockers found. Implementation may proceed. The architecture is well structured. Components are small and single-purpose, and the interfaces are mostly explicit. The error boundary is centralized, and every FR, NFR and AC traces to a component. The streaming, two-pass design is sound. The ASCII-only regex inference removes the `float()` and `fromisoformat` portability traps.

The main concerns are quantitative and edge-case risks, not structural ones:

- **Memory margin (NFR-1).** The worst-case memory estimate is thinner than it looks.
- **Time budget (NFR-2).** The per-cell cost estimate is optimistic.
- **Silent wrong output.** Non-regular input files (FIFOs, `/dev/stdin`) defeat the two-pass design without any error.
- **Hashed unique counts.** They deviate from requirements question 12 ("approximate counting is not used"). The deviation is disclosed, and the collision probability is negligible.

All of these can be handled during implementation and verification. None needs an architecture revision first.

## 2. Risk Table

| Risk | Severity | Recommendation |
|---|---|---|
| **Memory estimate understates real peak (4.2, `uniques.py`).** Tier 1 charges `getsizeof + 40` per entry. A CPython set table costs 16 B per slot at a load factor of at most 60%. It doubles on resize, so old and new tables coexist transiently. A single 1M-entry column can add roughly 60 MB of transient table on top of the charged 96 MiB. The `set(zip(hi, lo))` compaction transient is also underestimated: tuples of ints are about 150 B per entry, and the doc says "~1 MB per bucket". Freed Tier 1 strings may not return RSS to the OS because of pymalloc fragmentation. Scenario 3 (~420 MB estimated) therefore has little real margin against 512 MB. | Major | Lower the default `exact_limit_bytes` (for example 48 MiB) or measure it. Charge a realistic per-entry cost (about 100 B plus `len`). Make the verification step run the multi-column high-cardinality AC-16 variant and record the actual peak. Keep the budget values injectable so they can be tuned without changing the design. |
| **Time budget optimistic (4.2, NFR-2).** The 1-2 us per cell estimate ignores the per-cell cost on numeric and date columns: regex match, `float()`, Neumaier update and min/max token tracking. These likely cost 3-6 us per cell. On Windows with 10-20M cells, pass 1 alone could approach 60-100 s, and pass 2 adds to that. | Major | Add a fast path in `ColumnAccumulator.observe` (for example `float()` inside try/except, with the regex run only on success to exclude `nan`/`inf`/`_`). Cache the per-column state in local variables. Benchmark early during implementation. Make the `-m slow` test a mandatory part of verification, not just an opt-in. |
| **Non-regular input files cause silent wrong results (3.3, 4.1 step 5).** The design assumes the path can be re-read. A FIFO, `/dev/stdin` or process substitution (`<(cmd)`) opens successfully. Pass 2 then reads nothing or different data, and text unique counts come out as 0 or wrong with exit code 0. The same applies if the file is modified between passes; the doc only notes that errors "surface normally". | Major | In `reader` (or `profiler`), reject non-regular files with `error: cannot read <path>: not a regular file` (`stat.S_ISREG`). In pass 2, also assert that the record count equals pass 1's `row_count`, and raise `CsvSummaryError` on mismatch. |
| **Slow test excluded by default (5.2).** AC-16, NFR-1 and NFR-2 are verified only by a `slow` test that is off by default. The verification step could report green without ever exercising them. | Major | State in the architecture and impl plan that Verification must run `pytest -m slow`. Alternatively, run it via a separate marker or command, and fail the traceability check if AC-16 was not executed. |
| **Hashed unique counts versus requirements question 12 (4.2, section 8 Q1).** Requirements say exact counts are required and approximate counting is not used. Tier 2 is probabilistic (collision probability below 10^-21). The design reports this as "exact". | Minor | Acceptable engineering trade-off, since NFR-6 forbids temp files. The orchestrator should surface section 8 Q1 to the user at approval, and the final README or docs should state the caveat plainly. |
| **Tier 1 to Tier 2 eviction policy underspecified (3.5, 4.2).** It is not stated whether eviction repeats until the total is under the limit. It is not stated whether `pending_limit` is per column or global, or how a column's accounting is credited after conversion. The `UniqueCounter` interface has no documented behavior for `add` after `count`. | Minor | Specify in the impl plan: loop evicting the largest column until under budget; the pending limit is global; `count()` is idempotent and may be called once per column after all `add` calls. The design is also somewhat heavy (256 buckets, a shared budget, a 25% compaction rule). A simpler per-column threshold would be easier to test, but the current approach is defensible. |
| **Numeric overflow and non-finite results (3.4, `format_mean`).** Values such as `1e308` are individually finite, but their sum can overflow to `inf`. Neumaier compensation can then produce `nan`. `format(x, ".4f")` of `1e300` also prints about 300 digits, which breaks the 80-column goal. | Minor | Define behavior: compute the mean in a way that avoids overflow (for example, divide incrementally or catch non-finite), and print `inf`/`nan` or fall back to exponent notation for large magnitudes. Add a unit test. |
| **80-column requirement versus untruncated names (3.7, NFR-5).** The layout claims "at most 80 columns" but does not truncate long column names or min/max tokens. | Minor | Reword to "short lines for typical data" or wrap or truncate with an ellipsis. NFR-5 is only an assumption (A9), so wording is enough. |
| **Unhandled stdout failures (3.8).** `BrokenPipeError` (for example when piping to `head`) and other `OSError` from writing stdout fall through as a traceback. `sys.stdout.reconfigure` fails if stdout is replaced (pytest capture or in-process calls to `main`). | Minor | Guard `reconfigure` with `hasattr`. Catch `BrokenPipeError` and `OSError` around the single write and return 1 quietly. |
| **Only the header is sanitized for terminal control characters (3.7, section 7).** The user-supplied path in error messages, and tokens such as min/max strings, are echoed raw. The mixed-in claim "error messages echo the user-supplied path only" is fine, but min/max/earliest/latest are source tokens that cannot contain control characters only because they passed the regexes. | Minor | Apply the same escape function to the path in error messages. This is cheap and removes the reasoning burden. |
| **`ColumnAccumulator.finish` returns a frozen `ColumnSummary` with `unique_count=None`, and the profiler must fill it (3.4, 3.6).** The mechanism is not specified (`dataclasses.replace`). | Minor | Document it as `dataclasses.replace(summary, unique_count=n)` in `profiler`, or have the accumulator return a mutable intermediate. |
| **Blank-line skipping alters row counts (section 8 Q2).** In a single-column file, blank lines (which are really null rows) are dropped and not counted. This is disclosed but is a silent data-semantics choice. | Minor | Keep it, but add an explicit test and a note in the user documentation. |
| **Strict CSV mode rejects `"a"b` (section 8 Q7).** Real-world sloppy files will fail with exit 1 rather than being profiled. | Minor | Acceptable and consistent with NFR-3. Keep the error message actionable (line number is included). |
| **Test helper location not in the package layout (5.2).** `tests/helpers/run_with_peak.py` is referenced but the layout lists only `unit`, `integration` and `fixtures`. The impl plan could miss it. | Minor | Add `tests/helpers/` to the layout and to the implementation plan. |
| **`csv.field_size_limit` is process-global (3.3).** Setting it inside `reader` changes global state, which matters if tests call `main` in-process. | Minor | Set it once at module import in `reader.py`, or restore it in a `finally`. It is idempotent either way. |

## 3. Design Decisions Confirmed

- **Single error boundary** (`CsvSummaryError` plus `cli.main`). The exit-code table and the "no traceback, empty stdout on failure" rule are consistent with NFR-3, AC-3 and AC-17. Building the report fully in memory before writing is correct.
- **Two-pass processing.** Type is only known at end of file, so deferring unique collection to text columns avoids holding sets for ID-like numeric columns. Skipping pass 2 when there are no text columns is a good optimization.
- **ASCII-only regexes plus `float()` / `datetime` validation.** This is deterministic across Python 3.10-3.13 and across platforms. It avoids `nan`, `inf`, hex, underscore and Unicode-digit leniency. The regexes are linear, so ReDoS is not a concern.
- **Stable hashing.** `blake2b` instead of the salted built-in `hash()` preserves NFR-4 determinism. Reporting output from a count rather than iterating sets also avoids ordering dependence.
- **Neumaier summation.** This is O(1) memory and deterministic, and it is a sensible alternative to `fsum`.
- **Reader encapsulation.** `reader.py` is the only module that touches the filesystem or `csv`. It uses read-only open, `utf-8-sig`, `newline=""` and `strict=True`. It checks `isdir` first for portable messages and enforces the field-size limit.
- **Pure `report.py` and `models.py`.** Frozen dataclasses, no I/O and an injectable `UniqueBudget` give good testability (NFR-9).
- **Stdlib-only runtime, dev-only pytest.** This satisfies NFR-7 and NFR-8. The requirement traceability table in 3.9 is complete.
- **Test strategy.** Table-driven inference tests, forced Tier 2 conversion against a `len(set())` oracle, subprocess integration tests with a no-traceback check, and a byte-compare for AC-18.
- **Security posture.** No shell, `eval` or `pickle`; the path is treated purely as data; no writes or network access. These are appropriate for the scope.
- **Appropriately sized architecture.** Ten small modules for a CLI tool, with no unnecessary framework, plugin or config layer.

## 4. Required Changes Before Implementation

None.

The Major items above (memory margin, time budget, non-regular file handling, mandatory slow test) should be carried into `docs/impl-plan.md` as explicit tasks or acceptance checks. They do not require an architecture revision.
