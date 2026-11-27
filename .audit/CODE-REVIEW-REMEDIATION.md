# PRISM Studio full code review remediation checklist

Reviewed: 2026-11-27  
Source: current `overhaul/prism-v2` checkout, version 2.0.10  
Assumed load: one local operator or small trusted design team, concurrent OMP/MCP/dashboard processes, long-lived run histories, and user-supplied project assets.

## What this repo does

PRISM Studio installs OMP design skills, exposes an MCP runtime, stores transactional project state, serves an authenticated browser dashboard, packages themes and run evidence, and builds distributable archives. Its highest-risk boundaries are local filesystem writes, durable run decisions, capability URLs, uploaded content, optimization subprocesses, and release evidence.

## Evidence collected

| Check | Result |
| --- | --- |
| Python suite excluding browser tests | **FAIL**: 356 passed, 220 subtests passed, 2 failed |
| Dashboard browser matrix | **PASS**: 15 tests each on Chromium, Firefox, and WebKit |
| Rebuild-pack tool suite | **ERROR**: 19 setup errors from `.prism-rebuild/MANIFEST.sha256` drift |
| Python compile, Node syntax, shell syntax | **PASS** |
| `pip check` | **PASS** |
| Source package manifest | **PASS**: 201 files |
| Trivy filesystem scan | **PASS**: no medium-or-higher vulnerability, secret, license, or misconfiguration findings |
| Semgrep | Two false positives: mode `0700` is intentionally stricter than suggested `0644` |

## Must fix

### 1. [ ] Close filesystem path escapes in lifecycle identifiers

**Severity:** P0 security and data loss  
**Evidence:** `src/ui_design_studio/theme_lifecycle.py:51-70`, `src/ui_design_studio/migration.py:219-239`, `src/ui_design_studio/server.py:112`, `.omp/skills/ui-design-studio/scripts/design_server.py:2177-2182`

- **What this is:** Receipt IDs, migration IDs, and the project state path select durable files and directories.
- **Problem:** `receipt_id` and `migration_id` are interpolated into paths without rejecting separators or `..`. `StateStore` resolves a project-controlled `.ui-design-studio` symlink instead of enforcing repository containment.
- **Concrete case:** `receipt_id="../outside"` selects a backup or receipt outside `state_root`. A repository symlink can redirect `state.sqlite3` outside the selected project.
- **Fix:** Validate IDs as bounded slugs. Resolve every target and require it to remain below its owned root. Reject symlinked state ancestors.
- **If skipped:** A local project or malformed command can overwrite, rename, or create files outside PRISM state.
- **Acceptance:** Add traversal, absolute-path, separator, Unicode-normalization, and symlink-ancestor tests for install, upgrade, restore, migration backup, MCP dispatch, and dashboard dispatch.

### 2. [ ] Keep optimized bytes separate from transport compression

**Severity:** P1 correctness  
**Evidence:** `.omp/skills/ui-design-studio/scripts/optimization.py:421-449`, `.omp/skills/ui-design-studio/scripts/design_server.py:1897-1915`, `.omp/skills/ui-design-studio/dashboard/dashboard.js:1360-1368`

- **What this is:** Optimization produces an optimized resource plus optional gzip and Brotli transport artifacts.
- **Problem:** The optimizer assigns the smallest compressed artifact to `current`, persists it as `after`, and serves it under the source MIME type without `Content-Encoding`. The UI also always renders a Gzip link even when no gzip artifact exists.
- **Concrete case:** Optimized HTML downloads gzip bytes labeled `text/html`; PNG and PDF Gzip links return “artifact not found.”
- **Fix:** Persist transformed bytes as `after`. Keep gzip/Brotli only in separate variants. Render links only for recorded artifacts and return correct headers.
- **If skipped:** “After” previews and downloads are corrupt or dead.
- **Acceptance:** Byte-level tests must open each `after` resource as its original type and independently decompress gzip/Brotli variants.

### 3. [ ] Replace unsafe lexical minifiers and sanitize before external SVG tools

**Severity:** P1 correctness and security  
**Evidence:** `.omp/skills/ui-design-studio/scripts/optimization.py:186-304`, `:318-409`

- **What this is:** Built-in minifiers and external tools transform user assets.
- **Problem:** Lexical JS/CSS rewriting changes valid semantics. `return\n{ok:true}` becomes `return{ok:true}`; `calc(100% - 1rem)` becomes invalid. SVG sanitization is discarded when it is not smaller, and external SVG tooling receives the unsanitized original, preserving `onclick`.
- **Fix:** Use syntax-aware minifiers or preserve source. Sanitization must win regardless of byte size, and every later SVG stage must consume sanitized bytes.
- **If skipped:** Lossless optimization can break applications or emit executable SVG content.
- **Acceptance:** Add semantic JS fixtures, CSS `calc()` fixtures, malicious SVG event/script/URL fixtures, and parse/render checks on final bytes.

### 4. [ ] Unify the public run state and authority model

**Severity:** P1 integrity  
**Evidence:** `src/ui_design_studio/server.py:202-220`, `:265-321`, `src/ui_design_studio/application/commands.py:82-119`

- **What this is:** Public MCP tools expose both the legacy JSON engine and the SQLite command engine.
- **Problem:** `ui_design_start_run`, scope, worker, register, and restore routes bypass the command store. `ui_design_command` accepts client-supplied principal, actor kind, mode, and project scope as authority.
- **Concrete case:** A run created through `ui_design_start_run` has `run.json` but no SQLite `runs` row. A caller can claim human guided authority in an envelope.
- **Fix:** Choose one authoritative state engine. Bind actor and project scope at the authenticated adapter boundary. Migrate every public mutation, then delete the legacy duplicate path.
- **If skipped:** Revisions, approvals, idempotency, and public status disagree about the same run.
- **Acceptance:** One end-to-end test must create, mutate, approve, query, resume, and restore the same run through public MCP APIs and one durable store.

### 5. [ ] Make run, migration, registry, and theme transitions crash-atomic

**Severity:** P1 data loss  
**Evidence:** `.omp/skills/ui-design-studio/scripts/studio.py:1556-1577`, `:1643-1723`, `.omp/skills/ui-design-studio/scripts/design_server.py:843-881`, `src/ui_design_studio/migration.py:273-369`, `src/ui_design_studio/theme_lifecycle.py:114-172`

- **What this is:** These flows perform read-modify-write operations across durable files.
- **Problem:** Scoped completion omits the records lock. Registry restore bypasses registration locking. Migration checkpoints can advance before copied bytes are durable. Activation retries can replace the true rollback locator. Theme restore deletes the target before validating the backup.
- **Fix:** Use one stable advisory lock per state domain. Journal multi-file transitions. Fsync copied bytes and parent directories before advancing checkpoints. Validate backup existence and digest before destructive changes.
- **If skipped:** Concurrent processes or a crash can lose cancellation, receipts, registry state, migration data, or installed themes.
- **Acceptance:** Add deterministic interruption tests at every write boundary and concurrent register/restore, cancel/complete, and migration-resume tests.

### 6. [ ] Enforce SQLite schema compatibility and durable outbox delivery

**Severity:** P1 data integrity  
**Evidence:** `src/ui_design_studio/storage/database.py:206-212`, `:498-516`

- **What this is:** SQLite stores commands, events, projections, and outbox delivery state.
- **Problem:** Startup overwrites existing schema metadata with `2.0.0` instead of validating or migrating it. Claimed outbox rows never return from `in_flight` after a consumer crash. Event delivery orders random IDs rather than append sequence.
- **Fix:** Reject unknown/newer schemas and migrate known older schemas transactionally. Add leases with expiry/reclaim. Persist an ordered event sequence and claim by that sequence.
- **If skipped:** Incompatible databases are silently relabeled, events can disappear forever, and dependent events can arrive out of order.
- **Acceptance:** Add newer-schema rejection, migration, crashed-consumer reclaim, duplicate consumer, and deterministic event-order tests.

### 7. [ ] Finish the artifact and approval transaction contract

**Severity:** P1 integrity  
**Evidence:** `src/ui_design_studio/application/commands.py:108-156`, `.omp/skills/ui-design-studio/scripts/design_server.py:791-840`, `:2110-2115`

- **What this is:** Approvals bind an actor, immutable bytes, annotations, dependency scope, and a run revision.
- **Problem:** `artifact.register` is advertised but unsupported. Approval commits do not verify blob bytes, discard canonical annotations/scope, and write attachments, decision, and request status separately. `rationale: null` raises uncaught `AttributeError`; oversized rationale enters every snapshot.
- **Fix:** Implement or remove artifact registration. Verify content digest at approval time. Persist annotations and scope fingerprint. Use one recoverable transaction or journal. Validate rationale type and size.
- **If skipped:** Corrupt or missing artifacts can be approved, annotation-only decisions cannot be replayed, and crashes leave permanently contradictory records.
- **Acceptance:** Add corrupt/missing blob, annotation-only, malformed rationale, oversized rationale, and interrupted-commit tests.

### 8. [ ] Enforce terminal governance and provider transitions

**Severity:** P1 accounting and concurrency  
**Evidence:** `src/ui_design_studio/domain/governance.py:107-128`, `:230-250`, `src/ui_design_studio/domain/provider.py:47-75`

- **What this is:** Budget reservations, worker leases, and provider attempts prevent duplicate work and charges.
- **Problem:** A settled reservation can settle again and double-count. Expired leases can heartbeat or publish outcomes. One provider attempt accepts multiple distinct receipts if charges match.
- **Fix:** Define terminal state machines. Reject all terminal rewrites. Check lease expiry before heartbeat/outcome. Bind exactly one provider receipt to one attempt.
- **If skipped:** Costs double-count, stale workers overwrite recovered work, and duplicate charges collapse into one attempt.
- **Acceptance:** Add repeated-settlement, receipt reuse, second-receipt, expired-heartbeat, expired-outcome, and fencing race tests.

### 9. [ ] Bound references, optimization results, snapshots, and subprocess work

**Severity:** P1 availability  
**Evidence:** `.omp/skills/ui-design-studio/scripts/design_server.py:335-394`, `:923-1021`, `:1268-1521`, `.omp/skills/ui-design-studio/scripts/optimization.py:487-538`, `:592-659`

- **What this is:** Each run retains references, artwork, decisions, history, optimization inputs, outputs, and compressed variants.
- **Problem:** Reference count and aggregate bytes are unbounded. Every snapshot rereads and hashes immutable content. HTML bundles load all dependencies into memory. Optimization keeps all result directories but exposes an arbitrary hash-sorted 128. Combined selectors read up to 64 inputs before rejecting the count.
- **Fix:** Add per-run count/byte quotas, per-bundle limits, streaming hashes/copies, immutable validation cache, creation-order result index, pruning, aggregate request budget, and bounded history.
- **If skipped:** Long runs cause repeated hundreds of MiB of I/O, memory exhaustion, disk growth, and fresh optimization links that immediately disappear.
- **Acceptance:** Add quota boundaries, >128 result retention, low-sorting fresh ID, large bundle, and bounded snapshot size/load tests.

### 10. [ ] Repair live update ordering, reconnect, and task provenance

**Severity:** P1 live correctness  
**Evidence:** `.omp/skills/ui-design-studio/dashboard/dashboard.js:254-263`, `:365-418`, `.omp/skills/ui-design-studio/scripts/design_server.py:1389-1396`, `.omp/extensions/ui-design-progress.ts:435-443`

- **What this is:** HTTP bootstrap, SSE, and OMP observer files feed the same dashboard state.
- **Problem:** An older HTTP response can overwrite a newer SSE frame. A connected stream never resets `streamConnected` after disconnect, so retry stops. Synthetic worker timestamps change every watcher tick, forcing full snapshots and unbounded history. Stale observer files have no liveness expiry.
- **Fix:** Compare monotonic snapshot generations before applying. Reset connection state in `finally`. Use source timestamps, not `now`, for projected workers. Add observer expiry and ownership checks.
- **If skipped:** Dashboards freeze, regress to stale decisions, churn every second, or show dead sessions as active.
- **Acceptance:** Browser tests must cover delayed HTTP versus SSE, established-stream EOF, reconnect, stable idle revision, and expired observer files.

### 11. [ ] Restore the control-port and selected-director boundaries

**Severity:** P1 security contract  
**Evidence:** `.omp/skills/ui-design-studio/scripts/design_server.py:1857-1968`, `:2121-2289`, `tests/test_design_server.py:225-258`, `:1200-1234`

- **What this is:** A loopback control listener should expose identity and shutdown only. Task projection should use the selected director or observer source.
- **Problem:** The control listener serves the public dashboard and preview routes. When the director pointer is absent, task discovery accepts a foreign `progress-pi-tasks.json` record. Both existing tests fail.
- **Fix:** Add an explicit GET allowlist for the control server. Keep director and observer directories separate and require exact run/session provenance.
- **If skipped:** The private control endpoint exposes unintended surfaces and unrelated session tasks appear in the run.
- **Acceptance:** Restore the two failing tests and add public/control route matrix tests.

### 12. [ ] Prevent private-tree packaging and milestone receipt forgery

**Severity:** P1 release security  
**Evidence:** `scripts/package_release.py:20-63`, `tools/run_prism_milestone_tests.py:14-23`

- **What this is:** Release packaging must exclude private data; milestone receipts must represent repository tests.
- **Problem:** `SKIP` is unused, so nested `.git`, `node_modules`, `__pycache__`, or `.DS_Store` files are packaged. The milestone runner allowlists only a basename, so `../outside/test_prism_m3.py` can execute external code and write a passing receipt.
- **Fix:** Reject skipped components during traversal. Resolve the requested test and require exact equality with `ROOT/tests/<allowed-name>`.
- **If skipped:** Archives can leak credentials/remotes, and release evidence can be forged by an external test file.
- **Acceptance:** Add nested-private-tree and external/absolute/path-traversal runner tests.

### 13. [ ] Restore release-evidence integrity

**Severity:** P1 release trust  
**Evidence:** `.prism-rebuild/MANIFEST.sha256`, `.prism-rebuild/knowledge/rules.json`, `tools/run_prism_m8_checks.py:12-23`, `.github/workflows/prism-release.yml:24-28`, `docs/VALIDATION.md:3-17`

- **What this is:** Manifests, milestone receipts, CI, and validation records are release claims.
- **Problem:** The rebuild pack manifest hash for `knowledge/rules.json` is stale, causing 19 setup errors. M8 hardcodes missing 2.0.0 artifact paths. CI writes a 2.0.0 ZIP for version 2.0.10 and regenerates the source manifest before checking it. Validation claims 14 browser tests and 185 hashes; current evidence is 15 and 201.
- **Fix:** Derive artifact names from `release.json`. Check the committed manifest before any builder mutates it, then assert a clean diff. Regenerate the rebuild manifest through its official finalizer. Refresh validation from current receipts.
- **If skipped:** Green CI and published validation do not prove the committed release.
- **Acceptance:** Rebuild-pack tests, M8, clean-manifest CI, and validation-count assertions must pass from a fresh clone.

## Should fix

### 14. [ ] Make optimization settings and results truthful

**Severity:** P2 product correctness  
**Evidence:** `.omp/skills/ui-design-studio/scripts/optimization.py:32-45`, `:90-124`, `:369-409`, `:476-501`, `.omp/skills/ui-design-studio/dashboard/dashboard.js:1304-1419`, `:2399-2405`

- **Problem:** `quality` is unused. Per-tool HTML/CSS/JS toggles are ignored. OptiPNG supersedes pngcrush rather than composing or choosing explicitly. `jpegoptim` writes to its existing source path and fails. Preset UI values conflict with backend defaults. Example POST ignores submitted unsaved settings. Result validation checks sizes, not hashes. SSE updates do not refresh a nonempty optimization panel.
- **Fix:** Delete inert controls or implement them. Make preset application one shared backend contract. Serialize writes, verify digests, and render only recorded artifacts.
- **If skipped:** Different settings yield identical or stale output while the UI claims otherwise.
- **Acceptance:** Parameterized tests must prove every exposed control changes the intended command/result or is absent.

### 15. [ ] Serialize dashboard async state and make draft persistence observable

**Severity:** P2 UI correctness and privacy  
**Evidence:** `.omp/skills/ui-design-studio/dashboard/dashboard.js:47-78`, `:656-679`, `:1081-1090`, `:1242-1285`, `:1647`, `:1790-1794`, `:2069-2120`

- **Problem:** Usage range responses can arrive out of order. Repeated requests create parallel poll chains. Text-reference previews race `showModal()`. SSE rerenders remove the stored focus target. Restored attachment IDs collide. Drafts duplicate base64 and data URLs, silently fail on storage errors, remain after submission, and contradict docs claiming memory-only edits.
- **Fix:** Add request generations/aborts, one owned polling timer, serialized dialog opens, stable focus identity, restored sequence calculation, one compact versioned draft, visible storage failure, and terminal cleanup.
- **If skipped:** Users see wrong ranges, broken dialogs, lost focus, rejected attachments, silent draft loss, or retained private screenshots.
- **Acceptance:** Browser tests must force delayed responses, storage exceptions/quota, multiple clicks, reload, SSE rerender, and confirmed submission cleanup.

### 16. [ ] Make usage telemetry safe and scalable

**Severity:** P2 security and performance  
**Evidence:** `.omp/skills/ui-design-studio/scripts/usage.py:145-190`, `:242-301`, `:303-330`

- **Problem:** Every record reparses and rewrites the full file, making append work quadratic. At 10,000 records or 8 MiB, new telemetry fails forever instead of applying retention. CSV cells can begin with spreadsheet formulas. `OMPUsageProbe.snapshot()` contains an unreachable duplicate block.
- **Fix:** Use SQLite/JSONL rotation or bounded append storage, implement declared dropped-record accounting, escape risky CSV text cells, cache projections by revision, and delete unreachable code.
- **If skipped:** Long runs get slower, permanently stop recording, and exported CSV can trigger formulas or external requests.
- **Acceptance:** Add max-retention rollover, 10k-record timing, formula-prefix, crash recovery, and installed/uninstalled OMP probe tests.

### 17. [ ] Align theme activation, knowledge selection, and runtime validation contracts

**Severity:** P2 contract integrity  
**Evidence:** `.omp/skills/ui-design-studio/scripts/studio.py:363`, `:1152-1164`, `:1686-1724`, `src/ui_design_studio/server.py:276-321`

- **Problem:** `activeTheme` is not schema-validated and can name an unregistered/stale theme. Registration writes activation-like metadata without a host adapter receipt. Public worker packets bypass knowledge-rule selection. Static CSS validation can pass without an adapter/runtime check.
- **Fix:** Separate registration from activation. Require a real adapter receipt before active state. Validate restored active themes. Route public packets through knowledge selection and record provenance. Require adapter-specific runtime evidence before release.
- **If skipped:** Registry state claims activation that the host never applied, workers miss shipped rules, and themes pass while runtime selectors fail.
- **Acceptance:** Add stale/unregistered active theme, adapter receipt, public packet provenance, and host adapter integration tests.

### 18. [ ] Expand CI to cover shipped behavior and actual artifacts

**Severity:** P2 regression risk  
**Evidence:** `.github/workflows/prism-release.yml:21-28`, `tests/test_mcp_package.py:24-33`, `tests/test_install.py:44-53`

- **Problem:** CI omits dashboard browser, Node extension, design server, global install/settings/cleanup, optimization, usage, and rebuild-pack suites. Wheels are tested from checkout, not from the extracted sdist. Installer tests use a tiny synthetic payload rather than shipped assets.
- **Fix:** Add isolated jobs for every shipped surface. Build a wheel from the extracted sdist and test it. Install the real source ZIP payload in a disposable project. Prevent duplicate push/PR runs.
- **If skipped:** Current regressions remain green, and sdists or production payloads can be incomplete.
- **Acceptance:** A fresh CI run must execute the exact commands in this audit and fail on each added regression fixture.

### 19. [ ] Bound and page dashboard/session projections

**Severity:** P2 performance  
**Evidence:** `src/ui_design_studio/dashboard.py:732-741`, `.omp/skills/ui-design-studio/scripts/design_server.py:1497-1521`, `:1820-1854`, `.omp/extensions/ui-design-progress.ts:184-192`

- **Problem:** Session listing scans every run with four workers. Status files and SSE frames copy full artwork, references, approvals, decisions, history, usage, and optimization projections. The extension rejects status above 8 MiB.
- **Fix:** Maintain a bounded indexed session projection. Keep live snapshots compact. Fetch collections through revision-bound pages already supported by `status_page`.
- **If skipped:** Latency and payload size grow with history until the OMP widget reports progress unavailable.
- **Acceptance:** Add 1k-run and large-history benchmarks with explicit latency, memory, and payload budgets.

## Nice to have

### 20. [ ] Remove stale generated docs, dead compatibility code, and fragile suppressions

**Severity:** P3 maintainability  
**Evidence:** `docs/documenter/01-overview.md:1-8`, `docs/RELEASE-v2.0.6.md:1-5`, `.omp/skills/ui-design-studio/scripts/studio.py:1505-1507`, `.omp/skills/ui-design-studio/scripts/optimization.py:140,415`, `src/ui_design_studio/server.py:131-132`, `.omp/extensions/ui-design-progress.ts:33-34`, `:387-395`, `:1120-1123`

- **Problem:** Fresh installs copy documentation claiming version 1.4.3. Release 2.0.6 has duplicate contradictory summaries. An ignored compatibility parameter remains. Brotli uses bare type suppressions. FastMCP private fields and handwritten host types are unversioned upgrade contracts. Broad catches hide discovery/timer failures.
- **Fix:** Regenerate or stop installing stale docs. Delete dead compatibility code after one declared window. Narrow suppressions. Add pinned dependency/host shape tests and visible diagnostics.
- **If skipped:** Operators receive contradictory docs, upgrades fail opaquely, and maintenance paths continue to diverge.
- **Acceptance:** Add documentation version/link validation, typed optional dependency checks, host-shape fixtures, and diagnostic tests.

## Remediation order

1. Findings 1–3: security and corrupt optimization output.
2. Findings 4–8: authoritative state, crash safety, approvals, accounting.
3. Findings 9–13: availability and release trust.
4. Findings 14–19: truthful UI, retention, contracts, CI, scale.
5. Finding 20: cleanup after behavior is stable.

## Release gate

Do not publish another release until all **Must fix** items pass their focused tests, the two current Python failures are fixed, the rebuild pack verifies, CI covers the new tests, the package manifest is clean before and after build, and current validation records match observed counts.

## Verdict

Incorrect for release. Fix findings 1–13 before shipping. The browser UI is visually well tested, but durable state, optimizer safety, release evidence, and concurrent runtime behavior need remediation first.

Lean: at least 15 lines can be removed immediately from the unreachable usage-probe block and ignored profile compatibility path. Larger deletion is possible after the duplicate legacy/SQLite mutation path is unified.

## Not checked

Native Windows/macOS behavior, physical second-device LAN behavior, real recipient applications, human usability research, third-party optimizer internals, and destructive crash tests on production data were not run. Historical documentation was sampled where it enters current installs or release claims; archival feature-freeze prose was not re-reviewed line by line.
