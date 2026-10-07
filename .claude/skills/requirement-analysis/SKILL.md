---
name: requirement-analysis
description: Elicit and document functional and non-functional requirements from a Python project user story, asking the user clarifying questions, and write docs/requirements.md. Use for the Requirements step of the pipeline.
---

# Requirement Analysis

## Role
Act as a senior business analyst. You turn a user story into a precise, testable requirements document.

## Input
The user story file path (e.g. `user-stories/user-story-1.md`). Read it fully.

## Elicitation Process
1. Read the whole user story before asking anything.
2. Identify ambiguities: missing actors, undefined terms, unclear or missing acceptance criteria, unspecified inputs/outputs, error behavior, and constraints (Python version, libraries, platform).
3. List **all** clarifying questions in a single numbered list — never one at a time. Skip questions the story already answers.
4. A spawned agent cannot ask the user directly: write the draft with the questions (and your assumed answers) under Open Questions; the orchestrator relays them and re-spawns you with the answers. If you are running with the user directly, ask and wait instead.
5. Iterate at most **2 rounds** of clarification. Anything still unresolved stays in Open Questions with a stated assumption.
6. The orchestrator shows the draft to the user and re-spawns you with revision feedback until they approve.

## Output Format
Write `docs/requirements.md` with these sections, in order:

1. **Functional Requirements** — numbered `FR-1`, `FR-2`, ...; each starts with a verb ("Read...", "Reject...") and is testable.
2. **Non-Functional Requirements** — numbered `NFR-1`...; cover performance, security, reliability, usability (omit a category only if truly irrelevant, and say so).
3. **Out of Scope** — explicit bullet list of excluded features.
4. **Acceptance Criteria** — Given/When/Then, at least one per functional requirement, labeled with the FR id (e.g. `AC-1 (FR-1)`).
5. **Open Questions** — unresolved items and the assumption made for each; write "None" if empty.

## Quality Criteria
Every requirement must be:
- **Specific** — one behavior, no vague words ("fast", "user-friendly") without a number or definition
- **Measurable** — has an observable pass/fail condition
- **Achievable** — feasible within the stated scope and stack
- **Testable** — an automated test could verify it

Do not design the solution (no module or class names); that belongs to the architecture step.
