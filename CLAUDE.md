# Agentic SDLC Pipeline

## Project Overview

This repo contains a Claude Code-native agentic pipeline that accepts any Python project user story and drives it through the full software development lifecycle — from requirements through a merged GitHub PR — entirely via Claude agents, skills, and hooks. You interact only with the orchestrator; it manages all specialist agents internally.

---

## How to Run the Pipeline

The orchestrator must run as the main-thread agent. Subagents cannot spawn other subagents, so it cannot be started with `@orchestrator`.

```
claude --agent orchestrator
> process user-stories/<filename>.md
```

Add `--fresh` to regenerate all artifacts from scratch (existing outputs are otherwise skipped):

```
> process user-stories/<filename>.md --fresh
```

**You never invoke subagents directly.**

---

## Pipeline Phases

The orchestrator executes these 9 steps in order:

1. **Requirements** — Elicits and documents functional/non-functional requirements from the user story. Output: `docs/requirements.md`
2. **Architecture** — Proposes system components, interfaces, and data flow. Output: `docs/architecture.md`
3. **Design Review** — Reviews the architecture for risks, gaps, and scalability concerns. Output: `docs/design-review.md`
4. **Implementation Planning** — Produces a dependency-ordered task breakdown. Output: `docs/impl-plan.md`
5. **Implementation** — Writes all Python source files and tests. Output: `src/**/*.py`, `tests/**/*.py`
6. **Code Review** — Reviews source and tests for correctness, security, and quality. Output: `output/reports/code-review.md`
7. **Verification** — Runs the test suite and reports results. Output: `output/test-results/results.md`
8. **Documentation Sync** — Updates docs to match the final implemented code. Output: updated `docs/` files
9. **PR** — Drafts and creates a GitHub Pull Request after explicit user confirmation.

---

## Interaction Levels

| Level | Steps | Behavior |
|---|---|---|
| L1 — Deep Interactive | Requirements, Architecture | Runs in the orchestrator's main thread via skills so it can ask you clarifying questions directly; iterates until you approve |
| L2 — Run + Approve | Design Review, Impl Planner, Implementation, Code Review, Verification, Doc Sync | Subagent runs autonomously; orchestrator shows output and asks: **approve / revise (with feedback) / abort** |
| L3 — Explicit Approve | PR | Orchestrator shows full PR draft; only creates PR after your explicit confirmation |

**Feedback loops**: Design Review blockers return to Architecture; Code Review issues or failing Verification return to Implementation. Each loop is capped at 2 retries, then the orchestrator escalates to you.

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
| `output/reports/` | Code review report (gitignored) |
| `output/test-results/` | Test results (gitignored) |

User story filenames must follow the pattern `user-story-<n>.md`.

---

## Do Not

- **Never invoke subagents directly** — always go through the orchestrator
- **Never skip gating checks** — each step must produce a non-empty output file before the next step runs
- **Never create the PR without explicit user confirmation** — the PR step is L3
- **Never run `--fresh` automatically** — only when the user explicitly passes the flag
- **Never commit `output/`** — it is gitignored by design
