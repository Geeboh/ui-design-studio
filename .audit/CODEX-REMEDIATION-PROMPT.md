# Codex remediation prompt

Copy the prompt below into Codex from the repository root.

```text
You are remediating PRISM Studio in `/code/helpers/ui-design-studio-prism`.

Read and obey all applicable AGENTS.md files. Read `.audit/CODE-REVIEW-REMEDIATION.md` completely before editing. Treat every unchecked item as required scope. Do not narrow the task, preserve compatibility with version 2.0.10 only where it does not preserve a defect, and do not publish a release until the final gate passes.

Objective

Remediate all 20 workstreams in `.audit/CODE-REVIEW-REMEDIATION.md`. Fix root causes. Add behavioral tests that fail on the documented concrete cases. Update user-facing documentation and current release validation from observed evidence. Delete obsolete compatibility paths after migrating callers. Do not add frameworks or abstractions unless the checklist proves they are necessary.

Required execution order

Phase 0 — Baseline and ownership
1. Confirm the working tree and current branch.
2. Reproduce and record the two current Python-suite failures and the rebuild-pack manifest failure.
3. Create a task plan mapping every checklist number to owned files, test files, and acceptance evidence.
4. Split file ownership before parallel work. Keep shared contracts under one owner.

Phase 1 — Security and output integrity
1. Fix filesystem containment for lifecycle/migration IDs and StateStore roots.
2. Separate optimized bytes from gzip/Brotli artifacts.
3. Remove unsafe lexical JS/CSS transforms unless a syntax-aware implementation is available.
4. Make SVG sanitization mandatory and feed only sanitized bytes to later tools.
5. Add path traversal, symlink, semantic minification, MIME/header, decompression, and malicious SVG tests.

Phase 2 — Authoritative durable state
1. Choose the SQLite command engine or legacy run engine as the single public authority. Migrate every public mutation in one cutover and delete the duplicate path.
2. Bind actor and project scope at the adapter boundary.
3. Make run, migration, registry, theme, approval, and artifact transitions lock-safe and crash-recoverable.
4. Add schema compatibility checks, ordered event sequence, outbox leases/reclaim, and projection compare-and-retry.
5. Make governance/provider transitions terminal and receipt-bound.
6. Add deterministic concurrency and interruption tests for every write phase.

Phase 3 — Availability and live state
1. Add aggregate reference, bundle, optimization, history, and snapshot quotas.
2. Use creation-order retention and prune old optimization directories.
3. Fix SSE generation ordering, established-stream reconnect, stable idle revisions, and observer expiry.
4. Restore the shutdown-only control listener allowlist and selected-director task provenance.
5. Page large collections and benchmark 1,000 runs plus long histories.

Phase 4 — Release trust
1. Filter private path components from archive traversal.
2. Constrain milestone test paths to exact repository files.
3. Repair `.prism-rebuild/MANIFEST.sha256` through the pack’s supported finalization workflow.
4. Derive M8 and CI artifact names from `release.json`.
5. Check the committed source manifest before any builder rewrites it. Assert no post-build source diff.
6. Build and test a wheel from the extracted sdist.
7. Install and test the real source-ZIP payload in a disposable project.
8. Add every shipped suite to CI, including browser matrix, Node extension, design server, global install/settings/cleanup, optimization, usage, and rebuild pack.

Phase 5 — UI, telemetry, contracts, and cleanup
1. Serialize dashboard requests and dialogs. Fix draft persistence, cleanup, focus restoration, attachment IDs, usage range races, and duplicate polling chains.
2. Implement or remove every optimization control. Share preset semantics between backend and UI. Verify result hashes.
3. Move usage telemetry to bounded append/SQLite storage and protect CSV text cells from formulas.
4. Separate theme registration from adapter activation. Validate active themes and record adapter receipts.
5. Route public worker packets through knowledge selection with provenance.
6. Refresh generated docs and validation counts. Delete dead compatibility and unreachable code. Narrow type suppressions and broad catches.

Engineering constraints

- Correctness first. Keep the smallest complete design.
- No silent fallback that reports PASS.
- No shims, aliases, stale re-exports, TODOs, placeholders, or narrowed tests.
- Validate untrusted input once at boundaries. Trust internal typed values afterward.
- Preserve atomic writes, content digests, idempotency, and repository confinement.
- A successful helper command is not release evidence unless its output is current, immutable, and mapped to the acceptance case.
- Do not weaken security checks to make tests pass.
- Do not modify historical evidence to claim a result that was not rerun. Mark it historical or produce fresh evidence.

Mandatory behavioral cases

At minimum add tests for:
- `../` and symlink path escapes.
- HTML `after` bytes versus gzip/Brotli bytes and headers.
- JavaScript automatic-semicolon-insertion and regex/comment cases.
- CSS `calc()` and quoted URL cases.
- SVG event attributes, scripts, external URLs, and external optimizer ordering.
- Concurrent cancel/complete, register/restore, optimization requests, approval writes, and projection rebuild/update.
- Crash after each migration/theme/approval write boundary.
- Newer SQLite schema, crashed outbox consumer, event ordering, and stale projections.
- Repeat settlement, second receipt, expired lease, and fencing.
- >128 optimization results, large references/bundles, quota rejection before reads, and bounded disk cleanup.
- HTTP versus SSE ordering, stream EOF reconnect, idle revision stability, and expired observer records.
- Control-port route matrix and exact selected-director provenance.
- Nested `.git`/`node_modules` archive content and external milestone test paths.
- LocalStorage failure/quota, duplicate attachment restoration, dialog races, stale usage responses, and draft deletion.
- Formula-prefixed CSV values.
- Extracted-sdist wheel and real installer payload parity.

Verification commands

Use the repository-defined environment. Run affected tests during fixes. After the last edit, run each final gate once:

1. Non-browser suite:
   `PYTHONPATH=src:tests .runtime/venv-prism/bin/python -m pytest -q tests --ignore=tests/test_dashboard_browser.py`
2. Browser matrix:
   `PYTHONPATH=src:tests .runtime/venv-prism/bin/python tools/run_prism_browser_tests.py`
3. OMP extension:
   `node --test tests/test_progress_extension.mjs`
4. Rebuild pack:
   `.runtime/venv-prism/bin/python -m pytest -q .prism-rebuild/tools/test_tools.py`
5. Static checks:
   `.runtime/venv-prism/bin/python -m compileall -q src .omp/skills/ui-design-studio/scripts scripts tools`
   `node --check .omp/skills/ui-design-studio/dashboard/dashboard.js`
   `node --check .omp/skills/ui-design-studio/dashboard/landing.js`
   `bash -n install.sh tools/ui-design`
   `.runtime/venv-prism/bin/python -m pip check`
6. Manifest before build:
   `.runtime/venv-prism/bin/python scripts/package_release.py --check`
7. Build wheel, sdist, and source ZIP into `.runtime/dist/remediation-release`; verify ZIP CRC, checksum sidecar, private-path exclusion, extracted-sdist wheel, and installed CLI/MCP smoke tests.
8. Manifest and clean source after build:
   `.runtime/venv-prism/bin/python scripts/package_release.py --check`
   `git diff --check`
   Confirm the build did not silently repair a stale committed manifest.
9. Security scans: rerun Semgrep and Trivy. Triage false positives with concrete permission/path evidence.
10. Inspect CI results for every supported Python and browser lane.

Completion contract

Return:
- checklist numbers completed;
- exact files changed;
- tests added for each concrete failure;
- commands run and observed results;
- current manifest/artifact hashes;
- unresolved gaps with precise blockers;
- independent review verdict.

Completion is forbidden while any Must fix item is open, any final command fails, validation claims are stale, or the working release artifact was not built from the exact reviewed source.
```
