---
name: ui-produce
description: Implement approved UI mockups and a portable theme through bounded coding agents, integration and independent review. Use for the Produce phase only; preserve required design approvals and do not automatically publish or change the default theme.
---

# Produce the approved interface

Perform the Produce phase only unless the user explicitly includes finalization or release.

Resolve or refresh the [project context](../ui-design-studio/references/project-context.md) for this scope. Use the selected run's model policy, or `models=auto-models` by default for a new run; honor `models=current-model` when requested. Follow [model routing](../ui-design-studio/references/model-routing.md) before delegation. These settings do not expand this phase's scope.

1. Read the [workflow](../ui-design-studio/references/workflow.md), [theme contract](../ui-design-studio/references/theme-module.md), [quality gates](../ui-design-studio/references/quality-gates.md) and [multi-agent guidance](../ui-design-studio/references/multi-agent.md).
2. Read project instructions, Git policy, config and current run records. Require the approved Plan, complete mockups, coverage and design contract. Identify missing prerequisites instead of inventing approvals.
3. Preserve unrelated changes. Use the authorized branch/worktree policy and the resolved [project context](../ui-design-studio/references/project-context.md). Read original instructions for each owned scope and preserve required business behaviour.
4. Implement a vertical slice: the existing host's theme adapter, shared tokens/primitives and one real page with edge states. Verify it before distributing page families.
5. Dispatch bounded implementers with non-overlapping files or worktrees. Keep global styles, tokens, registry and shared integration under one owner. Include explicit project instructions in every task contract.
6. Implement remaining surfaces against the approved contract in the existing toolkit. Prefer declarative styles, vector resources, local assets and existing native components; use CSS/SVG for web interfaces. Native themes require an explicit native adapter and platform tests; the supplied CSS validator cannot approve them. Preserve route, form, data, permission and business-state behavior.
7. Integrate sequentially, render the actual application and compare required cases against mockups. Run existing project gates and relevant accessibility, offline, performance and theme-switching checks.
8. Obtain independent review, fix material issues and rerun affected checks plus required integration gates. Record actual commands, results and current artifact/source identities.
9. Finish with implementation evidence and precise remaining gaps. Do not claim completion from worker summaries alone, register a default prematurely or deploy beyond existing authorization.
