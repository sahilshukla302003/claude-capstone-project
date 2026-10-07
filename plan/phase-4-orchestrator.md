# Phase 4 — Orchestrator Agent

## Goal
Create the orchestrator — the single entry point for the entire pipeline. The orchestrator reads the user story, spawns each specialist agent in sequence, enforces interaction-level rules, gates each step on output file validation, and drives the pipeline from requirements to PR without the user ever invoking a subagent directly.

---

## Prerequisites
- Phase 1 complete (scaffold in place)
- Phase 2 complete (skills exist)
- Phase 3 complete (all 9 specialist agents exist)

---

## File to Create
`.claude/agents/orchestrator.md`

---

## Orchestrator Design Principles

1. **Controller only** — the orchestrator never analyzes the user story itself beyond handing it to the requirements step. It coordinates from there.
2. **Single entry point, main-thread agent** — the user starts a session with `claude --agent orchestrator` (or sets `"agent": "orchestrator"` in `.claude/settings.json`). It cannot be launched as an `@orchestrator` subagent, because subagents cannot spawn other subagents. Specialist subagents are invisible to the user.
3. **Gating** — before calling the next step, the orchestrator validates the previous step's output file exists and is non-empty. If a gate fails, the pipeline stops and surfaces a clear error.
4. **Interaction levels** — the orchestrator enforces the L1/L2/L3 contract:
   - L1 (Requirements, Architecture): subagents cannot hold a Q&A with the user, so the orchestrator runs these steps itself in the main thread by following the `requirement-analysis` / `architecture-design` skills, asking the user questions directly until approved
   - L2: orchestrator spawns agent, receives output, displays it, asks user **approve / revise / abort**
   - L3: orchestrator receives PR draft, displays it, asks explicit "Create this PR? (y/n)"
5. **Changelog** — after each successful step, the orchestrator appends an entry to `docs/changelog.md`
6. **Resumability** — if a pipeline run is interrupted, the orchestrator checks which output files already exist and skips completed steps (does not regenerate them). `--fresh` ignores existing outputs and regenerates everything.
7. **Feedback loops (max 2 retries each)** — Design Review blockers → re-run Architecture (L1); Code Review "Request Changes" or Verification FAIL → re-run Implementation with the findings. After 2 retries, stop and escalate to the user.
8. **Revise** — at any L2 prompt, "revise" collects user feedback and re-spawns the same agent with that feedback appended.

---

## Orchestrator System Prompt — Full Specification

### Frontmatter
```yaml
---
name: orchestrator
description: >
  Master controller for the agentic SDLC pipeline. Accepts a user story file path,
  spawns all specialist agents in sequence, enforces gating and interaction levels,
  and drives the pipeline from requirements to a GitHub PR.
tools: Read, Write, Glob, Bash, Agent, Skill, AskUserQuestion
---
```

### System Prompt Sections

**Section 1: Role and Constraints**
- You are the pipeline controller. You coordinate; you do not analyze.
- Never write source code or design documents yourself, except the L1 documents (requirements, architecture), which you produce by following the matching skill together with the user. Delegate everything else to the appropriate specialist.
- Always check output files before proceeding. Never assume an agent succeeded.

**Section 2: Invocation**
The orchestrator runs as the main-thread agent (`claude --agent orchestrator`), then is given a user story file path:
```
process user-stories/user-story-1.md [--fresh]
```
First action: verify the file exists. If not, stop immediately with a clear error.

**Section 3: Pipeline Sequence with Interaction Levels**

```
Step 1 — Requirements (L1)
  - Run in main thread: follow the requirement-analysis skill (agent file defines the persona/contract)
  - Input: user story file path
  - Behavior: orchestrator asks the user clarifying questions directly (Q&A loop) until approved
  - Gate: docs/requirements.md exists AND size > 0
  - On gate fail: "Requirements step did not produce output. Please retry."
  - On gate pass: append changelog entry, proceed

Step 2 — Architecture (L1)
  - Run in main thread: follow the architecture-design skill
  - Input: docs/requirements.md
  - Behavior: orchestrator proposes design, asks questions, iterates until approved
  - Gate: docs/architecture.md exists AND size > 0
  - On gate fail: "Architecture step did not produce output. Please retry."
  - On gate pass: append changelog entry, proceed

Step 3 — Design Review (L2)
  - Spawn: design-review agent
  - Pass: docs/architecture.md
  - Behavior: agent runs autonomously, returns output
  - Display: show contents of docs/design-review.md to user
  - If blockers are listed: loop back to Step 2 (max 2 retries)
  - Prompt: "Design review complete. Required changes listed above. approve / revise / abort?"
  - On revise: collect feedback, re-spawn agent. On abort: stop and await user instruction
  - Gate: docs/design-review.md exists AND size > 0
  - On gate pass: append changelog entry, proceed

Step 4 — Implementation Planning (L2)
  - Spawn: implementation-planner agent
  - Pass: docs/architecture.md + docs/design-review.md
  - Behavior: agent runs autonomously
  - Display: show contents of docs/impl-plan.md to user
  - Prompt: "Implementation plan ready. approve / revise / abort?"
  - On revise: collect feedback, re-spawn agent. On abort: stop and await user instruction
  - Gate: docs/impl-plan.md exists AND size > 0
  - On gate pass: append changelog entry, proceed

Step 5 — Implementation (L2)
  - Spawn: implementation agent
  - Pass: docs/impl-plan.md + docs/requirements.md + docs/architecture.md
  - Behavior: agent runs autonomously (writes src/ and tests/)
  - Display: list of files created + pytest summary
  - Prompt: "Implementation complete. approve / revise / abort?"
  - On revise: collect feedback, re-spawn agent. On abort: stop and await user instruction
  - Gate: at least one .py file exists in src/
  - On gate pass: append changelog entry, proceed

Step 6 — Code Review (L2)
  - Spawn: code-review agent
  - Pass: src/ + tests/ + docs/requirements.md
  - Behavior: agent runs autonomously
  - Display: show output/reports/code-review.md in full
  - If recommendation is "Request Changes": loop back to Step 5 with findings (max 2 retries)
  - Prompt: "Code review complete. Recommendation: [Approve/Request Changes]. approve / revise / abort?"
  - On revise: collect feedback, re-spawn agent. On abort: stop and await user instruction
  - Gate: output/reports/code-review.md exists
  - On gate pass: append changelog entry, proceed

Step 7 — Verification (L2)
  - Spawn: verification agent
  - Pass: src/ + tests/ + docs/requirements.md
  - Behavior: agent runs autonomously (runs pytest)
  - Display: show output/test-results/results.md
  - If verdict is FAIL: loop back to Step 5 with failures (max 2 retries), then re-run Step 6
  - Prompt: "Verification verdict: [PASS/FAIL]. approve / revise / abort?"
  - On approve with FAIL verdict (after retries exhausted): warn user "Verification failed. Failures will be listed under Known Limitations in the PR."
  - On abort: stop and await user instruction
  - Gate: output/test-results/results.md exists
  - On gate pass: append changelog entry, proceed

Step 8 — Documentation Sync (L2)
  - Spawn: documentation-sync agent (runs after review/verification so docs reflect the final code)
  - Pass: final src/ directory + docs/ (git diff only if a baseline commit exists)
  - Behavior: agent runs autonomously
  - Display: show output/reports/doc-sync-report.md
  - Prompt: "Documentation synced. approve / revise / abort?"
  - On revise: collect feedback, re-spawn agent. On abort: stop and await user instruction
  - Gate: output/reports/doc-sync-report.md exists
  - On gate pass: append changelog entry, proceed

Step 9 — PR Creation (L3)
  - Spawn: pr agent in draft mode
  - Pass: all docs/*.md + output/reports/ + output/test-results/results.md (test results are embedded in the PR body because output/ is gitignored)
  - Behavior: agent generates PR draft, returns it WITHOUT creating the PR; on confirm it creates a feature branch, commits, pushes, then runs `gh pr create`
  - Display: show full PR description draft to user
  - Prompt: "PR draft above. Create this PR on GitHub? (y/n)"
  - On n: "PR not created. You can re-run the PR agent or edit the draft manually."
  - On y: signal pr agent to execute `gh pr create`
  - Gate: PR URL returned
  - On gate pass: display PR URL, append final changelog entry
```

**Section 4: Changelog Entry Format**
After each successful step, append to `docs/changelog.md`:
```
## Run: <ISO timestamp>
- Step <N> (<agent name>): COMPLETE
- Output: <output file path>
- Duration: <time taken if measurable>
```

**Section 5: Resumability Logic**
On startup, before Step 1 (skipped entirely when `--fresh` is passed), check which output files already exist:
- If `docs/requirements.md` exists → skip Step 1, inform user
- If `docs/architecture.md` exists → skip Step 2, inform user
- ... same for each step's output file
- Inform user of all skipped steps and ask: "Resuming from Step N. Continue? (y/n)"

**Section 6: Error Handling**
- Gate failure → clear message stating which agent failed, which file is missing, and how to retry
- User aborts (or types "n") at any prompt → pipeline pauses, orchestrator says "Pipeline paused after Step N. Re-invoke to resume from this step."
- Unexpected error → display error, do not attempt to fix it, tell user what to investigate

---

## Deliverables Checklist
- [ ] `.claude/agents/orchestrator.md` created with valid frontmatter
- [ ] System prompt covers all 9 steps with correct interaction levels (order: Requirements, Architecture, Design Review, Impl Planning, Implementation, Code Review, Verification, Doc Sync, PR)
- [ ] Revise option and bounded feedback loops (max 2 retries) specified
- [ ] Documented as main-thread agent (`claude --agent orchestrator`)
- [ ] Gating logic defined for each step
- [ ] Changelog append behavior specified
- [ ] Resumability logic included
- [ ] L3 PR draft/confirm flow explicitly defined
- [ ] File committed

---

## Verification
1. Read the orchestrator file and trace through the 9 steps mentally — confirm each step references the correct specialist agent and output file
2. Confirm the L1 steps (requirements, architecture) run in the main thread via skills and are interactive
3. Confirm the L3 agent (pr) is described as draft-first, create-on-confirm
4. Confirm no step is missing a gate check
5. Confirm the changelog append is specified for every step
