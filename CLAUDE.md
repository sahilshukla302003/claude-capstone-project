# Agentic SDLC Pipeline

## Project Overview

This repo contains a Claude Code-native agentic pipeline that accepts any Python project user story and drives it through the full software development lifecycle — from requirements through a GitHub PR — entirely via Claude agents, skills, and hooks. You interact only with the orchestrator; it spawns and gates all specialist agents.

---

## How to Run the Pipeline

Invoke the orchestrator with a user story path:

```
@orchestrator process user-stories/<filename>.md
```

The orchestrator verifies the file exists, then checks which gate files already exist (resumability). If any steps are complete it lists them and asks `Continue? (y/n)` before resuming from the next incomplete step. To regenerate an artifact, delete its gate file before re-invoking.

**You never invoke specialist subagents directly.**

---

## Pipeline Phases

The orchestrator executes these 9 steps in order:

1. **Requirements** (`requirements`) — Documents functional/non-functional requirements from the user story. Output: `docs/requirements.md`
2. **Architecture** (`architecture`) — Proposes system components, interfaces, and data flow. Output: `docs/architecture.md`
3. **Design Review** (`design-review`) — Reviews the architecture for risks and gaps. Output: `docs/design-review.md`
4. **Implementation Planning** (`implementation-planner`) — Dependency-ordered task breakdown. Output: `docs/impl-plan.md`
5. **Implementation** (`implementation`) — Writes Python source and tests. Output: `src/**/*.py`, `tests/**/*.py`
6. **Documentation Sync** (`documentation-sync`) — Updates docs to match the implemented code. Output: `output/reports/doc-sync-report.md` and updated `docs/` files
7. **Code Review** (`code-review`) — Reviews source and tests for correctness, security, and quality. Output: `output/reports/code-review.md`
8. **Verification** (`verification`) — Runs the test suite and reports PASS/FAIL. Output: `output/test-results/results.md`
9. **PR** (`pr`) — Drafts a GitHub Pull Request, and creates it only after explicit user confirmation.

---

## Interaction Levels

| Level | Steps | Behavior |
|---|---|---|
| L1 — Deep Interactive | Requirements, Architecture | The agent interacts with you directly (clarifying questions, iteration) until it writes its document, then returns control to the orchestrator |
| L2 — Run + Approve | Design Review, Impl Planner, Implementation, Doc Sync, Code Review, Verification | Agent runs autonomously; orchestrator displays the output and asks **y/n** to continue. `n` pauses the pipeline; re-invoke to resume |
| L3 — Explicit Approve | PR | Agent returns a full PR draft without creating it; the PR is created only after you answer **y** |

**Gating**: before each step the orchestrator verifies input files exist; after each step it verifies the gate file exists and is non-empty. A failed gate stops the pipeline with the name of the failing agent and file.

**Verification failure**: a FAIL verdict does not block the pipeline if you answer `y`, but the orchestrator warns you and the failures should be documented in the PR's Known Limitations section.

**No automatic feedback loops**: review findings and failures are surfaced to you; re-invoke to rerun a step.

After each successful step the orchestrator appends an entry to `docs/changelog.md` (never overwriting it).

---

## File Conventions

| Path | Purpose |
|---|---|
| `user-stories/*.md` | Input user stories — one per pipeline run |
| `docs/requirements.md` | Generated requirements artifact |
| `docs/architecture.md` | Generated architecture artifact |
| `docs/design-review.md` | Generated design review artifact |
| `docs/impl-plan.md` | Generated implementation plan |
| `docs/changelog.md` | Auto-appended run log |
| `src/` | Generated Python source code |
| `tests/` | Generated tests (unit/, integration/, fixtures/) |
| `output/reports/` | Code review and doc-sync reports (gitignored) |
| `output/test-results/` | Test results (gitignored) |

User story filenames must follow the pattern `user-story-<n>.md`.

---

## Do Not

- **Never invoke specialist subagents directly** — always go through the orchestrator
- **Never skip gating checks** — each step must produce a non-empty output file before the next step runs
- **Never create the PR without explicit user confirmation** — the PR step is L3
- **Never overwrite `docs/changelog.md`** — append only
- **Never commit `output/`** — it is gitignored by design
