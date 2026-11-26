# Baseline findings and required fixes

This is the implementation starting point from the review of UI Design Studio **1.4.3**, commit `60307ef31fd6e2bad1d39620fc507b0b822e281a`. It is not a claim that these findings still apply to an unknown later checkout. M0 must inspect the selected commit, reproduce each applicable issue, and mark it confirmed, already fixed, changed, or not reproducible with an explanation.

The review combined source inspection, targeted reproductions, package inspection and resource synthesis. Environment-dependent test failures were separated from product defects. Old aggregate test counts are not release evidence for the rebuilt product.

## Priorities

| Priority | Finding | Why it matters | Required destination |
| --- | --- | --- | --- |
| P0 | Optional approval feedback accepted during submission but rejected when checking whether the decision is current | A successful user action can immediately become unusable | REQ-APPROVAL-001, REQ-CORE-001 |
| P0 | Whole-run digest participates in stale-request checks while decisions use narrower input checks | Unrelated work can invalidate a review; clients disagree on currentness | REQ-APPROVAL-002, REQ-APPROVAL-004 |
| P0 | Resume assumes roots/checkpoints and includes incidental repository state | Safe continuation can block or target the wrong context | REQ-INSTALL-003, REQ-EVIDENCE-001, REQ-WORKER-005 |
| P0 | A distributed test depends on a root document omitted from the source ZIP | Checkout success does not establish installable release success | REQ-INSTALL-005–007 |
| P1 | Annotation endpoint, payload-limit and coordinate contracts differ across browser/server | The requested correction may point to the wrong area or fail on ordinary drawing | REQ-REVISION-001–003 |
| P1 | Worker packets omit applicable instructions, reject new target paths and hardcode concurrency | Delegation can violate project rules or fail on normal implementation tasks | REQ-WORKER-001–005 |
| P1 | Loopback startup still depends on LAN interface discovery | A restricted host can fail before serving a local-only dashboard | REQ-SECURITY-006, REQ-INSTALL-004 |
| P1 | Legacy/unbound validation evidence can appear fresh | Readiness can be overstated for the current source | REQ-EVIDENCE-001–005 |
| P1 | Global engine and project payload lack a sufficient compatibility handshake | Mixed versions can fail late or interpret state differently | REQ-CORE-007, REQ-INSTALL-004 |
| P1 | Full snapshots repeatedly read unchanged artwork and grow history in memory | Polling becomes expensive with run size | REQ-PERF-001–004 |
| P2 | Release/validation documentation and version metadata are duplicated | Instructions and packaged behavior drift | REQ-DOCS-002–003, REQ-INSTALL-007 |
| P2 | Skills load too much historical/reference context | Repeated sessions pay for irrelevant material and obscure current instructions | REQ-KNOWLEDGE-001–004 |

P0/P1 here describe rebuild priorities, not an unverified severity score for a security incident. A regression that corrupts decisions, charges money twice, loses data or creates false release evidence blocks the relevant milestone.

## Reproduction contracts

### 1. Approval feedback and currentness

Inspect `current_decision()` and the approval POST handler in `.omp/skills/ui-design-studio/scripts/design_server.py`, plus the decision creation path in `scripts/studio.py` under the same skill. Submit an otherwise valid approval with omitted feedback, `null`, an empty string and whitespace. Follow with the next authorized action and reload the dashboard.

Expected rebuilt behavior: optional feedback normalizes consistently; an empty rationale does not invalidate an approval. Missing required rationale for a different decision type should fail at the shared command boundary with an actionable error. Rejections, annotations and artifact identities are independent fields. CLI, MCP and dashboard must use that same boundary.

Source: [baseline design server](https://github.com/Geeboh/ui-design-studio/blob/60307ef31fd6e2bad1d39620fc507b0b822e281a/.omp/skills/ui-design-studio/scripts/design_server.py), [baseline studio engine](https://github.com/Geeboh/ui-design-studio/blob/60307ef31fd6e2bad1d39620fc507b0b822e281a/.omp/skills/ui-design-studio/scripts/studio.py).

### 2. Dependency-scoped decisions

Create an approval request against a particular artifact version. Change unrelated stage metadata or another independent component. The original request must remain actionable. Then revise its actual input artifact or relevant dependency; the original request must become stale with the changed dependency identified. Race the revision with approval and verify exactly one serializable outcome.

Preserve the historical decision even when it no longer applies. The rebuilt API must report the recorded decision, its current applicability, relevant versions, allowed actions and disabled reasons separately. A whole-run digest is useful as a snapshot identity; it is too broad to serve as every decision's validity predicate.

Source: the same baseline server's request/decision currentness and snapshot digest paths. Target: [domain contracts](DOMAIN-CONTRACTS.md) and [design governance](DESIGN-GOVERNANCE.md).

### 3. Annotation geometry and focused revisions

Inspect `.omp/skills/ui-design-studio/dashboard/dashboard.js` and the server annotation validator. Draw an arrow with multiple pointer samples, a long freehand mark and a mark on a letterboxed image. Resize the viewport, switch comparison views and reload.

The original browser used the early sampled point for an arrow endpoint; server point limits could reject a normal long stroke; normalized stage coordinates did not reliably denote the same source-image location. The rebuilt contract must use shape-specific geometry, bounded simplification, image-local normalized coordinates, exact artifact version and intrinsic dimensions. Test aspect-ratio changes and a keyboard/single-pointer alternative. A focused revision must reuse the pinned original as a reference input, preserve accepted unaffected regions, and show the before/after change with a stated scope.

Source: [baseline dashboard](https://github.com/Geeboh/ui-design-studio/blob/60307ef31fd6e2bad1d39620fc507b0b822e281a/.omp/skills/ui-design-studio/dashboard/dashboard.js) and the baseline server's annotation validation.

### 4. Worker packets, new files and concurrency

Build a worker packet for an existing source file, a new source file that does not yet exist, and a new output artifact. Confirm that applicable project/ancestor instructions, task constraints, required references, expected input revisions and owned paths arrive intact. Try an escaping path and overlapping write ownership. Change configured concurrency and available host capacity.

At baseline, default context/routing inputs did not include the complete applicable instruction chain; path validation conflated existing inputs with valid future outputs; dispatch used a fixed worker count. Rebuild with separate validation for existing read inputs and contained future write targets. The scheduler must honor both configured and observed capacity, reserve necessary money before paid dispatch, and reject conflicting ownership.

Source: packet/dispatch functions in the [baseline studio engine](https://github.com/Geeboh/ui-design-studio/blob/60307ef31fd6e2bad1d39620fc507b0b822e281a/.omp/skills/ui-design-studio/scripts/studio.py).

### 5. Resume and project roots

Exercise a Git checkout, a worktree, a nested path, an explicitly selected non-Git project if still supported, a changed unrelated commit, changed relevant inputs, a changed generated manifest, interrupted work and repeated resume. Check the recorded root, dependency closure and checkpoint after each meaningful operation.

The baseline guessed roots in some paths, could include generated/dirty state in its own invalidation criteria, tied some freshness checks to broad Git movement, and initialized a checkpoint without a sufficient continuing lifecycle. Rebuild with explicit project identity, stable dependency IDs, last committed domain revisions and source-bound evidence. Do not suppress real changed-input detection merely to make resume green.

### 6. Distribution isolation

`scripts/package_release.py` includes selected top-level files and trees. `tests/test_remediation_contract.py` requires the root document `UI-Design-Studio-v1.4.0-Cortex-Remediation.md`; that document was not in the source ZIP's top-level allowlist. A clean extraction therefore differs from the tested checkout.

The rebuilt gate must create a source ZIP, extract it outside the source tree and run the supported source workflow there. Separately build an sdist, build a wheel from that sdist, install the wheel in a fresh environment and execute from a nonrepository directory. Decide explicitly whether historical remediation documents belong in a source distribution; do not silently leave a test dependent on an absent file.

Source: [baseline packager](https://github.com/Geeboh/ui-design-studio/blob/60307ef31fd6e2bad1d39620fc507b0b822e281a/scripts/package_release.py), [baseline remediation test](https://github.com/Geeboh/ui-design-studio/blob/60307ef31fd6e2bad1d39620fc507b0b822e281a/tests/test_remediation_contract.py).

### 7. Network-independent local startup

Inspect LAN address discovery and dashboard startup in `src/ui_design_studio/dashboard.py`. In a restricted environment, deny interface enumeration while permitting loopback serving. Local mode must start without requiring successful LAN enumeration. Explicit LAN mode must report exposure and failures truthfully.

New installs default to loopback as a deliberate product change. Preserve an existing explicit LAN configuration during migration; do not silently reinterpret an owner's chosen deployment. Do not weaken authentication or host/origin checks as a shortcut around startup problems.

Source: [baseline dashboard host](https://github.com/Geeboh/ui-design-studio/blob/60307ef31fd6e2bad1d39620fc507b0b822e281a/src/ui_design_studio/dashboard.py).

### 8. Snapshot and history cost

Use a fixed fixture with many unchanged artifacts, then measure a cold snapshot, a warmed repeated snapshot, a history page, a single update and a compact MCP read. In the review, a fixture containing twenty 256 KiB artifacts caused a warmed snapshot to reread roughly 5 MiB of unchanged artwork. This is a workload observation, not a general latency benchmark.

Move large artwork out of frequently polled JSON, cache by immutable identity, use paged history with stable cursors, bound retained projections and avoid building a full result merely to discard most fields for a compact response. Measure actual reads, bytes, latency and memory under the same fixture before and after. Choose budgets in M0; do not invent universal timing numbers.

### 9. Evidence, host integration and documentation

Legacy evidence without a source binding cannot automatically become fresh. A green unit suite does not demonstrate OMP discovery, an installed MCP package, a browser flow or an extracted release. The baseline did not provide a complete checked-in CI path for those claims, and its historical validation documents could be mistaken for current qualification.

The rebuild must negotiate runtime/schema capabilities at boundaries, publish one canonical version source, retain old records as historical, and produce exact-candidate evidence for supported distributions and live host integration. Separate `NOT_RUN`, `BLOCKED`, `STALE`, `DEFERRED` and observed passes. Preserve a declared sequential review fallback only when a separate reviewer is unavailable; never relabel it independent.

## Strengths to retain

The repository already contains useful authentication, CSP/escaping, path-containment, owned-process/resource cleanup, transactional installation and restore, theme-state preservation and portable MCP work. Preserve and regression-test those boundaries. The rebuild is a deliberate consolidation of a useful foundation, with legacy behavior retained where it is safe and documented.

The proposed design budget, exact-base revision workflow, component-level partial approval, persistent model policy and knowledge retrieval go beyond repairing the listed defects. They are explicit product requirements in [the requirement catalogue](../contracts/requirements.json), not features assumed to exist at baseline.
