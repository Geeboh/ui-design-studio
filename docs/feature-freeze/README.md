# Feature freeze

Status: local engineering remediation complete. CONDITIONALLY READY for the reviewed Linux scope, not an unconditional release approval. All 43 confirmed findings are corrected or have completed documentation dispositions: four High, 29 Medium and ten Low. External acceptance and setup-recovery limits remain explicit in [BLOCKERS.md](BLOCKERS.md).

The current remediation branch is `feature-freeze/2026-11-16-audit-unique` in `/code/ui-design-freeze-20261116-UKWQB8`. It includes prior remediation through `5b1d7313247eb33bae5319c4be72c63ef809357b`. Original user edits remain in the original checkout. The setup incident and its recovery limits are recorded in [BASELINE.md](BASELINE.md).

| Record | Purpose |
| --- | --- |
| [Baseline](BASELINE.md) | Starting state and rollback |
| [Inventory](INVENTORY.md) | Complete inspection coverage |
| [Audit](AUDIT.md) | Confirmed technical findings |
| [Defect register](DEFECT-REGISTER.md) | Severity, disposition, evidence and commit |
| [Remediation plan](REMEDIATION-PLAN.md) | Ordered engineering work |
| [Test matrix](TEST-MATRIX.md) | Actual validation and coverage |
| [Architecture](ARCHITECTURE-REVIEW.md) | Boundaries and maintenance risks |
| [Security](SECURITY-REVIEW.md) | Threat model and safety findings |
| [Performance](PERFORMANCE.md) | Measurements and their limits |
| [Change history](CHANGELOG.md) | Verified remediation units |
| [Release readiness](RELEASE-READINESS.md) | Final gate assessment |
| [Blockers](BLOCKERS.md) | Exact remaining requirements |
| [Original review evidence](REVIEW-EVIDENCE.json) | Fourteen current reports with exact scope and dispositions |
| [Security evidence](SECURITY-EVIDENCE.json) | Current scan, dependency records and 77 source identities |

`decisions.tsv` records material decisions. No default-branch merge, deployment or publication occurred during the original freeze audit. The later explicit ShipIt request authorizes one independently verified PR merge; package publication and deployment remain excluded.

## Current checkout note

Current revalidation runs on `main` at `5a3c603e4f95c884d5b0535eb4aa52c2a7ff62c4` (`v1.4.2`). The historical audit branch named above is not the active checkout. See [CONTINUATION](CONTINUATION.md), [MODEL-ROUTING](MODEL-ROUTING.md), [MODEL-ESCALATIONS](MODEL-ESCALATIONS.md), and [MODEL-USAGE](MODEL-USAGE.md) for current state.
