# Test matrix

## Baseline results

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

## Final results

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
| Secrets/configuration | Trivy batch `02cf14e6-cf83-4300-93f9-d8bead9634d4` returned no findings | Scanner result; not proof of absence |
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

## Risk-weighted coverage

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
