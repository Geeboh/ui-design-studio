# PRISM Studio 2.0.11

PRISM Studio 2.0.11 publishes the post-2.0.10 remediation release.

## Changes

- Routes public MCP mutations through the durable state and operation journal.
- Keeps SQLite run projections consistent across repeated updates and reconnects.
- Hardens path containment, migration writes, theme writes, artifact validation, and approval scope.
- Fixes dashboard approval handling, run selection, observer timestamps, draft outcomes, and theme build idempotency.
- Binds the M8 gate to the source commit, manifest digest, and reproducibly rebuilt ZIP, sdist, and wheel.
- Expands CI coverage for browser engines, the standalone OMP host, extracted sdist installation, and the real source ZIP installer.
- Retains the representative high-detail optimization PNG fixture with measured before and after results.

## Compatibility

The release keeps the existing CLI names, MCP tools, project-local installer, global MCP runtime, OMP skills, dashboard routes, and run schema. Existing 2.0.10 installations can update through the normal installer conflict checks.

## Verification

The release candidate passed the full Python suite, the Chromium, Firefox, and WebKit browser matrix, the Node extension suite, the rebuild-pack tests, package and installer checks, reproducible artifact checks, and GitHub CI. Trivy reported no medium, high, or critical findings.

One requested independent shipping verifier crashed before producing a verdict. The release uses direct verification and the completed GitHub CI matrix instead. Native Windows and macOS, physical-device LAN checks, and human recipient-application UAT remain outside this package validation.
