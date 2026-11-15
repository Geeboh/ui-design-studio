# Feature-freeze change history

The original dirty checkout remains untouched. All remediation commits are on `feature-freeze/2026-11-15-hardening`; nothing was merged, pushed or published.

| Commit | Verified logical unit | Findings |
| --- | --- | --- |
| `747d3eed029` | Protected baseline, rollback and audit gates | Baseline |
| `5fef92d097` | Shared workflow, filesystem and MCP boundaries | FF-001–005, FF-007, FF-010 |
| `1e137f6658` | Retained artwork identity and nested cleanup | FF-006, FF-009, FF-017 |
| `7ebd26664d` | Selected and owned probe scheduling | FF-008 |
| `3d47815bc3` | Private package inputs and recoverable output publication | FF-014–016 |
| `700cc01362` | Selection, browser polling and keyboard focus | FF-018–020 |
| `d1f6923ee4` | Routing contracts, provenance and benchmark method | FF-011–013 |

Final report reconciliation and regenerated source manifest follow these units. The defect register identifies each finding's correction commit. No unrelated product feature or speculative refactor was added.
