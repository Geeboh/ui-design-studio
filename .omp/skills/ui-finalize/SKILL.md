---
name: ui-finalize
description: Validate, document, register and package a completed reviewed UI theme, apply first-run or later-theme lifecycle rules and record rollback. Use for Finalize only when implementation and required approvals already exist.
---

# Finalize the reviewed theme

Perform Finalize only. Do not invent missing design, implementation or review work to satisfy a release gate.

## Phase contract

Trigger: explicit finalization of a completed, reviewed theme.
Minimum inputs: current approvals, fresh evidence, package metadata and rollback.
Task contract: validate current bytes, document, register only after full gates.
Outputs: package, registry result, rollback record and handoff.
Gate: all required full-theme checks and independent review pass.
Escalate: stale evidence, missing approval, adapter check or authorization.

Resolve or refresh the [project context](../ui-design-studio/references/project-context.md) for this scope. Use the selected run's model policy, or `models=auto-models` by default for a new run; honor `models=current-model` when requested. Follow [model routing](../ui-design-studio/references/model-routing.md) before delegation. These settings do not expand this phase's scope.

1. Read the [workflow](../ui-design-studio/references/workflow.md), [theme contract](../ui-design-studio/references/theme-module.md), [run records](../ui-design-studio/references/run-records.md), [quality gates](../ui-design-studio/references/quality-gates.md) and [decision lifecycle](../ui-design-studio/references/decisions.md).
2. Read project instructions and the current run. Verify approved Plan/Design artifacts, complete coverage, independent implementation review and required project/UI checks against current files.
3. Resolve stale evidence or exact blockers before release. Require the actual platform's integration and native checks for native targets; the supplied web theme compiler/validator only validates its CSS/SVG contract. Missing checks are not successful checks. Finalization approval is the director's acceptance; do not create an extra human checkpoint solely because this is guided mode.
4. Complete the theme's version, compatibility, editable tokens, generated styles, local icons, manifest, licensing/attribution, usage guide, decisions, changelog, measurements and rollback documentation.
5. Complete the declared host adapter's validation. After dependent workers finish or park, restore any temporary assignments with `models-restore`, record restoration and refresh the routing hash. For the supported web module, run documented `tools/ui-design` build/theme/run checks. Bind final acceptance to the current review digest and register/package through the declared adapter's documented procedure; a native module requires its explicit native tooling. In yolo mode use `agent-yolo` for autonomous design decisions; never mislabel them as user approval.
6. Make the first successfully finalized Studio theme the default. On later runs honor `modify-default` versus `new`, retaining the existing default for a new theme unless otherwise instructed.
7. Verify the real application consumes the theme registry/adapter; test persistence, invalid selection fallback, state preservation and development rollback. Registry metadata alone is not a working theme interface.
8. Preserve the prior theme and evidence. Complete only Git/release operations already authorized by project policy.
9. Clean up the Design Server with `tools/ui-design design-cleanup <run-directory>` and verify that the owned listener stopped. Yolo does this automatically after current final acceptance and on successful registration; the explicit command is idempotent. Retain all design artifacts, the browsable artwork library, decisions and evidence. Guided review pauses keep the server available.
10. Hand over name/version, package and preview paths, default status, verified results, limitations and exact rollback steps. Distinguish a completed local result from an external deployment.
