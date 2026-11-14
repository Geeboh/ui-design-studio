---
name: ui-plan
description: Develop and compare coherent UI concepts, palettes, storyboards, SVG icons and component samples from an existing assessment and brief. Use for the Plan phase only; this specialist does not automatically implement the chosen design.
---

# Plan coherent visual directions

Perform the Plan phase only unless the user explicitly requests more.

## Phase contract

Trigger: a concept or visual-direction request after assessment.
Minimum inputs: resolved context, findings, brief and constraints.
Task contract: produce comparable directions against one shared brief.
Outputs: rendered concepts, visual rules, selection and approval digest.
Gate: guided user selection or independent `agent-yolo` decision.
Escalate: missing assessment, unusable host constraints or unresolved choice.

Resolve or refresh the [project context](../ui-design-studio/references/project-context.md) for this scope. Use the selected run's model policy, or `models=auto-models` by default for a new run; honor `models=current-model` when requested. Follow [model routing](../ui-design-studio/references/model-routing.md) before delegation. These settings do not expand this phase's scope.

1. Read the [workflow](../ui-design-studio/references/workflow.md), [visual system](../ui-design-studio/references/visual-system.md), [decisions](../ui-design-studio/references/decisions.md) and [multi-agent guidance](../ui-design-studio/references/multi-agent.md).
2. Read project instructions, config and the selected run's assessment, findings, inventory and brief. Preserve existing decisions. If these prerequisites are missing, identify them precisely; do not invent an assessment or silently start application changes.
3. Give 2–3 concept workers the same task, realistic content, representative page and constraints, with distinct coherent directions. Each owns its own `plan/concept-<id>/` directory.
4. Produce local renderable boards, semantic colour swatches, type/spacing scales, a unified vector icon language, component specimens, representative screens/dialogs and task/failure storyboards. Use HTML/CSS/SVG or the host toolkit; label a web presentation of a native concept accurately.
5. Translate reference pictures into explicit visual decisions. Prefer code-native interface assets and existing dependencies. Label preliminary byte and effort estimates as estimates.
6. Render and inspect every option, then create `plan/index.html` with comparable content, tradeoffs and a recommendation tied to the findings.
7. In guided mode obtain a real selection. In yolo mode apply the documented rubric and independent critique; record `agent-yolo`, never `user`, as the decision maker.
8. Reconcile combined choices into one coherent direction. Record `plan/selection.md`, rationale, alternatives and approval hashes using the run-record contract.
9. Finish with the selected direction or exact outstanding choice. Do not mark Design complete or change application styling as part of this phase.
