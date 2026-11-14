# v1.4.0 remediation compatibility

Status: ENGINEERING_READY_UAT_PENDING. Automated compatibility and package checks are recorded in `TEST-REPORT.md`; human acceptance remains deferred.

## Runtime and schema compatibility

| Area | Existing behavior | Remediation behavior | Migration | Rollback |
| --- | --- | --- | --- | --- |
| Evidence records | v1.0/v1.1 records and legacy no-input entries are readable | Shared validator checks report bytes, bound inputs, `inputsDigest`, path confinement and offline applicability; review digests include normalized dependencies | New records may add `inputs` and `inputsDigest`; legacy no-input entries remain readable and are labeled unbound | Remove new fields only when preserving legacy semantics; stale records must be re-reviewed |
| Routing | Existing key spellings and all-seven v1.1 assignments | Canonical `thinking`, `thinking-level`, `thinking_level` and `thinkingLevel`; v1.2 selected roles; journaled apply/restore | New runs use `modelRouting.schemaVersion=1.2` and `selectedRoles`; v1.1 all-seven records remain readable | `models-restore` restores original bytes; no global model settings are changed |
| Run records | `run.json` v1.0 and v1.1 | New runs record scope fields and create `manifest.json` v1.0; `scopedCompletion` is separate from final status | Missing manifest blocks resume conservatively; legacy checks remain readable | Delete only a newly generated manifest to force conservative legacy verification |
| Coverage | v1.0 full Cartesian state × viewport interpretation | Coverage v1.1 may declare `applicabilitySchema`, `applicableCases` and explained `excludedCases` | Omitted applicability fields retain Cartesian behavior | Remove applicability fields to restore legacy interpretation |
| MCP status | Full status snapshot and existing tools | Full status remains; compact status and revision-bound artwork/evidence pages are additive | Call new `ui_design_status_compact`/`ui_design_status_page`; old `ui_design_status` unchanged | Use full status and existing resource retrieval |
| Scope closure | No typed bounded closure | `scope-complete` and `ui_design_scope_complete` write versioned scoped evidence without changing final gates | Use only for non-`full-redesign` scopes | Full-redesign uses normal finalization; registration remains blocked |
| Worker packets | Manual role task context | `worker-packet` and `ui_design_worker_packet` hash owned files and mandatory instructions | Add selected roles to v1.2 routing before dispatch; packet does not claim execution | No packet mutation is required; regenerate after source changes |
| Installation | v1.4.0 package layout and isolated MCP runtime | Package includes new engine, docs, tests and benchmark script; no global install was performed here | Reinstall/update through existing installer in a disposable project | Use installer backup/restore; release/publish remains unauthorized |

## Host compatibility

Python >=3.10 remains required. Node and optional MCP tooling retain existing supported entry points. No global user model setting or user installation is changed by tests.

## Security compatibility

Path confinement, symlink rejection, HTTP sanitization, auth, CSRF, cleanup, and theme rollback remain required. Added APIs must not expose files or accept arbitrary remote code or styles.

## Verification and limits

Python 3.12.3, Node v24.22.2 and npm 11.19.1 were observed. `mcp==1.30.0`, `segno`, `psutil`, Pillow 11.3.0 and build 1.6.1 ran in `.venv`. No global user installation, provider call, deploy, publish, merge or tag mutation occurred.

The package builder passed ZIP CRC/content checks and `MANIFEST.sha256`. Installer integration tests ran in disposable paths. Source-only security regressions cover path confinement, symlink rejection, stale-input rejection, HTTP sanitization and owned cleanup. Browser, native-device and human acceptance remain deferred or unavailable, as listed in `UAT-DEFERRED.md`.
