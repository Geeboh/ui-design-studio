---
name: ui-review
description: Independently review UI concepts, complete mockups or implemented pages against their requirements, accessibility, coverage and performance evidence. Use for review only; this specialist does not silently repair, approve missing evidence or initiate a redesign.
---

# Review UI quality independently

Review the requested artifact or phase only. Keep changes read-only unless the user explicitly asks for fixes.

Resolve or refresh the [project context](../ui-design-studio/references/project-context.md) for this scope. Use the selected run's model policy, or `models=auto-models` by default for a new run; honor `models=current-model` when requested. Follow [model routing](../ui-design-studio/references/model-routing.md) before delegation. These settings do not expand this phase's scope.

1. Read the [workflow](../ui-design-studio/references/workflow.md), [quality gates](../ui-design-studio/references/quality-gates.md), [visual system](../ui-design-studio/references/visual-system.md) and [multi-agent guidance](../ui-design-studio/references/multi-agent.md).
2. Read applicable project instructions, brief, findings, required coverage, approved decisions and the actual artifact revision. Determine what kind of review is possible; a mockup cannot prove runtime behavior.
3. Use a reviewer who did not author the relevant work. If independent execution is unavailable, disclose that limitation and never label self-review independent.
4. Inspect raw artifacts, diffs and rendered output. Exercise task journeys, error recovery, keyboard/focus behavior, labels, contrast, responsive layouts and meaningful state changes where applicable.
5. Reconcile required surfaces/states with supplied evidence. Check offline conditions, payload/runtime measurements and source identity. Identify unrun checks rather than inferring a pass.
6. Compare implementation with approved intent, explaining intentional differences. Check that style changes preserve data meaning, permissions and application state.
7. Report findings with severity, evidence, reproduction, affected IDs and acceptance conditions. Separate observed defects, expert judgments and unavailable verification.
8. Return approve, request changes or blocked using the project's current record format. Yolo may delegate design judgment, but cannot waive failed required checks. Do not fabricate human approval.
9. Finish with the exact review scope, evidence and limitations; route remediation to the responsible owner.
