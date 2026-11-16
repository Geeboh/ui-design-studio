# Quality gates

Status: `ENGINEERING_READY_WITH_EXTERNAL_LIMITS`; local Linux automated gates pass. Playwright Fast application QA, cross-browser/platform/device checks, and human UAT remain unresolved. Human UAT is `DEFERRED_UAT`, never passed.

| Gate | Status | Evidence or blocker |
| --- | --- | --- |
| Focused remediation tests | PASS | SVG, approval persistence/order, and browser regressions pass. |
| Full Python suite | PASS | 312 tests and 212 subtests passed in `.venv`. |
| Node extension suite | PASS | 52 tests passed. |
| Static/syntax checks | PASS | Ruff correctness subset, compileall, Node syntax, and shell syntax passed. |
| Security scans | PASS | pip-audit returned no known vulnerabilities; Trivy returned no findings. Local package advisory coverage is unavailable. |
| Direct Chromium browser coverage | PASS | 8 Python Playwright tests passed. |
| Playwright Fast application QA | BLOCKED | `PLAN_NOT_READY`, `qaStatus=NOT_RUN`, no application config/CLI/projects. |
| Source manifest/package artifact | PASS | 137-entry source ZIP, 136 source hashes, archive checksum, wheel and sdist verified. |
| Cross-browser/platform/device | BLOCKED | Firefox/WebKit, Windows/macOS, native devices unavailable in this environment. |
| Human acceptance | DEFERRED_UAT | No user testing or sign-off was requested or performed. |

A blocked gate is not recorded as PASS. No production deployment, publish, merge, or user approval is claimed.
