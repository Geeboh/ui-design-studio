# v1.4.0 remediation test report

Status: ENGINEERING_READY_UAT_PENDING. Automated results are current after the final command matrix. Human and user-based testing remains `DEFERRED_UAT`.

## Environment

- Repository baseline commit: `0f25a1e85cca1b7d61602f08f7b4a4c79f9746a3`.
- Working branch: `main`; requested remediation branch creation was blocked by shared-workspace policy.
- Python: `3.12.3`; Node: `v24.22.2`; npm: `11.19.1`.
- `.venv` packages: `mcp==1.30.0`, `segno`, `psutil`, Pillow 11.3.0, build 1.6.1, hatchling 1.33.0, zxing-cpp 2.3.0.
- No paid provider calls, credentials, browser target, native device, global installation, deploy, publish or user interaction.
## Commands and results

| Command | Result | Evidence |
| --- | --- | --- |
| historical baseline Python suite before optional dependencies | 206 passed, 4 failed, 4 errors, 117 subtests | missing Pillow/build; preserved in R00 notes |
| final Python suite | PASS, 237 passed, 125 subtests | `.venv/bin/python -m pytest -q` |
| Node extension suite | PASS, 49 passed | `node --experimental-strip-types --test tests/test_progress_extension.mjs` |
| installer/MCP dashboard security suite | PASS, 69 passed, 46 subtests | `tests/test_mcp_dashboard.py`, `tests/test_global_mcp_install.py`, `tests/test_install.py` |
| wheel/package suite | PASS, 19 passed, 3 subtests | `tests/test_mcp_package.py tests/test_install.py` |
| package builder | PASS, v1.4.0, 103 files; final metadata captured by the final package-build command | `scripts/package_release.py`; `/tmp/remediation-package-final.json` |
| manifest/checksum | PASS, 102/102 hashes | `scripts/package_release.py --check`; `sha256sum -c MANIFEST.sha256` |
| remediation benchmark | PASS, bounded compact output, hash reduction, and six deterministic workload shapes | `scripts/remediation_benchmark.py`; `benchmarks.json` |
| compile and static contract checks | PASS | `compileall`, remediation contract tests, link/frontmatter audits |

## Coverage

Automated fixtures cover evidence freshness and registration rejection, routing normalization and recovery, validation cache invalidation, compact and paged MCP status, scoped closure, sparse applicability, resume manifests, selected-role packets, host-feasibility ordering, conditional offline policy, installer/package security, benchmarks and legacy compatibility.

Human visual preference, usability, physical-device, native-host, production and deployment checks remain deferred. Missing real target rendering is not converted to PASS.

