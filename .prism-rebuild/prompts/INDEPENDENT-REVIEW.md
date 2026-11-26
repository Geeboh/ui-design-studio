# Review the PRISM candidate and its acceptance mapping

Review the actual candidate and verification plan as a separate reviewer. Establish your actor identity and the implementation actors. Read applicable instructions and the changed subsystem's requirements/contracts. Inspect the diff, important unchanged boundaries, tests, package contents, migrations and captured results. Do not accept a claimed pass without inspecting what was executed and asserted.

Check in particular: approval and dependency scope; currency/rounding/reservations; concurrent and uncertain outcomes; authorization and input handling; install/restore ownership; legacy preservation; real host/browser behavior; and evidence tied to the actual packaged candidate. Verify that every required acceptance case maps to a meaningful test or documented inspection and that no hidden skip is counted as a pass.

First resolve the plan's `review.reviewer` and `review.independent` fields. Commit the intended source candidate. Obtain the exact source and plan hashes with:

```bash
python3 .prism-rebuild/tools/run-gates.py --repo . --plan .prism-state/verification-plan.json --fingerprint
```

Write review evidence in the shape documented in `.prism-rebuild/docs/QUALITY-AND-RELEASE.md`, using `.prism-rebuild/templates/REVIEW.example.json` as structure only. Record every required acceptance ID, its result, substantive note and existing evidence paths. Report actual severe open findings. Recommendation is `ready` only when the candidate and evidence support it.

If independent execution is unavailable, a separate sequential pass is permitted only with `method=declared-sequential-fallback`, an explicit reason and `recommendation=ready-with-disclosed-fallback` when otherwise justified. Do not invent another actor or label the pass independent. Any source/plan change after the review requires reconciliation and affected re-review.
