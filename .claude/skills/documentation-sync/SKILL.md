---
name: documentation-sync
description: Update docs/*.md so they match the final implemented source code, and produce a sync report of what changed. Use for the Documentation Sync step of the pipeline.
---

# Documentation Sync

## Role
Act as a technical writer reviewing code changes.

## Input
The contents of `src/` and the existing `docs/*.md` files. Use `git diff` only if a baseline commit exists; otherwise compare the code directly against the docs.

## Sync Process
1. Read the current code and the docs.
2. Identify drift: new functions/classes not documented, removed ones still referenced, changed signatures, new or removed dependencies, changed data flow.
3. Update only the affected sections in the relevant `docs/*.md` file.
4. Leave sections that are still accurate untouched.

## Output
- In-place updates to the affected `docs/*.md` files.
- A sync report (returned to the orchestrator) listing each file and section changed, and why. If nothing needed changing, say so.

## Rules
- Never delete documented design decisions — update them.
- Mark deprecated or removed items `[DEPRECATED]` instead of deleting them.
- Keep docs concise; do not pad with obvious information.
- Do not edit `docs/changelog.md` — the orchestrator and hooks own it.
