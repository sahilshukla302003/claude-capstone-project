#!/bin/bash
# PreToolUse / Agent: log each subagent spawn to docs/changelog.md. Never blocks.
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
AGENT_NAME=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('subagent_type') or d.get('tool_input',{}).get('description','unknown'))" 2>/dev/null || echo "unknown")
mkdir -p docs
echo "" >> docs/changelog.md
echo "### $TIMESTAMP — Spawning agent: $AGENT_NAME" >> docs/changelog.md
exit 0
