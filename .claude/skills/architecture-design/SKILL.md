---
name: architecture-design
description: Design a high-level Python system architecture (components, data flow, tech choices, security) from docs/requirements.md and write docs/architecture.md. Use for the Architecture step of the pipeline.
---

# Architecture Design

## Role
Act as a senior Python software architect.

## Input
`docs/requirements.md`. Read it fully. If `docs/design-review.md` exists with blockers (feedback loop), address each blocker and note how in the document.

## Design Process
1. Identify all system components needed to satisfy the requirements.
2. Map data flow between components, from input to output.
3. Choose the technology stack — Python stdlib first; add a third-party package only with a written justification.
4. Identify external dependencies and integration points (APIs, files, services, storage).
5. Note scalability and security considerations.
6. Trace every functional requirement to at least one component.

## Clarification Rule
If a requirement is ambiguous, list the question under Open Design Questions with the assumption you used, all in one numbered list. A spawned agent cannot ask the user directly: the orchestrator relays the questions, then re-spawns you with the answers so you can finalize. If you are running with the user directly, ask and wait instead.

## Output Format
Write `docs/architecture.md` with these sections, in order:

1. **System Overview** — 2-3 sentences.
2. **Component Diagram** — ASCII art showing components and connections.
3. **Component Descriptions** — for each: name, responsibility, public interfaces (function/class signatures with types), and the FRs it satisfies.
4. **Data Flow** — step-by-step narrative.
5. **Technology Choices** — each choice with its justification.
6. **External Dependencies** — APIs, services, storage, third-party packages (with version constraints).
7. **Security Considerations** — input validation, secrets handling, file/path safety.
8. **Open Design Questions** — unresolved items; "None" if empty.

## Quality Criteria
- Every component has a single, clear responsibility.
- Interfaces are concrete enough to implement and test against.
- No component or dependency exists that no requirement needs.
