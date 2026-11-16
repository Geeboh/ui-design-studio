# Unknowns

These facts remain unresolved because source inspection cannot establish them without executing an unavailable or intentionally skipped environment.

## U-RUNTIME-001 — Live OMP/provider behavior

Unknown: Whether the current package behaves as documented under a live OMP host, MCP provider, and configured model route.

Impact: Runtime routing, host API compatibility, and provider-specific failures remain unverified.

Next step: Run an isolated guided smoke workflow with the intended host and record actual route, phase, and failure evidence.

## U-APP-002 — Recipient application adapter

Unknown: Whether a particular recipient application has a working native or browser adapter for the theme and workflow outputs.

Impact: Native rendering, application integration, and end-to-end UI acceptance cannot be claimed from this package alone.

Next step: Supply the target application and adapter, then run the documented applicable accessibility, responsive, offline, and rollback checks.

## U-PLATFORM-003 — Cross-platform/browser/device execution

Unknown: Behavior on supported host, browser, and device combinations not exercised by this static review.

Impact: Platform-specific path, rendering, browser, device, and permission defects may remain.

Next step: Run the existing platform matrix and browser/device scenarios where the environment is authorized and available.

## Disposition

These unknowns are recorded, not hidden. Existing human-authored validation and UAT records remain preserved and may contain additional historical limits.

Sources: .omp/skills/ui-design-studio/references/quality-gates.md, workflow.md, model-routing.md, docs/VALIDATION.md, docs/remediation/v1.4.0/UAT-DEFERRED.md.
