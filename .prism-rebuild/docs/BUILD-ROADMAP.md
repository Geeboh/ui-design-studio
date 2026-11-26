# Build roadmap and acceptance ownership

## Objective and completion boundary

Build UI Design Studio 2.0.0, working name PRISM Studio, as an incremental replacement of the reviewed 1.4.3 implementation. Keep the useful Python engine, CLI/MCP interfaces, authenticated dashboard, OMP installation, theme lifecycle and compatibility aliases. Introduce a shared domain core and transactional state behind those surfaces. A new frontend framework, remote service fleet or message broker is not a prerequisite.

This document is an implementation plan. The pack contains **86 requirements, 96 acceptance scenarios, nine milestones and nine gates**; it does not contain the completed application or passing product evidence. The authoritative traceability files are [requirements](../contracts/requirements.json), [acceptance cases](../contracts/acceptance-cases.json), [milestones](../contracts/milestones.json) and [gates](../contracts/gates.json). The [example verification plan](../config/verification-plan.example.json) deliberately has no runnable gate bindings and no review evidence. It must fail product readiness until implementation and verification exist.

Read [the implementation playbook](IMPLEMENTATION-PLAYBOOK.md) for the per-task working loop, [architecture](ARCHITECTURE.md) for boundaries, and [quality and release](QUALITY-AND-RELEASE.md) for what counts as evidence. Requirements are proposed product policy unless their source record identifies a baseline finding, project instruction or external reference.

## Dependency and ownership map

| Milestone / gate | Primary outcome | Dependencies | Requirements | Main implementation owner |
|---|---|---|---:|---|
| M0 / G0 | Candidate identity, discovery, capability and evidence baseline | None | 2 | Integration lead and QA |
| M1 / G1 | Shared commands, transactions, idempotency and artifacts | M0 | 7 | Domain/state owner |
| M2 / G2 | Copy-first migration, recovery and rollback | M1 | 5 | Migration owner |
| M3 / G3 | Approvals, annotation contracts and focused revisions | M1, M2 | 12 | Workflow owner with dashboard liaison |
| M4 / G4 | Design budget, model policy and scoped workers | M1, M3 | 17 | Governance/dispatch owner |
| M5 / G5 | Real dashboard interactions and accessibility | M3, M4 | 11 | Dashboard owner and browser QA |
| M6 / G6 | Knowledge selection, theme lifecycle and performance | M4, M5 | 11 | Context/theme owners with performance QA |
| M7 / G7 | Isolated distributions, host integration and operational security | M2, M5, M6 | 15 | Installation/security owners |
| M8 / G8 | Current-candidate release evidence and handoff | M0–M7 | 6 | Integration lead and distinct reviewer, or declared fallback |

There is one owner for shared schema and command-contract changes. Other streams propose changes with affected requirement IDs and consequences; they do not independently introduce incompatible payloads. A worker packet includes owned paths/components, relevant instruction snapshots, input revisions, dependencies, acceptance IDs, effective model policy and allowed operations.

Parallelism follows actual host capacity, disjoint ownership and available budget. The example build policy's worker count is a configurable starting point for rebuilding the product, not the product's hardcoded concurrency limit. If no subagent capability exists, run explicit sequential role passes and report them as such.

## M0 — Establish a concrete baseline

**Requirements:** REQ-DOCS-001 and REQ-EVIDENCE-001.

Use the prepared worktree, preserve the original checkout, and read its actual instructions before editing. Record the selected commit and any differences from reviewed baseline `60307ef31fd6e2bad1d39620fc507b0b822e281a`. A defect already repaired at the selected candidate becomes a retained regression target, not a reason to reintroduce the old implementation.

Inventory the public entry points, schemas, Python package resources, OMP payload/discovery surfaces, dashboard routes, install/restore commands, theme operations, build scripts and current tests. Reproduce the relevant baseline failures with minimal fixtures: optional feedback, annotation endpoints/coordinates/limits, worker instruction and path scope, approval invalidation, non-Git resume, checkpoint self-invalidation, extracted-archive dependencies and loopback startup without interface enumeration.

Preflight records Git/Python/Node, the actual SQLite library and source identity, available MCP/OMP tools, model capabilities and the installed browser QA tool. It does not install dependencies or claim integration success. Store private discovery/evidence under the target repository's ignored `.prism-state/` path. Check that the source-fingerprint exclusion policy cannot hide product code.

**Exit:** a reproducible candidate and discovery record, a precise scope statement, actual capability observations, and G0 evidence. Human participant research is recorded as deferred. Undeclared native/offline targets remain outside this web-product release.

## M1 — Establish one authoritative domain

**Requirements:** REQ-CORE-001 through REQ-CORE-007.

Implement shared typed command handlers with explicit authority, expected versions and structured errors. Start with one narrow vertical slice—load a run, read an artifact, submit a decision—and make CLI, MCP and HTTP reach the same handler. Keep protocol-specific error/response formatting at the adapters. Schema validation does not replace semantic checks.

Introduce transaction boundaries, stable entity identities, integer revisions, idempotency records and an outbox in the same authoritative store. Immutable artifact blobs are addressed by content digest; mutable metadata and read projections reference them. Rebuildable summaries must never become a second source of authority.

The critical checks are conflicting writes, replay after lost replies, idempotency-key reuse with changed input, crashes around commit/dispatch, corrupted artifact bytes, stale projections and incompatible runtime/schema combinations. Exercise both success and rejection behavior through adapters. Do not postpone these invariants until the UI is complete.

**Exit:** the shared slice is working through all supported adapters, old behavior has a compatibility route, and G1 proves the invariants with deterministic interleavings and fault injection. Avoid broad rewrite/deletion of baseline code until the replacement behavior has evidence.

## M2 — Make migration and recovery trustworthy

**Requirements:** REQ-MIGRATION-001 through REQ-MIGRATION-005.

Build synthetic fixtures for supported legacy record versions, including valid history and incomplete/malformed cases. Inventory first, back up exact original bytes, import to a separate candidate store, verify counts/references/digests, then activate. Persist deterministic ID mappings and an audit receipt; a retry must not duplicate history or costs.

Missing legacy approval fingerprints, receipts, model observations or artifacts remain unknown. Preserve readable history while blocking only operations that require the missing fact. Do not manufacture zero spend or approval from absence. Recovery instructions should name the exact unresolved fact and available repair path.

SQLite is a runtime choice, not a guarantee supplied by the Python version. Record `sqlite3.sqlite_version` and `sqlite_source_id()`. Before enabling multi-connection WAL, verify the current runtime includes the documented WAL-reset fix: SQLite 3.51.3 or later, recognized fixed backports 3.44.6/3.50.7, or attributable vendor evidence. If that cannot be established, an explicitly selected and tested `DELETE` rollback-journal policy with `synchronous=FULL` and serialized writes can be evaluated instead. Do not silently switch policies or install system packages. The same transaction, crash, backup and integrity scenarios still apply. The basis is [SQLite's current WAL documentation](https://www.sqlite.org/wal.html#walreset), rechecked at implementation and release.

Test rollback before users depend on the new store. An unchanged fixture must restore exactly. Later writes create a divergence that must be preserved and reconciled rather than overwritten. Use a supported consistent backup procedure; copying only the live main database file is not a sufficient backup policy for WAL state.

**Exit:** G2 proves interrupted migration/activation, repeated import, incomplete-data handling, local-path policy, consistent backup and conflict-aware rollback. Keep the old export and receipt until the supported retention/cleanup decision is made.

## M3 — Repair approval and revision semantics

**Requirements:** REQ-APPROVAL-001 through REQ-APPROVAL-006; REQ-REVISION-001 through REQ-REVISION-006.

Resolve the optional-feedback contract once, then apply it to UI validation, API/MCP input, persistence and downstream checks. Bind approval to the artifact/component, relevant dependency revisions and criteria. Run progress and unrelated metadata do not invalidate design acceptance. A relevant change does, with a reason the user can inspect.

Require expected decision revision and artifact/dependency fingerprint on submission. Race approval against cancellation and against an artifact revision. Check both commit orders: no ordering may leave unseen new content covered by an old approval. Guided and YOLO records identify their real actor and mode; YOLO does not create publication or tool authority.

Normalize annotation geometry relative to the image content, not the outer stage. Use the final pointer position for line/rectangle endpoints. Share finite-value and point-count constraints across client and server. A client can reduce sampled points within the declared contract while preserving endpoints; it cannot silently submit data the server rejects. Reproduce letterboxing, zoom, resize, long strokes and direct malformed requests.

Focused revision pins exact base content, component IDs and an annotation snapshot. Decomposition creates stable IDs and a dependency graph. Preserve accepted independent components, and give each item of a batch its own durable decision outcome plus a replayable batch receipt. Concurrent edits to a shared token/dependency require conflict handling and new lineage, not last-write-wins replacement.

**Exit:** G3 verifies correct decisions and scoped revisions through the shared engine, including cross-domain races. The dashboard can consume authoritative allowed actions and reason codes instead of maintaining a separate workflow interpretation.

## M4 — Control cost, models and worker authority

**Requirements:** REQ-BUDGET-001 through REQ-BUDGET-007; REQ-MODEL-001 through REQ-MODEL-005; REQ-WORKER-001 through REQ-WORKER-005.

Implement the design ledger before chargeable dispatch. Design work includes the configured concept/mockup/artwork/revision/critique categories; implementation and pack-building work are separately tracked and excluded by default. Store integer minor units, currency and exponent. An estimate, upper bound, reservation and settled charge are different facts. Unknown is never zero.

In hard mode, a controlled dispatch needs a defensible charge bound and an atomic reservation. Test two workers competing for insufficient remaining budget, a cap reduction racing a reservation, lost provider responses, duplicate receipts and cancellation at each dispatch phase. Keep uncertain exposure reserved pending reconciliation. An external provider that cannot provide bounded, controlled behavior supports advisory enforcement, not an invented hard guarantee.

Implement model resolution with the agreed precedence: explicit invocation; persisted run settings on resume; project defaults; personal defaults; capability/cost-based auto selection. Preserve current-model mode. Store requested, resolved and observed assignments separately. Price/capability inputs carry source and time; no new model ID or price is assumed to exist.

Worker packets include applicable actual AGENTS instructions and ownership for intended new files as well as existing targets. Intersect host, session, project and task authority. Concurrency is configurable and observed; dispatch is constrained by dependencies and reservations. Validate worker outputs against owned scope and real evidence. Sequential role fallback is visible and cannot masquerade as concurrent independent review.

**Exit:** G4 demonstrates financial and dispatch invariants with controlled provider fixtures and no live spend. The `core` gate profile now has meaningful implementation evidence, but this does not claim a working web release, successful installation or host integration.

## M5 — Complete the dashboard's real interaction flow

**Requirements:** REQ-UX-001 through REQ-UX-006; REQ-A11Y-001 through REQ-A11Y-005.

Use [the product/UX contract](PRODUCT-AND-UX.md) to implement persistent current context, stable before/after comparison, explicit changed scope, drafts that survive errors, honest progress, clear cancellation outcomes and deliberate decisions. Keep the lightweight frontend unless measurement establishes a concrete reason to replace it.

Use [the accessibility contract](ACCESSIBILITY-AND-PERFORMANCE.md) for semantic structure, keyboard focus, noncolor status, reduced motion, contrast, zoom/reflow and usable target sizes. Drag alternatives and keyboard support are separate obligations. A textual/structured revision path remains available when drawing is unavailable; any genuinely path-dependent freehand exception is narrowly justified.

Follow the repository's existing browser QA routing: plan with the installed `playwright_fast` tool or `/pw-fast`, then execute `affected` or `quick` Chromium checks for the changed flow. Capture actual interactions and screenshots. Unit/DOM simulations are useful but do not satisfy required browser evidence. Preserve valid work and report an unavailable browser honestly; do not install system packages without authorization.

**Exit:** G5 exercises critical flows, errors, stale state, cancellation races, resize, keyboard and nondrag pointer behavior in a real browser. Human participant research remains deferred and no usability-study result is implied.

## M6 — Bound knowledge, theme and performance work

**Requirements:** REQ-KNOWLEDGE-001 through REQ-KNOWLEDGE-004; REQ-THEME-001 through REQ-THEME-003; REQ-PERF-001 through REQ-PERF-004.

Integrate original, compact knowledge rules with source/edition/page or URL, applicability, confidence and conflicting advice. Preserve the distinction between evidence, heuristic and project policy. Do not import source PDFs or dump entire books into worker context. Retrieval selects a relevant bounded subset and leaves project instructions/acceptance criteria intact.

Exercise theme installation, activation, upgrade and restore in projects with consumer overrides. Token coherence and visual appeal do not replace accessible state checks. Keep theme rollback separate from package installation restore and application redesign rollback.

Measure representative fixtures before optimizing. The initial project budgets in the accessibility/performance document are proposed targets, not observed results. Remove redundant blob reads and full-history scans, implement bounded snapshot-aware paging, control overlapping polling and cancel obsolete requests. Reuse immutable content safely and verify relevant content again at the approval boundary. Do not add event infrastructure before reducing repeated work.

**Exit:** G6 provides catalog provenance, context-selection evidence, conflict-safe theme lifecycle and raw fixture-specific performance measurements. Any threshold change is explicit and supported by evidence; correctness and authority invariants are not relaxed to improve speed.

## M7 — Verify what users actually install

**Requirements:** REQ-INSTALL-001 through REQ-INSTALL-007; REQ-SECURITY-001 through REQ-SECURITY-007; REQ-DOCS-002.

Validate source ZIP, sdist and wheel as separate deliverables. Extract the ZIP away from the checkout and execute its documented installation and packaged checks. Build the wheel from an extracted sdist; install it normally into a clean environment and test from a nonrepository directory. Prevent editable-install, inherited destination and `PYTHONPATH` leakage. A test that needs a missing checkout-only remediation document exposes a packaging defect.

Define intentional file/capability differences between distributions. A wheel need not include every repository document, but every advertised wheel workflow must work with what it ships. The source ZIP must contain every test fixture/document needed by the verification it advertises. Scan nested private canaries and keep licenses, manifests, bundled runtime/skill/theme resources and versions coherent.

Verify project install/update/restore with actual receipts and divergent user edits. Exercise local MCP in a real supported client/transport and OMP discovery in the actual host. A lack of hot reload may use the documented direct-reading fallback; it is not reported as native discovery success.

Use [security and operations](SECURITY-AND-OPERATIONS.md) for authentication, origin/CSRF, XSS/artwork, capability scope, path containment, redaction and owned-server lifecycle checks. New installs default to loopback; explicit legacy LAN configuration is preserved and surfaced rather than rewritten silently. Loopback execution must succeed without network-interface enumeration.

**Exit:** G7 verifies deliverables and host/security behavior on the declared environment. The `web` profile is a candidate-quality signal; final release still requires G8 and its current-candidate matrix/review/artifact evidence.

## M8 — Produce one coherent release candidate

**Requirements:** REQ-EVIDENCE-002 through REQ-EVIDENCE-006; REQ-DOCS-003.

Freeze a clean candidate and the reviewed verification plan. Run the `release` profile with real bindings for G0–G8. The browser release matrix is `matrix` or `full` across configured Chromium, Firefox and WebKit projects. Every required engine must actually execute; missing projects, infrastructure errors and skips remain blocked/failed.

Obtain a substantive review of the diff, domain invariants, accepted scenarios, packaging and operational risk. Prefer a distinct reviewer. If unavailable, use the explicit sequential-role fallback with its reason and limited-assurance label. A second role label applied to the same actor is not independence. Review records cover all release cases with current evidence and zero unresolved severe findings.

Build and verify the final artifacts from that candidate, retain their hashes and isolated-install receipts, and assemble the release handoff. If tests or packaging modify source, re-establish the candidate and rerun the affected gates; never join old passes to new bytes. A readiness receipt does not itself publish, push, merge, tag or deploy.

**Exit:** G8 supports either a verified release-candidate claim or the explicitly qualified review-fallback variant, with human research still labeled deferred. Any remaining blocker identifies exact acceptance IDs, observed failure, attempted safe alternatives and a resumable next action. Scope changes require coordinated contract updates; deleting a hard case is not a fix.
