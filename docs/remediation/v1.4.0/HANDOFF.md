# v1.4.0 Cortex remediation handoff

Status: `ENGINEERING_READY_UAT_PENDING`
Version: `1.4.0`
Baseline: `0f25a1e85cca1b7d61602f08f7b4a4c79f9746a3`
Current branch: `main`; remediation branch creation was blocked by shared-workspace policy.

## Summary

Implemented R01-R14 remediation code, tests, docs and benchmark evidence. Shared evidence validation now rejects stale bound inputs across engine, dashboard, MCP and registration. Routing normalization accepts all declared thinking key variants and preserves transactional restore behavior. MCP retains full status and adds bounded compact/paged status. Scoped runs record versioned closure without granting full-theme release. Coverage supports explained applicability. Resume manifests mark only changed dependency transitive nodes stale. Selected-role worker packets preserve original instructions and exact hashes. Offline quality checks are conditional on resolved project context. Early host feasibility is required before contract freeze.

## Install and migration

Use the existing project installer or local MCP package commands in `docs/INSTALLATION.md` and `docs/MCP.md`. New run records write scope fields, `manifest.json` schema 1.0 and model routing schema 1.2. Existing v1.0/v1.1 records remain readable. A missing manifest blocks resume conservatively. No global installation or publish occurred during remediation.

Run `tools/ui-design resume-check <run>` before continuing an interrupted dossier. Use `scope-complete` only for non-full-redesign work. Use `worker-packet` for bounded role context.
## Rollback

Use `models-restore` for routing changes. Installer backups and existing theme registry rollback remain authoritative. Revert the uncommitted working tree through the repository's approved process; do not overwrite user-owned settings or delete run history. No commit was created because shared-workspace policy blocked branch creation.

## Automated verification

Run `.venv/bin/python -m pytest -q`, `node --experimental-strip-types --test tests/test_progress_extension.mjs`, `bash -n install.sh tools/ui-design`, `.venv/bin/python scripts/package_release.py --check`, `sha256sum -c MANIFEST.sha256`, and `.venv/bin/python scripts/remediation_benchmark.py`. Exact results are in `TEST-REPORT.md`; measured synthetic values are in `BENCHMARKS.md` and `benchmarks.json`.

## Deferred testing

`UAT-DEFERRED.md` is authoritative. Human visual preference, usability, physical-device, native-host, production, deployment and release sign-off were not run and are not passed. Engineering completion does not require human sign-off.

## Known issues and blockers

- Git policy blocker: task branch creation was refused by shared-workspace policy; changes remain on `main` and uncommitted.
- Real application/browser/native host evidence was unavailable. This does not block automated source remediation, but it blocks claims about the target application's rendered usability or native behavior.
- Live provider execution was not performed. Routing tests use synthetic identities and do not prove external model availability.

## Final classification

`ENGINEERING_READY_UAT_PENDING`. Release, merge, deploy, publish, tag overwrite and human acceptance remain unauthorized or deferred.
