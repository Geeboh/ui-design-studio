---
name: ui-yolo
description: Run the complete UI Design Studio lifecycle autonomously, choosing visual concepts, approving reviewed mockups, naming the theme and directing implementation through final packaging. Use when the user explicitly delegates design choices in yolo mode.
---

# Autonomous UI Design Studio

Use this wrapper only when the user explicitly delegates cosmetic and interaction
choices. Load the [director](../ui-design-studio/SKILL.md), resolve the requested
scope, and execute the smallest applicable phase sequence in `mode=yolo`.

## Contract

Trigger: explicit yolo authorization for autonomous cosmetic decisions.
Minimum inputs: resolved context, requested scope, host constraints and run state.
Task contract: choose and execute only the authorized lifecycle phases.
Outputs: agent-owned decisions, bounded artifacts and current verification evidence.
Gate: the director's full or scoped contract, with no human-approval impersonation.
Escalate: unavailable host, failed mandatory check or unsafe authorization boundary.

- Preserve project instructions, Git policy, task tracking, model policy, offline
  requirements, runtime permissions and all quality gates.
- Read [project context](../ui-design-studio/references/project-context.md),
  [workflow](../ui-design-studio/references/workflow.md), [decisions](../ui-design-studio/references/decisions.md)
  and [multi-agent guidance](../ui-design-studio/references/multi-agent.md).
- Record every autonomous visual choice with actor `agent-yolo`, rationale and
  artifact identities. Never label it as user approval.
- Keep workers bounded by owned files. Give each worker applicable original
  instructions and the resolved model assignment. Use a different reviewer.
- Continue safe work through finalization. A blocked check, missing host or
  unavailable provider remains blocked. It never becomes a pass.
- Scoped completion never authorizes full-theme registration or default changes.
- Restore temporary routing, refresh its digest, clean up owned dashboard processes,
  retain evidence and report package, rollback, verification and limitations.

## Phase sequence

`full-redesign` uses Assess, Plan, Design, Produce, Review and Finalize.
`fix`, `component`, `single-flow` and `reference-adaptation` use only the phases
required by their scope. `assess-only` and `design-only` stop before application
changes. Use `ui_design_read_guide` for MCP-hosted guides; OMP reads bundled files.

Yolo chooses among concepts under the documented rubric and independent critique.
It does not disable approval provenance, fabricate evidence, deploy, change user
settings or authorize unrelated work. Human visual review, usability studies,
physical-device acceptance and release sign-off remain `DEFERRED_UAT`.
