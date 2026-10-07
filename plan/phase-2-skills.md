# Phase 2 — Skills

## Goal
Create 6 reusable Claude Code skill files under `.claude/skills/`. Skills are structured prompt templates that agents invoke when they need to perform a specific type of analysis or generation. They are not agents themselves — they are helpers that give agents a repeatable, consistent method for doing their core task.

---

## Prerequisites
- Phase 1 complete (repo scaffold in place)
- `.claude/skills/` directory exists

---

## What Is a Claude Code Skill?
A skill is a directory `.claude/skills/<skill-name>/` containing a `SKILL.md` file with `name` and `description` YAML frontmatter; Claude Code discovers it by that structure and loads it when an agent (or the user) invokes it by name. Flat `.claude/skills/<name>.md` files are not discovered. The `SKILL.md` provides:
- A structured prompt template
- Step-by-step instructions for how to perform the task
- Output format specification
- Quality criteria

Agents reference skills in their system prompts: "Use the `requirement-analysis` skill to elicit and document requirements."

---

## Skills to Create

### Skill 1 — `requirement-analysis/SKILL.md`
**Purpose**: Guide an agent through structured requirements elicitation from a user story.

**Sections to include:**
1. **Role** — Act as a senior business analyst
2. **Input** — User story text
3. **Elicitation Process**:
   - Read the user story fully before asking anything
   - Identify ambiguities: missing actors, undefined terms, unclear acceptance criteria
   - Ask all clarifying questions in a single numbered list (not one at a time)
   - Wait for user answers before proceeding
   - Iterate maximum 2 rounds of clarification
4. **Output Format** — structured `requirements.md` with:
   - Functional Requirements (numbered, verb-first, testable)
   - Non-Functional Requirements (performance, security, reliability, usability)
   - Out of Scope (explicit list of excluded features)
   - Acceptance Criteria (Given/When/Then per functional requirement)
   - Open Questions (anything still unresolved)
5. **Quality Criteria** — each requirement must be: specific, measurable, achievable, testable

---

### Skill 2 — `architecture-design/SKILL.md`
**Purpose**: Guide an agent through designing a high-level system architecture for a Python project.

**Sections to include:**
1. **Role** — Act as a senior Python software architect
2. **Input** — `docs/requirements.md`
3. **Design Process**:
   - Identify all system components from the requirements
   - Map data flow between components
   - Choose technology stack (Python stdlib first, third-party only if justified)
   - Identify external dependencies and integration points
   - Note scalability and security considerations
4. **Output Format** — structured `architecture.md` with:
   - System Overview (2-3 sentences)
   - Component Diagram (ASCII art)
   - Component Descriptions (name, responsibility, interfaces)
   - Data Flow (step-by-step narrative)
   - Technology Choices (with justification for each)
   - External Dependencies (APIs, services, storage)
   - Security Considerations
   - Open Design Questions
5. **Clarification Rule** — if a requirement is ambiguous, ask the user before designing around an assumption

---

### Skill 3 — `implementation-planning/SKILL.md`
**Purpose**: Break an approved architecture into an ordered, dependency-aware task list.

**Sections to include:**
1. **Role** — Act as a senior engineering lead doing sprint planning
2. **Input** — `docs/architecture.md` + `docs/design-review.md`
3. **Planning Process**:
   - List all implementation tasks (one task = one cohesive unit of work)
   - Identify dependencies between tasks (Task B cannot start until Task A is done)
   - Order tasks by dependency (topological sort)
   - Estimate complexity per task: S / M / L
   - Flag any tasks that are blocked on external factors
4. **Output Format** — structured `impl-plan.md` with:
   - Task table: ID | Task Name | Description | Depends On | Complexity | File(s) Affected
   - Dependency graph (ASCII)
   - Blocked tasks section (if any)
   - Definition of Done for the full implementation
5. **Rules**:
   - Each task must result in runnable, testable code
   - Test tasks must be paired with each implementation task
   - No task should be larger than "1 day of focused work"

---

### Skill 4 — `documentation-sync/SKILL.md`
**Purpose**: Keep `docs/` files in sync with the actual source code after implementation.

**Sections to include:**
1. **Role** — Act as a technical writer reviewing code changes
2. **Input** — `src/` directory contents + existing `docs/` files
3. **Sync Process**:
   - Diff the current code against what the docs describe
   - Identify: new functions/classes not documented, removed functions still referenced, changed signatures, new dependencies
   - Update affected sections in the relevant docs file
   - Do not rewrite sections that are still accurate
4. **Output** — in-place updates to affected `docs/*.md` files + a sync report listing what changed
5. **Rules**:
   - Never delete documented design decisions, only update them
   - Mark deprecated items as `[DEPRECATED]` rather than deleting
   - Keep docs concise — do not pad with obvious information

---

### Skill 5 — `pipeline-code-review/SKILL.md`
**Purpose**: Perform a structured code review against a defined checklist.

**Review Areas and Questions:**

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

**Output Format** — `output/reports/code-review.md` with:
- Summary (pass / fail / needs-changes)
- Finding per area: Severity (Critical / Major / Minor) | File | Line | Description | Suggestion
- Overall recommendation: Approve / Request Changes

**Rules**:
- Only report actual findings, not hypothetical issues
- Severity = Critical if it would break functionality or expose a security risk
- Always check `docs/requirements.md` — review against spec, not against assumptions

---

### Skill 6 — `verification/SKILL.md`
**Purpose**: Run the test suite, validate output quality, and produce a structured results report.

**Sections to include:**
1. **Role** — Act as a QA engineer running final acceptance testing
2. **Input** — `src/` + `tests/` + `docs/requirements.md`
3. **Verification Steps**:
   - Step 1: Run unit tests (`pytest tests/unit/ -v`)
   - Step 2: Run integration tests (`pytest tests/integration/ -v`)
   - Step 3: Check test coverage (`pytest --cov=src --cov-report=term-missing`)
   - Step 4: Validate each acceptance criterion from `docs/requirements.md` is covered by at least one test
   - Step 5: Check for any requirements with zero test coverage (flag as gap)
4. **Output Format** — `output/test-results/results.md` with:
   - Test Run Summary: total / passed / failed / skipped
   - Coverage Report: overall % + per-module breakdown
   - Acceptance Criteria Coverage: table mapping each criterion to its test(s)
   - Gaps: any requirement with no test coverage
   - Final Verdict: PASS / FAIL
5. **Pass Criteria**: All unit tests pass, integration tests pass, coverage ≥ 80%, no Critical findings from code review open

---

## Deliverables Checklist
- [ ] `.claude/skills/requirement-analysis/SKILL.md`
- [ ] `.claude/skills/architecture-design/SKILL.md`
- [ ] `.claude/skills/implementation-planning/SKILL.md`
- [ ] `.claude/skills/documentation-sync/SKILL.md`
- [ ] `.claude/skills/pipeline-code-review/SKILL.md`
- [ ] `.claude/skills/verification/SKILL.md`
- [ ] All 6 files committed

---

## Verification
Each skill file should be readable as a standalone document — an agent should be able to follow it without needing additional context. Spot-check: confirm each skill appears in Claude Code's skill list (name + description frontmatter present), then read `pipeline-code-review/SKILL.md` and confirm the review checklist covers all 8 areas defined in the project plan.
