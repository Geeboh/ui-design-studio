---
name: ui-assess
description: Assess an existing interface and produce an evidence-based usability report, complete page/dialog/state inventory, baseline and prioritized recommendations. Use for an audit or assessment only; this specialist does not automatically start redesign or implementation.
---

# Assess the interface

Perform the Assess phase only unless the user explicitly asks for the full lifecycle.

## Phase contract

Trigger: an assessment or `assess-only` request.
Minimum inputs: project context, target inventory and a selected or new run.
Task contract: inspect actual behavior and label evidence, inference and gaps.
Outputs: findings, surface/state inventory, baselines and next-phase prerequisites.
Gate: evidence-labelled findings and reconciled inventory.
Escalate: missing requirements, runtime access or required automated checks.

Resolve or refresh the [project context](../ui-design-studio/references/project-context.md) for this scope. Use the selected run's model policy, or `models=auto-models` by default for a new run; honor `models=current-model` when requested. Follow [model routing](../ui-design-studio/references/model-routing.md) before delegation. These settings do not expand this phase's scope.

1. Read the director's [workflow](../ui-design-studio/references/workflow.md), [assessment](../ui-design-studio/references/assessment.md) and [quality gates](../ui-design-studio/references/quality-gates.md).
2. Read applicable project instructions, `ui-design-studio.json` and existing run records. Resolve the source-labelled [project context](../ui-design-studio/references/project-context.md) from requirements and actual code. Preserve Git state and existing project gates; no profile selector is needed.
3. Discover actual routes, dialogs, state transitions, components, styling, browser/native inspection tools and test commands. Reconcile source and runtime evidence. Separate implemented, planned and missing surfaces.
4. Use independent usability and engineering/performance workers when available. Pass complete task contracts using [multi-agent guidance](../ui-design-studio/references/multi-agent.md); workers do not inherit the director's project context automatically.
5. Record observations and reproducible baselines. Label inference, hypotheses and unverified checks. Do not describe an agent walkthrough as user research or invent performance results.
6. Write `brief.md`, `report.md`, `findings.json`, `coverage.json` and baseline evidence under the selected `docs/design/runs/<id>/`. Use the director's current machine-record contract.
7. In guided mode show findings and ask a compact set of unresolved design questions. In yolo mode record explicit assumptions without cosmetic questions. Apply [decision rules](../ui-design-studio/references/decisions.md).
8. Report priorities, evidence, coverage gaps and the next phase's prerequisites. Finish without changing application styles or implicitly approving a concept.

Use `tools/ui-design` only for its documented checks and run bookkeeping. A successful environment check is not a usability assessment.
