# Test matrix

## Inherited baseline results

Environment: isolated CPython 3.13.16, system Python 3.12.3 available, Node 24.22.2, Linux x64.

| Gate | Command | Observed result |
| --- | --- | --- |
| Python unittest | `python -m coverage run --source=src/ui_design_studio,.omp/skills/ui-design-studio/scripts,scripts -m unittest discover -s tests -v` | 232 tests passed |
| Node extension | `node --test tests/test_progress_extension.mjs` | 49 passed, zero failed or skipped |
| Shell syntax | `bash -n install.sh tools/ui-design` | Exit 0 |
| Dependencies | `python -m pip_audit --format=json` | No known vulnerabilities found |
| Release manifest | `python scripts/package_release.py --check` | Failed after audit documents were added; exact original-source manifest reconstruction matched the baseline manifest |
| Wheel | Regular package install through uv | Built and installed successfully |
| Editable install | `uv pip install -e .` | Unsupported Hatchling prefix-rewriting layout |

Baseline additionally passed five pytest-only remediation-contract functions. Baseline unittest does not collect those functions. Final `pytest -q` collects both styles.

## Prior remediation results

All source corrections were present for these gates. Logs remain at `/tmp/ui-design-freeze-baseline/`; these are local evidence, not portable release assets.

| Gate | Observed result | Evidence |
| --- | --- | --- |
| Python 3.13.16, full pytest | 266 passed, 161 subtests passed, zero skipped or failed | `release-python313.log` |
| Python 3.10.22, full pytest | 266 passed, 161 subtests passed, zero skipped or failed | `release-python310.log` |
| Node 24.22.2 extension | 52 passed, zero skipped or failed | `final-node.log` |
| Chromium 159.0.8154.6 | Four lifecycle/focus regressions passed, also included in both full Python runs | `browser-lifecycle-after.log` |
| Release builder | 13 tests passed, including unsafe destinations and publication failures | Included in full pytest |
| Wheel/sdist/package | Five tests passed, including private-ancestor template exclusion without VCS ignores | Included in full pytest |
| Source manifest and ZIP | Builder PASS; source hashes, archive entries and CRC checked; ZIP sidecar verified from its directory | `final-manifest.log`, release builder output |
| Wheel and sdist builds | Both 1.4.1 artifacts built successfully through Hatchling | `final-build.log` |
| Ruff correctness subset | `E9,F63,F7,F82` passed for source, scripts and tests | Central command output |
| Shell and browser-script syntax | `bash -n install.sh tools/ui-design` and both `node --check` commands passed | Central command output |
| Runtime dependencies | pip-audit reported no known vulnerabilities | `release-dependency-audit.json` |
| Secrets/configuration | Historical Trivy batch `02cf14e6-cf83-4300-93f9-d8bead9634d4` was reported empty | Original response was not retained; not current acceptance evidence (FF-028) |
| Native OMP 18.20.2 | Real PTY loaded the extension, waiting widget, authenticated dashboard URL and QR card without a model prompt | Native smoke observation |
| Native OMP cleanup | Owned dashboard port closed and no private runtime JSON remained | Post-exit command |
| Historical release archives | Three existing ZIPs matched their SHA-256 sidecars | Central checksum command |

Reproduce the full source gates using the isolated interpreter for each supported Python version:

```bash
UI_DESIGN_TEST_BROWSER=/path/to/chromium python -m pytest -q
node --test tests/test_progress_extension.mjs
python -m ruff check --select E9,F63,F7,F82 src scripts tests hatch_build.py .omp/skills/ui-design-studio/scripts
bash -n install.sh tools/ui-design
node --check .omp/skills/ui-design-studio/dashboard/dashboard.js
node --check .omp/skills/ui-design-studio/dashboard/landing.js
python scripts/package_release.py --check
sha256sum -c MANIFEST.sha256
```

Use the verification dependencies in [DISTRIBUTION.md](../DISTRIBUTION.md). A missing Playwright/browser skips browser tests, so inspect the reported skip count. The Python 3.10 environment initially lacked pip; after installing that test prerequisite, its complete final run passed. An initial sidecar check used the repository directory and could not resolve the sidecar's relative ZIP name; checking from `/tmp` passed. Neither environment error is counted as a passing product check.

## Inherited coverage

Parent-process statement coverage increased from 74% to 77%. Subprocess execution is not included.

| Component | Final statement coverage |
| --- | --- |
| Workflow engine | 91% |
| Design server | 89% |
| Dashboard service | 93% |
| Runtime | 96% |
| MCP server | 55% |
| CLI | 14% |
| Project installer | 24% |
| Global installer | 90% |
| Release builder | 84% |
| Benchmark script | 0% |

CLI, installer, MCP stdio and benchmark subprocess checks exist; their child-process execution does not contribute to this report. The benchmark was executed separately. Coverage is not a release certificate. Native Windows/macOS execution, native BFCache restoration, other browser engines, physical devices and human acceptance remain unverified. No configured project-wide type-check or lint gate exists; the correctness-only static check does not claim strict typing.

## Independent revalidation on 16 November 2026

Current evidence is retained under `/tmp/ui-freeze-evidence-UKWQB8/`.
These local logs are not portable release assets.
The starting baseline and inherited candidate are distinguished below.

| Gate | Current observed result | Local evidence |
| --- | --- | --- |
| Unchanged release baseline, Python 3.12.3 | 228 unittest cases ran, five dependency/setup errors | `baseline-tests.log` |
| Inherited candidate, Python 3.12.3 | 261 unittest cases passed | `candidate-tests.log` |
| Final Python 3.10.22 full pytest | 298 passed, 212 subtests passed, zero skips/failures | `audited-full-py310.log` |
| Final Python 3.12.3 full pytest with branch coverage | 298 passed, 212 subtests passed, zero skips/failures | `audited-full-py312.log` |
| Engine correction regressions | Initial 36 failures; later review reproduced eight cases and final CSS review four cases; final affected suite 188 passed and 134 subtests passed | `engine-regressions-before.log`, `integrity-review-before.log`, `css-final-review-before.log`, `css-final-review-after.log` |
| Chromium 159.0.8154.6 | Six lifecycle, focus and actual guided form regressions, included in both final full suites | Full Python logs |
| Browser workflow smoke | Actual landing/run navigation, retained HTML, focus restoration, four sections at 320px, approval controls and zero page errors | `browser-smoke.log` |
| Node 24.22.2 extension | 52 passed, zero failures/skips | `engine-node.log` |
| Actual OMP 18.20.2 | Final installed wheel and candidate extension, live dashboard card, authenticated matching identity; owned listener and runtime records removed after exit | `final-native.log` |
| Ruff correctness subset | `E9,F63,F7,F82` passed for final runtime, scripts and tests | `audited-static.log` |
| Shell and browser JavaScript syntax | `bash -n` and both `node --check` commands passed | Parent command output |
| Wheel and sdist | Both final 1.4.1 candidate artifacts built with no isolation; installed consumers exercised outside checkout in both full suites | `audited-build.log`, `audited-packages/` |
| Source ZIP privacy/recovery | 14 builder tests and 15 subtests passed, also included in final full suites | `package-template-after.log` |
| Historical release ZIPs | All three existing sidecars verified from `dist/` | Parent checksum output |
| Current scanner | Batch `20ae704c-e6ca-49cf-a126-601958c52512`, empty findings across vulnerability, secret, configuration and license scans | Original response retained in `SECURITY-EVIDENCE.json` |
| Resolved dependency audits | No known vulnerabilities in final Python 3.10 and 3.12 environments | Raw JSON and removed-dependency advisories in `SECURITY-EVIDENCE.json` |
| Complete packaged-source identity | All 50 wheel members and 55 sdist source members matched final authored bytes | `audited-package-identity.log` |
| Source manifest and ZIP | 127 source hashes verified; 128 ZIP members, original bytes and CRCs verified by builder; sidecar matches archive | `final-source-integrity.log`, regenerated after final report/traceability changes |

The initial errors were four missing Pillow errors and missing Hatchling for a no-isolation wheel build.
Verification dependencies were installed before candidate checks.
An initial pip-audit command used `--disable-pip` without `-r` and was rejected.
The corrected installed-environment audit passed.
An initial historical ZIP check used the wrong working directory.
The corrected check ran from `dist/` and passed.
The browser smoke initially selected all three artwork cards instead of the named fixture.
The corrected specific selector passed without changing product code.
The host browser helper could not launch its daemon.
Actual Chromium checks used Playwright directly instead.

Parent-process coverage excludes child-process execution.
The source CLI, MCP, installer, and installed-console checks execute real subprocesses.
No strict TypeScript check is claimed because the repository has no resolvable host API types or configured type-check gate.

## Current risk-weighted coverage

Combined parent-process statement/branch coverage is 76%. This is not directly comparable to the inherited statement-only 77% figure.

| Component | Combined coverage |
| --- | ---: |
| Workflow engine | 90% |
| Design server | 87% |
| Dashboard service | 91% |
| Runtime | 92% |
| MCP server | 54% |
| CLI | 12% |
| Project installer | 22% |
| Global installer | 87% |
| Release builder | 81% |
| Benchmark script | 0% |

`audited-coverage-report.txt` retains the final component data. Child processes are not measured by this report. CLI, installer, MCP stdio, installed console and benchmark checks execute separately. Low parent-process coverage remains a disclosed measurement gap, not an invented complete-coverage claim.

The first coverage report's output name overlapped the data-file prefix and caused an attempted combine warning. No test failed. The existing database still produced the reported component data. The audit environment initially lacked `pip_audit` on Python 3.10; installing it introduced an unnecessary vulnerable verification-only `filelock`. The added auditor packages were removed and that environment was audited from Python 3.12 with `--path`, rather than suppressing advisories.

The native OMP smoke exercised the unchanged extension/dashboard lifecycle with the `final-review-packages` wheel. The final three CSS lexical/source corrections do not modify that surface; the newer `audited-packages` wheel received complete source-byte and installed-consumer verification in both full Python gates.

## Explicit ShipIt follow-up

`tests/test_dashboard_browser.py` now includes actual cross-site navigation and browser Back. All seven Chromium cases passed using `ignore_default_args=["--disable-back-forward-cache"]`, without changing application headers or synthesizing this test's lifecycle events.

The trusted `pageshow` reported `persisted=false` and a new document identity. Chromium 159.0.8154.6 reported `response-cache-control-no-store` and `response-cache-control-no-store-with-js-network-request`. The reloaded landing page displayed the run created while away, then found a second run through continued polling. This verifies real history-navigation recovery, not a BFCache restore. Earlier simulated persisted cases remain separate coverage for the restoration handler.

Current follow-up execution is retained at `/tmp/ui-freeze-shipping/browser-history-tests.log`. The earlier 298-case full-suite figures describe the complete pre-shipping audit head; the shipping PR's independent verifier records its final-head consumer results on GitHub.

Playwright's [default Chromium switches](https://github.com/microsoft/playwright/blob/main/packages/playwright-core/src/server/chromium/chromiumSwitches.ts) explicitly disable BFCache by default. Removing that automation-only switch permits observation of the browser's real eligibility decision; it does not force cache admission.
