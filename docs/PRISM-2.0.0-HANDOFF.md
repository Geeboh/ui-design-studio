# PRISM Studio 2.0.0 release handoff

## Candidate

- Branch: `overhaul/prism-v2`.
- Candidate commit: the clean `HEAD` is recorded by the release runner and `.prism-state/progress.json`.
- Source fingerprint: recorded in `.prism-state/progress.json` and the release receipt.
- Verification plan: `.prism-state/verification-plan.json`.
- Human participant research: deferred by project policy.

## Evidence

- Current focused M0 preflight, M1 core, M2 migration, M3 workflow, M4 governance, M5 browser, M6 knowledge/theme/performance, M7 distribution/security, and M8 artifact checks passed.
- The dashboard browser matrix passed 14 tests in each of Chromium, Firefox, and WebKit. A Playwright Fast visual capture produced `.prism-state/dashboard-visual.png`.
- The standalone OMP host regression passed 52 of 52 tests.
- The current artifact hashes are recorded in `.prism-state/release-artifacts.txt`.
- The wheel rebuilt from the extracted sdist matched the direct wheel hash. The source ZIP extracted without private runtime paths.

## Open release blocker

The release profile remains blocked by `.prism-state/release-review.json`. The remaining gaps are full zoom/state accessibility coverage, live OMP session qualification, complete acceptance mapping, and substantive release evidence for every mapped case.

The release runner reports:

```text
Review has unresolved severe findings or does not recommend readiness
```

Recovery action. Resolve the listed semantic gaps. Refresh every acceptance mapping against the clean candidate. Run the release profile and the required browser matrix. Do not mark the review ready before those results.

## Rollback

For source installation, keep the prior project files and the install receipt. Use the existing `scripts/install.py restore` flow. For migrated state, use `docs/MIGRATION-AND-ROLLBACK-v2.0.0.md`; rollback refuses divergent later writes. Do not overwrite a candidate with later writes.
