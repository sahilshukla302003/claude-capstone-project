---
name: code-review
description: Perform a structured code review of src/ and tests/ against an 8-area checklist and the requirements spec, writing output/reports/code-review.md. Use for the Code Review step of the pipeline.
---

# Code Review

## Role
Act as a senior Python reviewer. Review against the spec, not against assumptions.

## Input
`src/`, `tests/`, and `docs/requirements.md` (always read the requirements first).

## Review Checklist

| Area | Question |
|---|---|
| Correctness | Does each component behave as specified in `docs/requirements.md`? |
| Security | Are secrets excluded from output? Is user input validated at all boundaries? |
| Error Handling | Are API failures, missing files, and edge cases handled gracefully? |
| Test Coverage | Do tests cover the happy path AND the key edge cases (Not Found, empty input, invalid format)? |
| Code Clarity | Are function names self-explanatory? Is logic followable without comments? |
| DRY Principle | Is there duplicated logic that should be refactored into a shared function? |
| Dependency Safety | Are all third-party packages pinned? Are there known-vulnerable versions? |
| Python Conventions | PEP8, type hints, no bare `except:`, no mutable default arguments |

## Output Format
Write `output/reports/code-review.md` with:

1. **Summary** — `pass`, `fail`, or `needs-changes`.
2. **Findings per area** — one section for each of the 8 areas, with a table: `Severity | File | Line | Description | Suggestion`. Write "No findings" for a clean area.
3. **Overall Recommendation** — `Approve` or `Request Changes`.

## Rules
- Report only actual findings, not hypothetical issues.
- Severity is **Critical** if it would break functionality or expose a security risk; **Major** for significant correctness/quality problems; **Minor** for style and polish.
- Any Critical finding means `Request Changes`.
- Cite file and line for every finding.
