# Testing

## Test inventory

The repository contains Python tests for studio lifecycle and model routing, design-server and browser dashboards, MCP protocol/dashboard/package behavior, installers, freeze and acceptance contracts, release privacy and checksums, remediation contracts, and progress extension payloads. tests/test_progress_extension.mjs covers authenticated connection selection, isolation, path and symlink confinement, task export, legacy behavior, recovery, runtime handling, redaction, and lifecycle cases.

## Existing test records

docs/VALIDATION.md and remediation/feature-freeze records contain historical and current-branch validation reports, declared limits, and deferred UAT. Those pages are preserved. Their statements are not re-executed or upgraded by this review.

## Verification performed here

The initial Documenter run inspected source and test files and recorded static review evidence. It did not run installation, the Python suite, Node tests, browser automation, a live MCP server, a provider, a device, or user acceptance.

After source changes, run the narrow existing test or check covering the changed surface. For runtime or browser changes, include the relevant dashboard/extension test and an actual supported host or browser scenario. Record commands, results, environment, and limits separately from source review.

Sources: tests/, docs/VALIDATION.md, docs/remediation/v1.4.0/TEST-REPORT.md, scripts/remediation_benchmark.py.
