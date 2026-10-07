---
name: verification
description: Run the test suite with coverage, check every acceptance criterion has a test, and write output/test-results/results.md with a PASS/FAIL verdict. Use for the Verification step of the pipeline.
---

# Verification

## Role
Act as a QA engineer running final acceptance testing.

## Input
`src/`, `tests/`, `docs/requirements.md`, and `output/reports/code-review.md` (to check for open Critical findings).

## Verification Steps
1. Run unit tests: `pytest tests/unit/ -v`
2. Run integration tests: `pytest tests/integration/ -v`
3. Check coverage: `pytest --cov=src --cov-report=term-missing`
4. Validate each acceptance criterion in `docs/requirements.md` is covered by at least one test.
5. Flag any requirement with zero test coverage as a gap.

If pytest or pytest-cov is missing, report that as a failure with the exact error — do not fake results.

## Output Format
Write `output/test-results/results.md` with:

1. **Test Run Summary** — total / passed / failed / skipped (unit and integration separately).
2. **Coverage Report** — overall % and per-module breakdown, including missing lines.
3. **Acceptance Criteria Coverage** — table: `Criterion | Test(s)`.
4. **Gaps** — requirements with no test coverage, or "None".
5. **Final Verdict** — `PASS` or `FAIL`, with the reason for any failure.

## Pass Criteria
PASS only if all of:
- All unit tests pass
- All integration tests pass
- Coverage ≥ 80%
- No Critical code-review findings remain open
