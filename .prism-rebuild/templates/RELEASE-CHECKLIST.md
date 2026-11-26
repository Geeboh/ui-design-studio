# PRISM release-candidate checklist

This checklist is a navigation aid. Actual mapped acceptance cases, executed gates and retained evidence determine readiness.

## Candidate

- [ ] Target version and compatibility scope recorded from one canonical version source.
- [ ] All M0–M8 deliverables reconciled against the requirement ledger.
- [ ] Intended source committed and clean; source and plan fingerprints recorded.
- [ ] Required review completed with actor provenance and zero unresolved severe findings.
- [ ] Sequential review fallback, if used, explicitly disclosed and labelled.

## Behavior

- [ ] CLI, MCP and dashboard use the same command validation and canonical state.
- [ ] Optional feedback, approval races, dependency currentness and stale submissions proven.
- [ ] Exact-base annotations/revisions and stable component partial approval proven.
- [ ] Design money, reservations, settlement, unknown provider outcomes and refunds proven.
- [ ] Model-default persistence, current-model mode, actual routing and bounded workers proven.
- [ ] Theme lifecycle, knowledge retrieval and recovery preserve user state.

## Migration and delivery

- [ ] Copy-first legacy import, restart and rollback checked with representative fixtures.
- [ ] SQLite runtime/source identity and chosen local journal policy qualified.
- [ ] Source ZIP extracted outside the checkout and checked there.
- [ ] sdist built, wheel built from sdist, wheel installed in a fresh environment.
- [ ] Installed commands exercised from a nonrepository directory.
- [ ] Actual OMP discovery and MCP host integration verified separately from packaging.
- [ ] Install/upgrade/restore preserve project instructions and later customizations.
- [ ] Archives contain required runtime resources and exclude private state/sourcebooks.

## Browser and operations

- [ ] Real browser interactions verified for critical flows and failure/recovery states.
- [ ] Configured Chromium/Firefox/WebKit release matrix completed.
- [ ] Keyboard, focus, nondrag controls, reflow, contrast and reduced-motion checks recorded.
- [ ] Auth, origin/CSRF, escaping, capability, path and process-ownership boundaries checked.
- [ ] Performance measured with named fixtures, warm/cold distinction and environment.
- [ ] No missing/blocked/skipped required check is counted as passed.
- [ ] Human participant research explicitly remains deferred.

## Handoff

- [ ] Full release profile executed against the reviewed candidate and plan.
- [ ] Current status rechecks retained logs, reports, review and plan identity.
- [ ] Changelog, installation, first success, migration, recovery and limitations match artifacts.
- [ ] Source and artifact hashes recorded with support/environment matrix.
- [ ] Publication/merge authority checked separately if that action is requested.
- [ ] Post-publication smoke checks and support receipts prepared for an authorized release.
