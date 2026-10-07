# Agentic SDLC Pipeline

## What This Is

A Claude Code-native pipeline that takes any Python project user story and drives it through the full software development lifecycle — requirements, architecture, implementation, testing, code review, and a GitHub PR — entirely via Claude agents. You describe what you want to build; the pipeline does the rest.

---

## Quick Start

1. **Clone the repo** (or use an existing copy)
2. **Add a user story** — copy `user-stories/user-story-template.md` to `user-stories/user-story-<n>.md` and fill it in
3. **Invoke the orchestrator**:
   ```
   claude --agent orchestrator
   > process user-stories/user-story-1.md
   ```
4. **Follow the prompts** — the pipeline will ask clarifying questions during Requirements and Architecture, then run autonomously and ask for approval at each subsequent step

---

## Pipeline Architecture

```
user-stories/user-story-N.md
        │
        ▼
[ORCHESTRATOR]
        │
        ├─[L1]─► Requirements ──────────────► docs/requirements.md
        │
        ├─[L1]─► Architecture ──────────────► docs/architecture.md
        │
        ├─[L2]─► Design Review ─────────────► docs/design-review.md
        │
        ├─[L2]─► Implementation Planner ────► docs/impl-plan.md
        │
        ├─[L2]─► Implementation ────────────► src/ + tests/
        │
        ├─[L2]─► Code Review ───────────────► output/reports/
        │
        ├─[L2]─► Verification ──────────────► output/test-results/
        │
        ├─[L2]─► Documentation Sync ────────► docs/ (updated)
        │
        └─[L3]─► PR ────────────────────────► GitHub Pull Request
```

---

## Folder Structure

```
agentic-sdlc-pipeline/
├── .claude/
│   ├── agents/          # 9 specialist agents + orchestrator
│   ├── skills/          # reusable skill files
│   └── settings.json    # hooks configuration
├── user-stories/        # input: one .md file per pipeline run
├── docs/                # generated requirements, architecture, etc.
├── src/                 # generated Python source code
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── output/
│   ├── reports/         # code review output (gitignored)
│   └── test-results/    # test run output (gitignored)
├── CLAUDE.md
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Agent Reference

| Agent | Role | Interaction Level |
|---|---|---|
| orchestrator | Entry point; drives the full pipeline | — |
| requirements | Elicits and documents requirements | L1 (interactive) |
| architecture | Proposes system design | L1 (interactive) |
| design-review | Reviews architecture for risks | L2 (run + approve) |
| implementation-planner | Ordered task breakdown | L2 (run + approve) |
| implementation | Writes Python source + tests | L2 (run + approve) |
| code-review | Reviews code quality and security | L2 (run + approve) |
| verification | Runs tests, reports results | L2 (run + approve) |
| documentation-sync | Keeps docs in sync with code | L2 (run + approve) |
| pr | Drafts and creates GitHub PR | L3 (explicit approve) |

---

## Requirements

- **Claude Code** — latest version with agent support
- **Python** ≥ 3.11
- **Git** and **GitHub CLI** (`gh`) — authenticated (`gh auth status`)
- No other API keys or external services required

---

## Contributing

**Adding a new agent**: Create `.claude/agents/<name>.md` with a clear system prompt, input/output contract, and tool list. Register it in the orchestrator's step sequence.

**Adding a new skill**: Create `.claude/skills/<name>/SKILL.md` with `name` and `description` frontmatter. Skills are invoked by agents using the `Skill` tool.
