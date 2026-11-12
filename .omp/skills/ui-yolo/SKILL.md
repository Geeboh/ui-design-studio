---
name: ui-yolo
description: Run the complete UI Design Studio lifecycle autonomously, choosing visual concepts, approving reviewed mockups, naming the theme and directing implementation through final packaging. Use when the user explicitly delegates design choices in yolo mode.
---

# Run autonomous design end to end

Load the [UI Design Studio director](../ui-design-studio/SKILL.md) and execute its full lifecycle in `mode=yolo`, respecting any explicit scope limits or resume request. Read project requirements through [project context](../ui-design-studio/references/project-context.md); no `profile=` argument is needed. Use `models=auto-models` for a new run unless `models=current-model` or a project preference selects otherwise; honor recorded choices on resume. Follow [model routing](../ui-design-studio/references/model-routing.md) before delegation.

Run in normal OMP mode or within `/goal` when its objective explicitly loads this skill. Goal mode adds continuation; it does not change the design authorization or model policy. Mark a goal complete only after the full requested scope and required checks are verified. A blocked or budget-limited run remains incomplete.

1. Read [decisions](../ui-design-studio/references/decisions.md), [workflow](../ui-design-studio/references/workflow.md), [multi-agent guidance](../ui-design-studio/references/multi-agent.md) and applicable project instructions.
2. Inspect existing runs and actual code before starting. Reuse established preferences, requirements and provided pictures. Preserve the project's Git, task, gate and authorization rules.
3. Assess the interface and write the evidence-based report and complete inventory. Mark unavailable measurements and uncertain user assumptions honestly.
4. Dispatch comparable concepts, render them, apply the rubric and obtain independent critique. Choose a coherent direction or reconcile specific elements without asking cosmetic questions.
5. Direct complete mockups for every scoped page/dialog and applicable state. Inspect them, resolve review findings and record autonomous approval against the actual artifacts.
6. Direct bounded coding workers, integrate shared components and the theme adapter, verify rendered behavior and require independent review. Continue safe, unblocked work until the requested scope is complete.
7. Choose a suitable theme name and collision-free stable ID. First successful finalization makes it the default. On later runs without an explicit action, create a new theme and preserve the existing default.
8. Record design choices with actor `agent-yolo`, rationale and artifact identities. Do not impersonate human approval, fabricate evidence or relax quality gates.
9. Finalize, package, document and hand over the result. Preserve rollback and existing deployment authorization. Ask only for a genuine unresolved blocker, after completing independent work.

Yolo delegates design judgment for the current run. It does not disable runtime permissions, authorize unrelated changes or turn failed checks into passing results.
