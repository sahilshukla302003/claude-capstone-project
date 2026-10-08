# Requirements: CSV Summary Report Generator

Source: `user-stories/user-story-1.md`

## 1. Functional Requirements

- **FR-1** Accept exactly one positional command-line argument, the path to a CSV file, via `python -m csv_summary <path-to-csv>`.
- **FR-2** Reject invocation with a missing or extra positional argument by printing a usage message to stderr and exiting with a non-zero code (assumed 2).
- **FR-3** Print an error message naming the path to stderr and exit with code 1 when the file does not exist.
- **FR-4** Print an error message to stderr and exit with code 1 when the path exists but cannot be read (is a directory, permission denied) (assumption A2).
- **FR-5** Print "No data rows found" to stdout and exit with code 0 when the file is empty (0 bytes) or contains only a header row.
- **FR-6** Treat the first row as the header and exclude it from the row count.
- **FR-7** Print the summary report to stdout and exit with code 0 on success.
- **FR-8** Include in the report the total number of data rows (excluding header).
- **FR-9** Include in the report every column name, in file order, with its inferred type: `numeric`, `text`, or `date`.
- **FR-10** Infer a column as `numeric` when every non-null value parses as a number (integer or decimal, optional sign, optional exponent).
- **FR-11** Infer a column as `date` when every non-null value is a valid ISO 8601 date (`YYYY-MM-DD`; datetime values such as `YYYY-MM-DDTHH:MM:SS` are also accepted, assumption A3).
- **FR-12** Infer a column as `text` when it is neither numeric nor date, including when values are mixed.
- **FR-13** Treat an empty field (and whitespace-only field) as null in every column type (assumption A4).
- **FR-14** For each numeric column, report min, max, mean and null count.
- **FR-15** For each text column, report the count of unique non-null values and the null count.
- **FR-16** For each date column, report the earliest date, the latest date and the null count.
- **FR-17** For a column whose values are all null, report type `text` with unique count 0 and null count equal to the row count (assumption A5).
- **FR-18** Process the file in a streaming or chunked manner so that memory use does not grow in proportion to file size, except for state needed for unique-value counting.
- **FR-19** Parse quoted fields, embedded delimiters and embedded newlines per RFC 4180, with comma as the delimiter and UTF-8 encoding (assumption A1, A6).
- **FR-20** Treat a data row with fewer fields than the header as having nulls for the missing fields; report a row with more fields than the header as an error to stderr with exit code 1 (assumption A7).

## 2. Non-Functional Requirements

- **NFR-1 (Performance, memory)** Peak memory shall not exceed 512 MB while processing a 100 MB CSV file.
- **NFR-2 (Performance, time)** A 100 MB CSV shall be processed in 120 seconds or less on a typical developer machine (assumption A8).
- **NFR-3 (Reliability)** The tool shall never print a Python traceback for expected failures (missing file, unreadable file, malformed row, bad encoding). Each shall produce a one-line error message and exit code 1.
- **NFR-4 (Reliability)** Output shall be deterministic: the same input yields byte-identical output.
- **NFR-5 (Usability)** Error messages shall state what failed and the offending path. Report layout shall be plain text, one section per column, readable at 80 columns (assumption A9).
- **NFR-6 (Security)** The tool shall only read the file given; it shall not write files, make network calls, or execute file content. Input paths are treated as data, not as commands.
- **NFR-7 (Portability)** The tool shall run on Python 3.10 or later on Windows, Linux and macOS (assumption A10).
- **NFR-8 (Dependencies)** The tool shall use only the Python standard library at runtime (assumption A11).
- **NFR-9 (Testability)** Core behavior shall be verifiable by automated tests using small fixture CSV files; the memory and size criteria by one large generated file test.

## 3. Out of Scope

- Output formats other than plain text to stdout (JSON, HTML, file output).
- Delimiters other than comma, and automatic delimiter detection.
- Encodings other than UTF-8 (including BOM handling beyond tolerating a UTF-8 BOM).
- Statistics beyond those listed (median, standard deviation, percentiles, histograms).
- Non-ISO 8601 date formats, locale-specific number formats (e.g. `1.234,56`), and time zone normalization.
- Boolean, categorical or other type inference beyond numeric, text and date.
- Multiple input files, reading from stdin, URLs or compressed files.
- Interactive mode, a GUI, and configuration files.
- Data cleaning or modification of the input file.

## 4. Acceptance Criteria

- **AC-1 (FR-1, FR-7, FR-8, FR-9)** Given a valid CSV with 3 columns and 10 data rows, when the tool is run with its path, then stdout contains row count 10 and each of the 3 column names with its type, and exit code is 0.
- **AC-2 (FR-2)** Given no path argument, when the tool is run, then a usage message goes to stderr and the exit code is non-zero.
- **AC-3 (FR-3)** Given a non-existent path, when the tool is run, then stderr contains an error with the path, stdout is empty, and exit code is 1.
- **AC-4 (FR-4)** Given a path that is a directory, when the tool is run, then an error is printed to stderr with no traceback and exit code is 1.
- **AC-5 (FR-5)** Given a CSV containing only a header row, when the tool is run, then stdout contains "No data rows found" and exit code is 0.
- **AC-6 (FR-5)** Given a 0-byte file, when the tool is run, then stdout contains "No data rows found" and exit code is 0.
- **AC-7 (FR-6, FR-8)** Given a header plus 5 data rows, when the tool is run, then reported row count is 5.
- **AC-8 (FR-10, FR-14)** Given a numeric column with values 1, 2, 3, and one empty field, when the tool is run, then the column is `numeric` with min 1, max 3, mean 2, null count 1.
- **AC-9 (FR-12, FR-15)** Given a text column with values "a", "b", "a", and one empty field, when the tool is run, then the column is `text` with unique count 2 and null count 1.
- **AC-10 (FR-11, FR-16)** Given a date column with values 2024-01-15, 2023-06-01, 2024-12-31 and one empty field, when the tool is run, then the column is `date` with earliest 2023-06-01, latest 2024-12-31, null count 1.
- **AC-11 (FR-12)** Given a column with values "1", "2", "abc", when the tool is run, then it is typed `text`.
- **AC-12 (FR-13)** Given a field containing only whitespace in a numeric column, when the tool is run, then it is counted as null.
- **AC-13 (FR-17)** Given a column with all fields empty across 4 rows, when the tool is run, then it is `text` with unique count 0 and null count 4.
- **AC-14 (FR-19)** Given a field `"a,b"` and a field with an embedded newline in quotes, when the tool is run, then each is parsed as a single value and the row count is not inflated.
- **AC-15 (FR-20)** Given a data row with fewer fields than the header, when the tool is run, then missing fields count as null. Given a row with more fields, then an error is printed to stderr and exit code is 1.
- **AC-16 (FR-18, NFR-1)** Given a generated 100 MB CSV, when the tool is run, then it completes with exit code 0 and peak memory is at most 512 MB.
- **AC-17 (NFR-3)** Given an invalid UTF-8 file, when the tool is run, then a one-line error is printed to stderr with no traceback and exit code is 1.
- **AC-18 (NFR-4)** Given the same file run twice, when outputs are compared, then they are identical.

## 5. Open Questions

1. **A1 Delimiter and encoding:** Is comma-delimited UTF-8 the only supported format? Assumption: yes.
2. **A2 Unreadable path:** Should directories and permission errors also exit 1? Assumption: yes.
3. **A3 Date scope:** Are ISO 8601 datetimes (with time) valid as `date`, or only `YYYY-MM-DD`? Assumption: both accepted; earliest and latest are printed as they appear in the input.
4. **A4 Null definition:** Is null only an empty or whitespace-only field, or also tokens such as `NA`, `NULL`, `NaN`? Assumption: only empty or whitespace-only.
5. **A5 All-null columns:** What type should be reported? Assumption: `text`, unique count 0.
6. **A6 Quoted fields:** Should RFC 4180 quoting be supported? Assumption: yes.
7. **A7 Ragged rows:** Short rows are padded with nulls; long rows are a fatal error. Assumption as stated in FR-20.
8. **A8 Time limit:** Is 120 s for 100 MB acceptable? The story gives no time target. Assumption: yes.
9. **A9 Report format:** Is there a required layout? Assumption: free-form human-readable plain text; only the content in the story is mandated, and "No data rows found" is exact.
10. **A10 Python version:** Which minimum version? Assumption: 3.10.
11. **A11 Dependencies:** May third-party libraries (e.g. pandas) be used? Assumption: no, standard library only.
12. **Unique counting memory:** A text column with many distinct values in a 100 MB file could consume significant memory. Assumption: exact unique counts are required and fit within 512 MB for the 100 MB test file; approximate counting is not used.
13. **Numeric edge cases:** Should `NaN`, `inf`, and hex values count as numeric? Assumption: no, they make the column text.
14. **Mean precision:** Number of decimals for the mean and float display? Assumption: up to 4 decimal places.
15. **Leading-zero and ID-like values** (e.g. `007`): numeric or text? Assumption: numeric (no special handling).
