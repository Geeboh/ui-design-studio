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

Logs are retained at `/tmp/ui-design-freeze-baseline/`. They are local evidence, not portable release assets. Final results will be committed in this record.

## Coverage limits

Baseline parent-process statement coverage is 74%. Component results: engine 90%, design server 89%, dashboard 93%, runtime 96%, MCP server 54%, CLI 14%, project installer 24%, global installer 90%. Subprocess execution is not included in this coverage run. Low CLI/installer figures do not imply those subprocess integration tests were absent. Release and benchmark scripts show 0% because subprocess execution was not measured.

`tests/test_remediation_contract.py` contains pytest functions and is not collected by unittest. Run it separately before the final gate. No configured lint or type-check command exists.
