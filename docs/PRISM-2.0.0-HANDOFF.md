# PRISM Studio 2.0.0 release handoff

## Candidate

- Branch: `overhaul/prism-v2`.
- Commit: `bf817021f2d146e16ae62488e678297a2267694e`.
- Source fingerprint: `4e35ce6d0c6dd06579dbdae98afbc039d101680dde7e6103f9d947a08e64ebff`.
- Verification plan: `.prism-state/verification-plan.json`.
- Human participant research: deferred by project policy.

## Evidence

- Core G0-G4 passed before the final clean commit. The same command bindings, source bytes and test receipts are retained under `.prism-state/evidence/`.
- Web G0-G7 passed before the final clean commit. The dashboard browser suite passed 10 tests. The Playwright Fast capture produced `.prism-state/dashboard-visual.png`.
- Package, install, MCP, dashboard security, and source distribution checks passed in the isolated `.venv-prism` environment.
- Final artifact hashes are in `.prism-state/release-artifacts.txt`.

## Open release blocker

The actual OMP host regression remains open. `node --test tests/test_progress_extension.mjs` fails 17 of 52 tests. Several cases do not observe dashboard child readiness or run selection. The failures reproduce in a standalone run without concurrent gate activity.

The release profile is therefore intentionally blocked by `.prism-state/release-review.json` and reports:

```text
Release review has unresolved severe findings or does not recommend readiness
```

Recovery action. Trace `dashboardRuntime()` and readiness handling in `.omp/extensions/ui-design-progress.ts` with the failing fixtures. Fix the root cause. Rerun the complete Node host regression and the `release` profile against the same clean candidate. Do not mark the review ready before that result.

## Rollback

For source installation, keep the prior project files and the install receipt. Use the existing `scripts/install.py restore` flow. For migrated state, use `docs/MIGRATION-AND-ROLLBACK-v2.0.0.md`; rollback refuses divergent later writes. Do not overwrite a candidate with later writes.
