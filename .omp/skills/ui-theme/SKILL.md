---
name: ui-theme
description: Create, adapt, inspect or refine a versioned UI theme module with semantic tokens, declarative styling, local vector assets and a host adapter. The supplied compiler targets CSS/SVG; native stacks require an explicit native adapter and native validation. Use for a bounded theme engineering operation, without automatically redesigning all pages or changing the default.
---

# Engineer a portable theme

Perform the requested theme operation only. Determine whether the user wants inspection, scaffolding, refinement, adapter integration or validation.

## Phase contract

Trigger: a bounded theme, token or host-adapter operation.
Minimum inputs: context, theme contract, host mechanism and rollback target.
Task contract: change one versioned adapter surface without redesigning all pages.
Outputs: tokens, declarative resources, adapter validation and rollback notes.
Gate: theme compiler plus host-specific selection, persistence and fallback checks.
Escalate: native target without adapter, unsafe asset, stale evidence or registry risk.

Resolve or refresh the [project context](../ui-design-studio/references/project-context.md) for this scope. Use the selected run's model policy, or `models=auto-models` by default for a new run; honor `models=current-model` when requested. Follow [model routing](../ui-design-studio/references/model-routing.md) before delegation. These settings do not expand this phase's scope.

1. Read the [theme contract](../ui-design-studio/references/theme-module.md), [visual system](../ui-design-studio/references/visual-system.md), [run records](../ui-design-studio/references/run-records.md) and [quality gates](../ui-design-studio/references/quality-gates.md).
2. Read project instructions, config, existing theme mechanisms and relevant approved design artifacts. Preserve current styling and a known-good fallback. Missing registry files do not prove that no theme exists.
3. Use `themes/<slug>/` and the package's documented manifest/token contract. Reuse the host's theme API through an adapter instead of creating a competing style system.
4. Separate primitive, semantic and component tokens. Keep colour mode, density and motion preferences independent. For the supplied web adapter, use the helper's supported token types and deterministic CSS generation. For native targets, document and test token conversion, native resources, packaging and validation explicitly; do not treat a successful CSS build as native acceptance.
5. Prefer the host's declarative styles, local fonts where justified and small vector subsets; use CSS/SVG for web themes. Do not introduce arbitrary executable theme hooks or undeclared remote runtime assets.
6. Keep one owner for shared tokens and adapter integration. Propose contract changes explicitly; coordinate affected pages and invalidate stale evidence.
7. Validate the module and inspect real component states. Check selection, persistence, fallback, preserved application state and applicable accessibility/performance budgets.
8. Document compatibility, source tokens, customization, provenance and rollback. Record precisely which checks ran.
9. Follow the [theme lifecycle](../ui-design-studio/references/decisions.md). Scaffolding does not set a default; registration/default changes require the complete finalization prerequisites unless the user requested an independently scoped existing-theme operation.
