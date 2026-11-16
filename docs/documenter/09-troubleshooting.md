# Troubleshooting

| Symptom | Source-established action |
| --- | --- |
| Installer says Python is missing | Provide Python 3 with the venv module, then rerun install.sh. |
| Project venv is incomplete | Repair or move .venv-ui-design; the installer refuses to overwrite it. |
| Installation conflict | Inspect the named file or managed block. Use --update only after preserving intentional edits. |
| Temporary model routing is active | Run the documented restore command for the run, then install or update. |
| Dashboard runtime is missing | Install the user-global MCP runtime, then use /ui-design-dashboard start. |
| Dashboard identity mismatch | Stop using that connection; select a verified connection inside the project boundary. |
| Multiple design servers or runs | Select an explicit run or dashboard session. Do not guess. |
| Design server stopped | Resume explicitly; automatic discovery does not silently claim a stopped run. |
| Dashboard recovery stops | Use /ui-design-dashboard start after capped automatic recovery attempts. |
| Restore refuses | Inspect edited or missing files. Restore only when installed hashes still match. |
| Release check fails | Review MANIFEST.sha256 and source changes; do not publish a stale archive. |

Existing validation docs contain historical and current-branch notes. Treat their reported test counts as recorded claims, not as results of this documentation run. The current review performed static inspection only.

Sources: install.sh, scripts/install.py, .omp/extensions/ui-design-progress.ts, scripts/package_release.py, docs/INSTALLATION.md, docs/VALIDATION.md.
