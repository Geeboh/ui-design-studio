# Remediation plan

1. Preserve baseline and user changes. Completed in an isolated worktree.
2. Inventory all 116 tracked paths and obtain independent risk-slice reviews. In progress.
3. Execute central baseline gates. Python and Node passed; additional pytest-only contracts remain to run.
4. Fix confirmed release-acceptance and coverage defects with failing regressions before corrections.
5. Resolve remaining confirmed security, correctness, lifecycle, installation and documentation findings by severity.
6. Verify each logical unit and commit using selective ownership-aware commits.
7. Run full practical release checks, inspect actual dashboard behavior, and obtain fresh remediation review.
8. Reconcile every finding and all requested documents against final evidence.

Throughput checkpoint: four independent read-only review slices run while the parent owns workflow fixes and central validation. Source writes remain single-owner until bounded independent fixes are assigned. Tool results wake this run; no polling watcher is needed for local finite checks.

No speculative rewrites or performance claims without comparable measurements. Human acceptance and native platform checks remain explicitly separate from automated engineering readiness.
