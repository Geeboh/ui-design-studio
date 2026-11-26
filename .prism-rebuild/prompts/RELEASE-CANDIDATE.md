# Qualify the completed PRISM release candidate

Reconcile all M0–M8 requirements and acceptance cases against actual evidence. Resolve implementation and review findings. Verify the intended source is committed and clean, version metadata is coherent, migration/rollback is proven, and the release plan maps every required case to real checks.

Build source ZIP, sdist and wheel using the rebuilt project's supported release tooling. Record exact source and artifact digests. Install them in isolated clean environments and complete the documented first-success, decision, revision and resume journeys. Verify actual OMP discovery/routing and MCP compatibility, authenticated dashboard behavior and the configured Chromium/Firefox/WebKit release matrix. Preserve meaningful security and performance evidence.

Obtain current review evidence, then execute the real release plan:

```bash
python3 .prism-rebuild/tools/run-gates.py --repo . --plan .prism-state/verification-plan.release.json --profile release
```

The plan must declare `targetProfile: "release"`. Inspect all results and captured artifacts. Confirm documentation matches the built package, no unavailable or skipped required test is counted as passed, and human participant testing is clearly deferred.

Produce the release-candidate handoff with changelog, supported environments, installation, migration, rollback, known limitations, artifact hashes and requirements coverage. Do not equate handoff-pack validation with application validation. Publish or merge only when that action is explicitly authorized in this session.
