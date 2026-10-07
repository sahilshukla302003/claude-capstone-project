# Phase 5 — Hooks

## Goal
Configure Claude Code hooks in `.claude/settings.json` to add automated behaviors around the pipeline: logging agent invocations, validating output file quality, and printing a pipeline summary when the orchestrator finishes. Hooks run outside the agent context — they are shell commands executed by the Claude Code harness, not by Claude itself.

---

## Prerequisites
- Phase 1 complete (`.claude/` directory exists)
- Phase 3 complete (agent files exist — hooks reference them by name)
- Phase 4 complete (orchestrator exists — Stop hook fires when it finishes)

---

## What Are Claude Code Hooks?
Hooks are shell commands defined in `.claude/settings.json` that fire on specific Claude Code events:

| Hook Type | Fires When |
|---|---|
| `PreToolUse` | Before Claude calls a tool (e.g., before spawning a subagent) |
| `PostToolUse` | After a tool call completes |
| `Stop` | When Claude finishes its turn (the session ends or Claude stops) |
| `Notification` | When Claude sends a notification to the user |

Hooks receive the event as a JSON object on **stdin** (fields such as `tool_name`, `tool_input`, `cwd`) — not via an environment variable. Hooks can:
- Log to files
- Validate outputs
- Block execution (exit code 2 = block + show message to Claude)
- Warn without blocking (exit code 0 with stderr output)

---

## Hooks to Configure

### Hook 1 — Agent Invocation Logger (`PreToolUse` on `Agent`)
**Purpose**: Log every subagent invocation to `docs/changelog.md` before it starts.

**Trigger**: `PreToolUse` when the tool name is `Agent`

**Shell command**:
```bash
#!/bin/bash
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
AGENT_NAME=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('subagent_type') or d.get('tool_input',{}).get('description','unknown'))" 2>/dev/null || echo "unknown")
mkdir -p docs
echo "" >> docs/changelog.md
echo "### $TIMESTAMP — Spawning agent: $AGENT_NAME" >> docs/changelog.md
```

**Notes**:
- The hook event JSON is read from stdin; the agent name is `tool_input.subagent_type` (falls back to `description`)
- Appends a timestamped entry to `docs/changelog.md` before the agent starts
- Never exits with code 2 (should never block)

---

### Hook 2 — Output File Validator (`PostToolUse` on `Write`)
**Purpose**: After any agent writes an output file, validate it is non-empty and warn if not.

**Trigger**: `PostToolUse` when the tool name is `Write`

**Shell command**:
```bash
#!/bin/bash
FILE_PATH=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")
# file_path is usually absolute; make it relative to the project dir
FILE_PATH="${FILE_PATH#$PWD/}"

# Only validate files in docs/ or output/
if [[ "$FILE_PATH" == docs/* ]] || [[ "$FILE_PATH" == output/* ]]; then
  if [ ! -s "$FILE_PATH" ]; then
    echo "WARNING: $FILE_PATH was written but is empty. The agent may have failed to produce output." >&2
  else
    LINES=$(wc -l < "$FILE_PATH")
    echo "OK: $FILE_PATH written ($LINES lines)" >&2
  fi
fi
```

**Notes**:
- Only checks files in `docs/` and `output/` — ignores `src/` and `tests/` writes
- Outputs to stderr (visible to Claude as a warning, not blocking)
- Does not exit 2 — validation warnings are surfaced, not blocking

---

### Hook 3 — Pipeline Summary Printer (`Stop`)
**Purpose**: When the pipeline finishes (the PR step has completed), print a summary of what was produced.

**Trigger**: `Stop`

**Shell command**:
```bash
#!/bin/bash
# Stop fires after every turn. Only print once the PR step has been logged as complete.
grep -q "Step 9 (pr): COMPLETE" docs/changelog.md 2>/dev/null || exit 0
echo ""
echo "========================================"
echo "  PIPELINE RUN SUMMARY"
echo "========================================"

check_file() {
  if [ -s "$1" ]; then
    echo "  [OK]  $1"
  else
    echo "  [--]  $1 (not produced)"
  fi
}

check_file "docs/requirements.md"
check_file "docs/architecture.md"
check_file "docs/design-review.md"
check_file "docs/impl-plan.md"
check_file "output/reports/doc-sync-report.md"
check_file "output/reports/code-review.md"
check_file "output/test-results/results.md"

SRC_COUNT=$(find src/ -name "*.py" 2>/dev/null | wc -l)
TEST_COUNT=$(find tests/ -name "*.py" 2>/dev/null | wc -l)
echo "  [SRC] $SRC_COUNT Python source files in src/"
echo "  [TST] $TEST_COUNT Python test files in tests/"

echo ""
if [ -s "output/test-results/results.md" ]; then
  VERDICT=$(grep -i "Final Verdict" output/test-results/results.md | tail -1)
  echo "  Verification: $VERDICT"
fi
echo "========================================"
```

**Notes**:
- `Stop` fires after every turn, so the script exits silently unless the orchestrator's final changelog entry (`Step 9 (pr): COMPLETE`) exists — keep the orchestrator's changelog format (Phase 4, Section 4) in sync with this grep
- Uses `find` and `grep` — safe, no side effects

---

## `.claude/settings.json` Structure

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Agent",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/log-agent-invocation.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/validate-output-file.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/print-pipeline-summary.sh"
          }
        ]
      }
    ]
  }
}
```

---

## Hook Script Files to Create
Store hook scripts in `.claude/hooks/` for clarity:

| Script | Hook Type | Purpose |
|---|---|---|
| `.claude/hooks/log-agent-invocation.sh` | PreToolUse / Agent | Log agent start to changelog |
| `.claude/hooks/validate-output-file.sh` | PostToolUse / Write | Warn on empty output files |
| `.claude/hooks/print-pipeline-summary.sh` | Stop | Print what was produced |

All scripts must:
- Start with `#!/bin/bash`
- Be executable (`chmod +x`)
- Never exit with code 2 (no blocking hooks in this pipeline — warnings only)
- Write informational output to stderr, not stdout (stdout is passed back to Claude)

---

## Deliverables Checklist
- [ ] `.claude/hooks/log-agent-invocation.sh` created and executable
- [ ] `.claude/hooks/validate-output-file.sh` created and executable
- [ ] `.claude/hooks/print-pipeline-summary.sh` created and executable
- [ ] `.claude/settings.json` created with all 3 hooks configured
- [ ] All files committed

---

## Verification
1. Open a Claude Code session in the project directory
2. Ask Claude to write a test file to `docs/test-hook.md`
3. Confirm the PostToolUse hook fires and prints "OK: docs/test-hook.md written"
4. Delete `docs/test-hook.md` after verification
5. Check `.claude/settings.json` is valid JSON: `python -m json.tool .claude/settings.json`
6. Confirm the Stop hook script runs without errors: `bash .claude/hooks/print-pipeline-summary.sh` (it prints nothing until the changelog contains `Step 9 (pr): COMPLETE`; append that line temporarily to test, then remove it)
7. Pipe a sample event into the logger to test stdin parsing: `echo '{"tool_input":{"subagent_type":"design-review"}}' | bash .claude/hooks/log-agent-invocation.sh`
