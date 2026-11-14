# UI DESIGN STUDIO v1.4.0 - CORTEX REMEDIATION CONTRACT

ASCII ONLY. BASELINE: uploaded UI-Design-Studio-OMP-v1.4.0.zip (94 archive entries). TASK: implement remaining code/skill/efficiency remediation, tests, packaging, docs. USER-BASED TESTING DEFERRED. This is an execution contract, not a request for a plan.

## 0. NON-NEGOTIABLE RUN RULES

- Work in actual project checkout; inspect git status, instructions (AGENTS.md etc), current HEAD, and installed OMP conventions BEFORE modifying. Archive baseline may differ: inspect actual code, adapt targets, record deviations. Do not overwrite unrelated work. Create a task branch per repository policy. Preserve commits/history; no force push, release, deploy, merge or external mutation without existing authorization.
- Read this file once. Implement in dependency order; resume from ledger after compaction/restart. Continue independent work on failures; only stop for genuine missing credentials/permissions/unsafe action. Do NOT interrupt user for routine design decisions. No invented tests, approvals, benchmarks or screenshots.
- KEEP user-based testing (UAT, manual human visual judgment, device/user interviews, human acceptance, human deployment sign-off) DEFERRED, NOT PASSED. Never request UAT during this run. Implement all feasible automated checks now: unit/integration/property/regression/security, headless browser where available, fixture render comparison, accessibility automation, benchmark harnesses. If a real target/tool unavailable, label BLOCKED/NOT_RUN with reason; never convert to PASS or waive mandatory automated checks without evidence.
- Preserve guided approval actor/provenance, yolo agent-only cosmetic decision rights, original project instructions, offline requirements, routing restoration, theme registry/default/rollback, old schema compatibility, and independent reviewer separation. Do not turn scoped workflow completion into full-theme release approval.
- Python dependency work must use `.venv` (create with `python3 -m venv .venv`; use `.venv/bin/python -m pip ...`), avoid system pip. Prefer existing lockfile and test runner. Never make test results contingent on paid provider calls.
- Changes should be additive/backward compatible where possible. If schema/API must evolve: explicit versioning, migration/read support, downgrade/rollback notes, fixtures for legacy records. Validate symlink/path traversal protections; no arbitrary remote CSS/script acceptance.
- Do not edit release checks just to make failures pass. Require a failing regression test before each reproduced bug fix, then passing test after. Tests inspect behavior, not just expected strings.

## 1. VERIFIED BASELINE / TARGET MAP

Verified v1.4.0 targets (relative to repo root):
E=.omp/skills/ui-design-studio/scripts/studio.py
D=.omp/skills/ui-design-studio/scripts/design_server.py
S=src/ui_design_studio/server.py
P=src/ui_design_studio/dashboard.py
K=.omp/skills/ui-design-studio/SKILL.md
W=.omp/skills/ui-design-studio/references/workflow.md
R=.omp/skills/ui-design-studio/references/run-records.md
M=.omp/skills/ui-design-studio/references/model-routing.md
Q=.omp/skills/ui-design-studio/references/quality-gates.md
C=.omp/skills/ui-design-studio/references/project-context.md
A=.omp/agents/
T=tests/
Docs=README.md, docs/{VALIDATION,RUN-TYPES,INSTALLATION,MCP,CHANGELOG,DISTRIBUTION}.md

Other phase skills: `.omp/skills/{ui-assess,ui-plan,ui-design,ui-produce,ui-review,ui-theme,ui-finalize,ui-yolo}/SKILL.md`. Relevant MCP CLI: `src/ui_design_studio/{cli,server,dashboard}.py`; packaging: `scripts/{install,install_mcp,package_release}.py`, `pyproject.toml`.

Pre-fix defects verified on v1.4.0:
F1 `E:check_run()` hashes evidence report `path/sha256` but not evidence `inputs/inputsDigest`; `D:fresh_evidence()` DOES validate inputs. Change bound input => dashboard rejects, engine/reviewDigest/registration may PASS. Severity CRITICAL.
F2 `E:render_agent_model()` strips model/thinking/thinking-level variants, but not camelCase `thinkingLevel`; conflicting old high and new low can coexist. Severity HIGH.
F3 `S:ui_design_status()` returns unbounded snapshot; large artifact collections create large tool replies.
F4 `E:check_model_routing()` requires all seven assignments even for scoped runs.
F5 W/K/phase skills emphasize full concept-to-package process for small modifications; references/worker contracts still overly broad.
F6 offline performance agent unconditionally requests offline modes despite `offline=not-required` supported by project context.
F7 coverage validator assumes each surface has full states x viewports grid; reusable applicable-only cases poorly represented.
F8 repeated hashes/snapshot validation; dependency-aware resume and empirical optimization benchmarks incomplete.

Baseline reported in preceding audit: core Python 121 tests + 50 subtests passed; Node extension 49 passed with TypeScript stripping; optional MCP suite not independently run. Treat those as historical, not current verification. Preserve v1.4.0 global MCP/dashboard lifecycle changes.

## 2. REQUIRED OUTPUT / LEDGER

Create/update `docs/remediation/v1.4.0/`:
- `LEDGER.md`: rows ID, objective, status TODO|ACTIVE|PASS|BLOCKED|DEFERRED_UAT, commit, files, test/evidence path, remaining blockers; progress after each item.
- `COMPATIBILITY.md`: old/new schemas, flags, defaults, migration, rollback, host compatibility, installation effects.
- `TEST-REPORT.md`: exact environment/commands, total tests, pass/fail/skip, fixture names, automated coverage, honest limits.
- `BENCHMARKS.md` + machine-readable results: baseline vs changed measurements; same fixture, same tool/config/model when available, multiple samples, no invented real-provider results.
- `UAT-DEFERRED.md`: HUMAN testing not executed; explicit scenarios, expected results, how to run, who signs off; DO NOT require sign-off to finish engineering remediation. Document deferred gates separately from automatically verifiable acceptance.
- `HANDOFF.md`: summary, changed behavior, install/migration, rollback, known issues, deferred testing, final version/commit.

Mark engineering complete ONLY when all mandatory automated criteria pass and unresolved work is honestly blocked with its cause (do NOT label 100% complete with blocked mandatory items). UAT deferred does not block an `ENGINEERING_READY_UAT_PENDING` classification; final user acceptance remains NOT VERIFIED. Do not self-issue human approval.

## 3. EXECUTION ORDER / WORKSTREAMS

R00 PREFLIGHT / BASELINE
1. Inspect git status, existing instructions, tests, run formats, schemas, CLI/MCP interface, API contracts and prior design records. Record baseline commit/dirty paths. Avoid modifying generated install copies first: source edits must propagate via packaging/install.
2. Create ledger and capture baseline automated test results. Use `.venv`; install declared optional test dependencies when available (no global pip). Detect Node and run with supported TS strip workflow or project-approved Node >=24; skip with exact reason if unavailable. Preserve original failures.
3. Add deterministic synthetic fixtures to tests for routing, evidence, scope, coverage, hash reuse, resume, MCP status. No dependence on web, credentials or human actions.
AC: baseline recorded; regression-first tests demonstrate F1/F2 on old code; all source locations inventoried.

R01 UNIFY EVIDENCE TRUTH (BLOCKER FOR FINALIZATION)
1. Refactor E into shared validation primitive `validate_evidence_entry(root, entry, digest_cache=None)` (name flexible) returning normalized validity, reasons and canonical bytes/digests; support `passed` and `not-applicable` under existing offline policy. Enforce required fields, paths, SHA, types, uniqueness and current bytes. If `inputs` is PRESENT require nonempty/correctly typed path list as schema allows, require valid `inputsDigest`, recompute via existing confined `file_digest`. No silently ignoring invalid input binding. For legacy evidence without inputs retain documented old compatibility behavior, do not invent bindings. Never allow dangerous path, symlink escape, or ambiguous duplicate IDs.
2. Use SAME primitive from E:check_run, D:fresh_evidence/coverage gates, CLI validation, MCP status/acceptance, registration. Dashboard presentation may format results but must not redefine freshness. Reuse normalised validation result in one snapshot.
3. Include evidence dependency identities and current content digests in reviewDigest used for final decision. Changing bound inputs MUST change reviewDigest or invalidate check_run and block registration even if report is byte-identical. Existing finalize approvals against old digest must be re-reviewed when dependencies changed; do not synthesize human approvals. Preserve deterministic canonical ordering and versioned migration as required.
4. Regression matrix: mutate bound input after PASS; deleted input; missing digest; malformed digest; path escape; evidence file changed; status failed/pending; unrelated file changes; duplicate evidence; legacy no-input entry; `offline=not-required` N/A vs required; previous approved finalize digest invalidated. Assert E CLI check, D dashboard gates, S MCP and register agree for every case. Add explicitly registration rejection test.
AC: stale inputs => no PASS and no registration by ANY public path; all paths consistent; valid legacy runs compatible; adversarial tests PASS.

R02 ROUTING NORMALIZATION + TRANSACTIONAL SAFETY
1. In E:render_agent_model normalize `thinking`, `thinking-level`, `thinking_level`, `thinkingLevel` plus quoted YAML key forms; reject unsupported YAML alias/merge/duplicate/complex routing keys rather than silently corrupt. Preserve newline style, body, unrelated keys/comments; emit ONE canonical thinking setting according to current OMP parser and active provider. For `provider-default` do not leave a hidden old reasoning field.
2. Add tests for camelCase stale high->low, provider-default removal, quoted keys, CRLF, frontmatter name mismatch, duplicate field, malformed YAML, unchanged body, mixed key styles, preserving legitimate nonrouting metadata.
3. Respect OMP higher-priority overrides; verify routing was ACTUALLY applied/observed before recording success. Maintain transactional journal/restore: crash, partial apply, old journal, permissions, preexisting edits, user-owned settings. Rollback on failure and avoid overwriting subsequent edits. `models=auto-models` default; `models=current-model` explicitly exact active session model AND thinking for dispatched workers. Do not change global user model settings.
AC: no contradictory routing fields; journal recovery/restore tested; real unavailable provider observations labelled pending, not fabricated.

R03 SINGLE SOURCE FOR VALIDATION + DIGEST REUSE
1. Introduce per-check/snapshot `ValidationContext` (or equivalent) with file digest memoization keyed by confined absolute path AND robust signature (stat signature for within-check reuse only), evidence validation, coverage and gate results. Final acceptance must recompute/verify current files; no cross-request stale cache can bypass mutation detection.
2. D snapshot should consume E shared check rather than replicate expensive/reasoning-different logic; ensure consistent `FAIL/PENDING/PASS`, counts, blocking reasons. Preserve dashboard-only UI projection and sanitization.
3. Add instrumentation tests: hundreds of cases sharing artifacts => each unique file hashed once per stable validation cycle where safe; mutate between cycles => rehashed and invalidated; mutation during validation => fail safely/retry; symlink swapping/path escape => reject. Never report gains based solely on synthetic hot OS cache.
AC: identical acceptance result across interfaces; lower duplicate SHA calls; cache not a freshness bypass.

R04 MCP COMPACT STATUS / PAGINATION
1. In S `ui_design_status(run,interval=...)` maintain compatibility. Add optional `view=compact|full` (default COMPACT for NEW use only if API compatibility tests validate; alternatively introduce `ui_design_status_compact` while keeping legacy default; document exact choice). Keep full snapshot explicitly accessible, not silently removed. Allow `since_revision` if deterministic revision implemented, otherwise a separate changes tool; reject invalid cursor/revision cleanly.
2. Compact shape should include runId, phase, status, scope mode, gate statuses/reasons, counts, nextAction, blockers, worker summary, artifact/evidence counts, update revision and small bounded recent changes; no huge artwork metadata/HTML blobs. Paginate artwork/evidence listings with stable sorting, bounded page size, cursor and validation. A specific artifact remains retrievable by ID/path with safe confinement.
3. Ensure MCP `content` vs `structuredContent` avoid duplicate huge prose where client supports resource retrieval; don't assume duplication savings until traces prove it. Preserve dashboard/full snapshot detail for human viewing.
4. Regression: 0, 100, 1000 artifact fixtures; bounded compact bytes/tokens; full unchanged, pages complete/no repeats, invalid cursors rejected, encoded paths secure, `since` accuracy and stable revision. Target compact <=500 approx tokens for normal state and no unbounded growth, unless critical blocker details require more.
AC: normal status bounded independent of artwork count; detail reachable; tools backward compatible.

R05 PHASE-SPECIFIC LAZY INSTRUCTIONS
1. Keep public nine skill names and existing entry commands. Refactor K to concise router/director: scope discovery, task selection, original instructions/requirements, ownership, agent dispatch, evidence rules, stop conditions. Avoid loading every reference at startup. Use explicit `read when` pointers for assessment, concepts, implementation, review, theme, finalize, migration, OMP routing, MCP host operation. Only load relevant modules; NEVER omit applicable original AGENTS.md and requirements from worker tasks.
2. Each phase skill contains trigger, minimum inputs, task contract, outputs, applicable gate, narrow references and escalation; no duplicated full lifecycle. `ui-yolo` thin wrapper (autonomous aesthetic decisions), still no fabricated human approval and no extra deploy permissions. Host adapter instructions split OMP vs MCP; remove irrelevant host instructions from each workload.
3. Keep detailed HUMAN documentation, make machine-facing hot path short. Verify relative paths and install packaging include all moved refs; no broken links.
4. Static audit measure initial director+mandatory references and each phase's transitive required reads; establish budget targets: director <=1200 approximate tokens; routine startup <=3000 tokens before original project context; worker task packet <=700 tokens PLUS mandatory source instructions. These are optimization targets, NOT caps on truth/quality. Use actual tokenizer if installed; label estimates otherwise.
AC: targeted skill routing correctness, no missing original instructions, transitive context measured, no quality/safety invariant dropped.

R06 SCOPED WORKFLOW (NO FAKE FULL RELEASE)
1. Implement scope classification: `fix`, `component`, `single-flow`, `reference-adaptation`, `full-redesign`, plus `assess-only`/`design-only` boundaries as needed. Derive from request plus project inventory; do not restore `profile=` selection. Explicit request overrides inference. Capture scope and source rationale in run records. Avoid required new concepts for minor fixes and established-direction changes.
2. Focused execution: inspect affected behavior => bounded change => render affected states => independent check => scoped closure. Full redesign: assessment, 2 meaningful concepts (3 only justified), early feasibility slice, full applicable design coverage, produce, independent review and finalization. Guided requires authentic selected approvals; yolo only agent cosmetic decisions. Never mix a scoped 'done' with `run.status=passed/phase=finalize` unless full-theme gates genuinely pass.
3. Add `scopedCompletion` or separate typed result/report with versioning (not a magic bypass of E.check_run). Support explicit blockers and next action. Preserve theme registration only for fully approved full-theme records.
4. Tests: CSS one-line fix with no concepts, existing-component state fix, net-new page, reference-driven flow, full redesign, partial scope, failed check, requested design-only (no application changes), assess-only (no application changes), no duplicate goals, continuation. Prove no release bypass.
AC: focused tasks don't require unrelated work; full theme still requires unchanged quality gates.

R07 EARLY HOST FEASIBILITY SLICE
1. In W/phase contracts place a representative real-host component/page/dialog prototype AFTER selected concept but BEFORE freezing shared design contract/producing entire mockup matrix. Test typography, focus, dynamic content, theme variables, portal/dialog, narrow viewport, one failure state; constrain write permission to prototype until approved.
2. Use existing host components and deterministic fixtures; design-only uses isolated preview, not production mutation. Record feasibility findings and contract revision. Do not assert native validation from a web-only prototype.
3. Automated fixtures test contract dependencies, prototype failure stops expansion, implementation mismatch leads to re-plan, no accidental host mutation on design-only.
AC: integration limits detected before downstream mass mockups; scope/host boundaries preserved.

R08 REUSABLE RENDER FIXTURES + APPLICABILITY
1. Extend coverage schema in backwards-compatible/versioned way to represent explicit applicable `(state, viewport)` cases (or applicability rules with explanations), not mandatory Cartesian product when states do not apply to every viewport. Keep legacy Cartesian interpretation for old records. Reject unexplained omissions; critical states/failure paths cannot silently disappear. Aggregate counts reflect actual required cases.
2. Implement deterministic fixture IDs and render-from-host component/state machinery where host supports it; capture static previews/screenshot assets for dashboard (scripts sanitized), interaction checks on actual host. Record fixture version, component, environment, data, breakpoint, output identity, evidence deps. Reuse component-state evidence only for truly identical semantics; still require page-level integration for unique flows.
3. Tests: legacy coverage, sparse valid coverage, missing required state, excluded with rationale, duplicate case, invalid viewport, shared evidence across pages, changed token invalidating relevant cases, no native/web claim substitution.
AC: explicit applicability with no coverage loophole; fixtures reproducible and attached to current evidence.

R09 CHANGE/DEPENDENCY-AWARE RESUME
1. Create stable manifest of source-labeled project instructions/requirements, component/theme dependencies, files/digests, run revisions and environment facts. Preserve privacy/path safety. Record full observed source IDs, not just labels. Re-read instructions on resume, compare actual bytes. No unconditional bulk reread of unchanged references.
2. Build dependency DAG (e.g. token -> component -> surface case -> evidence -> approvals) and mark only transitive affected nodes stale on changes; scoped changes preserve unrelated accepted work. Source revision/dirty state considered, but don't invalidate only because unrelated files changed. Any project requirement change must trigger re-evaluation of applicability.
3. Schema migration: old runs still readable; missing manifest => conservative verification, NOT invented freshness; legacy 1.0 continuation must preserve authentic prior human approvals and original routing restoration. No writing an old journal under a new run identity.
4. Tests: component-local change, shared token, requirement file, ignored unrelated file, deleted/symlinked input, resume on dirty tree, old 1.0/1.1 record, changed external environment, restored routing journal.
AC: every changed dependency invalidates exactly its dependent acceptance evidence or conservatively blocks; no unrelated restart.

R10 ROLE-BASED DISPATCH / WORKER PACKETS
1. Allow run routing assignments for ONLY selected/dispatched specialist roles in new schema/version; preserve read support for v1.1 all-seven records. Before first dispatch selection can be planned/resolved; DO NOT require an already-observed execution to authorize first dispatch. At dispatch time verify actual model and thinking; after execution record observation. `current-model` applies to every dispatched worker; preserve 3 workers as a concurrency ceiling, not mandatory count.
2. Add generator for a small per-role packet: objective, owned files, immutable shared tokens, applicable original requirement paths, contract revision, exact artifacts, acceptance/evidence gates, allowed actions, reviewer independence. Never drop worker access to original AGENTS.md due to subagent inheritance assumptions. Workers must not edit unowned shared paths.
3. Constrain tools by role where practical without blocking required evidence capture or assuming tool list = sandbox. Reuse worker context on related follow-ups; separate implementer/reviewer identities.
4. Tests: one-role assessment, first dispatch, partial availability, absent unused roles, multi-worker conflicts, higher-priority OMP overrides, current-model, restore, packet missing original instruction => failure.
AC: unused roles need no model assignment; all actual workers observed/validated; shared-file collisions prevented.

R11 QUALITY / OFFLINE APPLICABILITY / REVIEW
1. Edit `A/ui-performance-reviewer.md`, Q and review skill: offline cold/WAN-off/warm-cache checks ONLY when resolved context requires offline. With `offline=not-required`, run relevant network failure/recovery checks without inventing offline product requirement. If context unresolved, do not waive required offline checks; mark pending.
2. Preserve measurable accessibility, focus, keyboard, contrast, reduced motion, long-content, density, error and recovery checks as applicable. Require independent reviewer; each finding contains severity, evidence path, reproducible case, fix criterion. No vague infinite aesthetic loop: cap repair rounds, then BLOCK with concrete defect.
3. Annotate reference-image interpretation in existing contract (observed feature -> selected rule -> applies -> deliberately excluded) instead of reinterpreting image in each agent. Do not create fake visual examples or claim human review.
4. Tests: offline required, not-required, unresolved, reviewer different from implementer, fabricated proof rejected, applicable automated a11y/visual checks.
AC: requirements applied conditionally; quality gates not weakened.

R12 PACKAGE / HOST / SECURITY REGRESSION
1. Preserve v1.4.0 global MCP install, auto dashboard lifecycle, process ownership, cleanup/restart, HTTP sanitization, path confinement, CSRF/auth protections (where implemented), and theme rollback. New status/fixture APIs must not create file disclosure, path traversal, SSRF, arbitrary code execution or cross-project access.
2. Run `scripts/package_release.py` using supported command syntax (inspect `--help` before invoking), validate MANIFEST.sha256, install/uninstall/upgrade dry-run or isolated temp paths where possible. Verify `.omp` content and references survive install, global MCP isolation, symlink handling, Windows path assumptions where testable; do not alter user machine globally during tests.
3. Update docs, examples, schema specification, and CHANGELOG; record remediation as new version/patch per repo policy; do not overwrite tag v1.4.0. No public publish without authorization.
AC: old use-cases intact, packaging deterministic, install tests PASS, no unintended external changes.

R13 BENCHMARK HARNESS / BUDGET EVIDENCE
1. Build deterministic task suite: tiny component fix, new page in established system, reference-inspired flow, dense offline appliance screen, full multi-page redesign, resume after token change. Include fixed fixture project requirements and expected acceptance properties; separate simulated workload from live provider runs.
2. Measure total tokens per tool exchange/worker where metadata accessible; use explicit approximation for static prompt size. Count tool response bytes, read duplication, hashes per snapshot, wall time, tool calls, repair loops, detected seeded defects, coverage, contract consistency. Baseline v1.4.0 may be measured from unmodified archive in temporary tree; NEVER compare invented prior results or different fixture/model and claim savings. Multiple repetitions when meaningful; record sample sizes, variance, CPU/cache/runtime/environment.
3. Targets: compact status bounded; per-cycle duplicate hash reduction; initial phase context materially reduced; scoped fix fewer orchestration steps; no new false passes, omitted requirements, or critical review misses. Exact percentage gains are REPORT-ONLY measured values, not acceptance gates unless task sets a reproducible threshold.
4. Make benchmark runner repeatable, noninteractive, offline by default; optional live-provider benchmarking flagged opt-in and NOT mandatory this run.
AC: reproduce same comparisons with one command; measured gains/regressions and caveats documented, no unsupported savings claims.

R14 CONTRACT/COMMAND/TEST SURFACE
1. Retain existing public CLI, MCP, scripts, dashboard, installation commands. For added functions expose CLI/MCP aliases or flags with `--help` and docs. Decide status API default compatibility explicitly. Typecheck/lint JSON/YAML; validate all Markdown relative links and skill frontmatter. No `profile=` requirement.
2. Add negative and end-to-end synthetic tests across engine, dashboard, MCP, CLI, install, security, phase choice, registries. All cross-API acceptance relies on shared authoritative validation. Ensure code coverage targets known risks, not just number of tests.
3. Run complete repo-declared tests: `.venv/bin/python -m pytest -q` when dependencies present, Node TS extension tests using supported Node version or documented strip flag, packaging/hash test, syntax/format checks, bounded token/read measurements. Capture full logs and exact versions. If a suite requires unavailable package, use `.venv` to install project-declared test extras; if network unavailable leave BLOCKED_NOT_RUN and list command.
AC: all runnable automated suites green; every previously reproduced defect has a regression; no silent skips.

R15 FINISH / CONTINUATION
1. Reconcile ledger all IDs with code + passing tests. Independently inspect diff for scope creep, unsupported assertions, stale docs, unsafe cache, release bypass, accidental permission changes. Revert unrelated modifications. Finish valid git commit(s) per policy; show final `git status` and exact commit(s).
2. Produce `HANDOFF.md` including commands for automatic verification; deferred UAT test checklist; unresolved automated blockers; known platform/env limits; release/publish not authorized state. Keep `UAT-DEFERRED.md` status clearly `DEFERRED_UAT` for all human checks.
3. End only after independent automated review. If engineering checks PASS but UAT deferred, report `ENGINEERING_READY_UAT_PENDING`; if mandatory automated gates remain blocked, report `ENGINEERING_BLOCKED` and precisely name gate, evidence, next feasible step; never assert full user acceptance.
AC: reproducible evidence-backed engineering state; human testing deferred as explicitly requested.

## 4. UAT DEFERRAL (STRICT)

DO NOW (automated, no user interaction): unit, integration, failure injection, source schema migration, simulated run acceptance, automated render/a11y where environment permits, security regression, performance baseline, packaging/installation in disposable sandbox, documentation and source review.

DEFER (do not solicit or mark passed): human visual preference and aesthetic review; assisted usability study; real user behavior/task timings; acceptance on user's physical machines; live production theme switching validation requiring user access; operator acceptance/release sign-off; non-automatable observational testing. Create instructions and expected outcomes for each in `UAT-DEFERRED.md`. A missing human signoff is NOT a defect in engineering tests but blocks claiming user-approved release.

Special case: if a supposedly automatic required test cannot run because it depends on unavailable service/device, classify `BLOCKED_AUTOMATION`, not `DEFERRED_UAT`. Keep it separate from deliberate UAT deferral.

## 5. CORTEX EXECUTION PROMPT (PASTE AS FIRST USER MESSAGE IN OMP)

Read `UI-Design-Studio-v1.4.0-Cortex-Remediation.md` as the mandatory remediation contract. Inspect current project/AGENTS instructions and git state. Execute R00-R15 in dependency order, create and keep `docs/remediation/v1.4.0/LEDGER.md`, add regression-first tests for F1/F2, implement all remaining optimizations, and run every feasible automated test and benchmark. Keep HUMAN/USER-based testing deferred; do not ask for UAT or falsely mark it passed. Continue all independent safe tasks without checkpoints, follow existing git/permissions policy, preserve current v1.4.0 MCP/dashboard and theme behavior, and never weaken acceptance checks. Finish with evidence-backed ENGINEERING_READY_UAT_PENDING or exact ENGINEERING_BLOCKED status, changed files, test commands/results, before/after metrics and remaining deferred UAT steps. Do not stop after writing a plan.

## 6. CRITICAL FINAL INVARIANTS

I1 `bound input changed => shared evidence freshness rejects => engine != PASS => finalize approval stale => register blocked`.
I2 `routing rewrite => one effective thinking value; current-model exact; override conflicts caught; preexisting user config restored`.
I3 `small scoped work != whole-theme finalization; no bypass via MCP/CLI/dashboard`.
I4 `offline requirements sourced, never assumed or waived for offline project`.
I5 `legacy run/theme/approval/journal readable and not impersonated`.
I6 `compact status bounded; full detail available; caches never permit stale PASS`.
I7 `every dispatched worker receives original applicable instructions and actual verified model policy`.
I8 `automated tests mandatory now; HUMAN/UAT explicitly deferred; no invented release permission`.

END OF CONTRACT.
