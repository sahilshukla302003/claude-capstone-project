---
name: implementation-planning
description: Break an approved architecture into a dependency-ordered task list with complexity estimates and write docs/impl-plan.md. Use for the Implementation Planning step of the pipeline.
---

# Implementation Planning

## Role
Act as a senior engineering lead doing sprint planning.

## Input
`docs/architecture.md` and `docs/design-review.md`. Incorporate any review recommendations that were accepted.

## Planning Process
1. List all implementation tasks; one task = one cohesive unit of work.
2. Identify dependencies (Task B cannot start until Task A is done).
3. Order tasks by dependency (topological sort); no cycles.
4. Estimate complexity per task: **S** / **M** / **L**.
5. Flag tasks blocked on external factors (credentials, access, decisions).

## Output Format
Write `docs/impl-plan.md` with:

1. **Task Table** — columns: `ID | Task Name | Description | Depends On | Complexity | File(s) Affected`
2. **Dependency Graph** — ASCII.
3. **Blocked Tasks** — list with the blocker, or "None".
4. **Definition of Done** — criteria for the full implementation (all tasks complete, tests pass, coverage ≥ 80%, no open Critical review findings).

## Rules
- Each task must produce runnable, testable code.
- Pair a test task with every implementation task (same row or an adjacent `T<n>-test` row), naming the test file under `tests/`.
- No task larger than one day of focused work — split L tasks that exceed it.
- Every component in the architecture must be covered by at least one task.
