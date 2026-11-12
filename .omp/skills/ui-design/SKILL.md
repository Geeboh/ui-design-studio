---
name: ui-design
description: Create complete adaptable screen, window and dialog mockups from an approved UI direction, with shared tokens, state/device coverage and interaction specifications. Use for the Design phase only; the ui-design command invokes the separate full Studio workflow.
---

# Design every scoped surface

Perform the Design phase only unless the user explicitly requests implementation or the full lifecycle.

Resolve or refresh the [project context](../ui-design-studio/references/project-context.md) for this scope. Use the selected run's model policy, or `models=auto-models` by default for a new run; honor `models=current-model` when requested. Follow [model routing](../ui-design-studio/references/model-routing.md) before delegation. These settings do not expand this phase's scope.

1. Read the [workflow](../ui-design-studio/references/workflow.md), [visual system](../ui-design-studio/references/visual-system.md), [quality gates](../ui-design-studio/references/quality-gates.md) and [multi-agent guidance](../ui-design-studio/references/multi-agent.md).
2. Read project instructions and the current brief, findings, reconciled coverage and approved Plan artifacts. If selection or its evidence is missing, report that prerequisite; do not fabricate user approval.
3. Have the theme engineer freeze `design/contract.md`: semantic tokens, components, states, responsive rules, focus behavior, icon language and intended theme API.
4. Assign page families to independent workers when separable. Give each the same contract revision, required coverage IDs, owned paths and explicit project constraints.
5. Produce complete screen/window/dialog mockups with realistic content for every required state and window/device configuration. Include narrow layouts, orientation/scaling and on-screen-keyboard effects where relevant, long content, errors, unavailable states, recovery and less prominent surfaces. Use the actual host toolkit where available; label web presentations of native designs as concepts.
6. Create `design/index.html` linking each coverage case. Specify navigation, keyboard behavior, focus entry/return and responsive rearrangement. Label planned functionality clearly.
7. Render and inspect the complete index. Use an independent critic to resolve coherence, usability, accessibility and implementation concerns.
8. Apply [guided/yolo decision rules](../ui-design-studio/references/decisions.md): guided approval must come from the user; autonomous approval uses `agent-yolo`. Bind approval to the actual artifacts and contract.
9. Finish with complete design coverage and the next implementation prerequisites, or precise gaps. Do not implement application code or claim runtime tests passed in this mockup phase.
