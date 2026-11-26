# Quality, evidence and release contract

## What a pass means

The rebuild pack separates four claims. Keeping them separate prevents a complete-looking handoff or successful unit suite from being mistaken for a finished product.

| Claim | Required evidence | What it does not establish |
|---|---|---|
| Pack integrity | Valid schemas, hashes, local references and requirement/case/milestone/gate traceability | Application behavior, migration, installation, browser or host success |
| Core implementation | G0–G4, executed against the recorded candidate | Web interactions or distributable/host readiness |
| Web candidate | G0–G7, including actual browser, accessibility, isolated installation and host/security checks | Final release matrix and substantive current-candidate review |
| Release candidate | G0–G8, exact artifacts, release browser matrix and review | Human participant research, undeclared platforms, publication or deployment |

**Human participant research is DEFERRED by project policy.** It is not a required automated-release gate, and it must not be recorded as passed. Automated interaction/accessibility verification remains required for the supported web product. Native application and offline-specific checks become obligations only when those targets/capabilities are explicitly declared. An unavailable required web browser is a blocker, not an inapplicable target.

The authoritative gate profiles in [gates.json](../contracts/gates.json) are:

- `core`: G0, G1, G2, G3, G4.
- `web`: G0, G1, G2, G3, G4, G5, G6, G7.
- `release`: G0, G1, G2, G3, G4, G5, G6, G7, G8.

## Traceability and meaningful coverage

[requirements.json](../contracts/requirements.json) defines 86 requirements. [acceptance-cases.json](../contracts/acceptance-cases.json) defines 96 scenarios, including ten cross-domain fault/race/recovery cases. Requirement `acceptanceIds` and case `requirementIds` are reciprocal. Each case names its gate, preconditions, action, observable outcomes, automation environment and expected evidence. Milestones name their prerequisites and assigned requirements.

Every implemented work item identifies its requirement IDs and acceptance cases. A test can cover several cases when it actually asserts their behavior; several tests can provide evidence for one case. Coverage is a semantic mapping, not a line-coverage percentage or a count of named tests. Renaming an existing test to an acceptance ID does not establish that its assertions exercise the scenario.

Milestone progression checks the cases assigned to that milestone's gate. Some requirements also link to later cross-domain cases; those remain explicitly pending until their assigned gates. For example, M1 can establish command idempotency before M4 verifies its interaction with provider reservations. A requirement is globally complete only after all of its applicable required cases pass. This distinction avoids circular milestone dependencies without waiving integration evidence.

Required cases cannot be satisfied by placeholders, `true`, a successful `echo`, static screenshots of a previous version, a planned command, a mocked browser or a prose claim that testing was done. Negative scenarios should assert the expected rejected operation inside a successful test harness; the gate command itself exits zero only if the assertions hold. A gate command that fails or times out is not converted into a pass through an exception list.

Priorities guide implementation order. They do not silently waive requirements. A deliberately changed product scope updates the relevant requirement, case, milestone, applicability, documentation and reviewer rationale together. Required web behavior does not become optional because its test is inconvenient. A native/offline extension can be excluded with an explicit target rationale without blocking the core web product.

## Binding the verification plan

The provided [example plan](../config/verification-plan.example.json) is intentionally incomplete. Its required gates have empty command arrays and its review evidence is unset. This lets the handoff verifier inspect the contract without providing a shortcut to product PASS.

After implementation, create a reviewed target-repository plan that binds each required gate to actual available tests/tools. Every command is an object containing:

| Field | Meaning |
|---|---|
| `id` | Stable command identifier within the plan |
| `argv` | Nonempty array of literal executable arguments; no shell interpolation |
| `cwd` | Existing relative directory inside the target repository |
| `timeoutSeconds` | Positive bounded timeout appropriate to the operation |
| `expectedExitCodes` | `[0]` for a successful gate harness; assertions handle expected negative application outcomes |
| `coversAcceptanceIds` | Existing cases whose assertions this command actually exercises |
| `evidenceArtifacts` | Relative paths to real, nonsecret output artifacts created by the command and hashed in its receipt |

Use the actual project's tool inventory and test interface. Do not invent future OMP flags, a future test module or a product CLI based on this document. Existing baseline suite commands can seed discovery, but their assertions must be inspected before assigning new acceptance coverage. A wrapper around a host tool may be necessary; it must record the actual host call and result, not merely return success after generating a plan.

Run the handoff tool after the binding is concrete. From this pack's root, the interface is:

```bash
python tools/run-gates.py --repo /absolute/path/to/worktree --plan /absolute/path/to/verification-plan.json --profile core
```

The same interface selects `web` or `release`; the plan's `targetProfile` must match the requested profile. Obtain the exact source and plan digests for a review record with:

```bash
python tools/run-gates.py --repo /absolute/path/to/worktree --plan /absolute/path/to/verification-plan.json --fingerprint
```

These are handoff-tool interfaces, not new application commands. The fingerprint helper observes identity; it does not execute a gate or establish readiness.

Unknown/missing gate IDs, empty required commands, missing acceptance coverage, invalid paths, missing outputs, timeouts and unsuccessful exits are failures or blockers. A required tool's absence is not a test skip that qualifies the release. Tool installation remains governed by the existing session authorization and environment policy.

## Source and artifact fingerprints

Evidence is bound to the exact candidate, not just to `HEAD`. A useful fingerprint records the commit/tree identity and a deterministic digest of relevant current source bytes, paths and modes, including allowed dirty/untracked product files. The verification plan has its own digest. Release requires a clean candidate by default. Intermediate work may explicitly allow a dirty candidate, but its actual content is still hashed and reported.

Excluded paths must be declared and justified: private runtime state, credentials, caches, generated evidence and declared build-output directories. Exclusions must not conceal implementation, tests, configuration or distributable resources. Paths containing private information are redacted from user-facing summaries while the local auditable manifest retains the information necessary under the project's data policy.

Capture source identity before and after gate execution. A source change during the run invalidates the result even if the test command returned zero. Tests should write output to declared ignored locations, not modify tracked product files. Review evidence must match the same `sourceFingerprintSha256` and `reviewedPlanSha256` used by the gate runner.

Each final source ZIP, sdist and wheel has an independently recorded SHA256 digest, build provenance and isolated-install evidence. Artifact tests identify the exact digest they consumed. Rebuilding different bytes or changing version metadata after testing creates a new candidate artifact; earlier passes do not transfer automatically. Keep the source/plan/artifact relationship inspectable rather than relying on a filename or version string alone.

## Gate and evidence records

Record `NOT_RUN`, `RUNNING`, `PASSED`, `FAILED`, `BLOCKED`, `DEFERRED`, `NOT_APPLICABLE` or `STALE` as distinct states. An implementation may use equivalent internal status names, but the public meaning must remain clear. A requirement with code but missing evidence is implemented-unverified, not complete.

A command receipt should include actual argv and working directory, start/end time, process result, timeout state, source/plan digests, covered cases, evidence paths/digests, and redacted diagnostics. Browser receipts also identify tool/version, engine/project, viewport and exercised flow. Performance receipts identify fixture digest, environment, iterations and raw samples. Host receipts identify actual installed runtime and observed capability.

The gate runner can check mechanical conditions and coverage declarations. It cannot prove that a test's assertions are meaningful merely by inspecting its exit code. Release review therefore checks the code, assertions, fixture realism, negative behavior and evidence mapping. Do not treat a validator as an oracle for product correctness.

Large logs remain local evidence with concise summaries. Preserve complete failure details needed to reproduce a problem; do not compress away path, version, amount, identity, assertion or return code. Screenshots and traces use synthetic project data and redacted credentials. A screenshot establishes appearance at one observed state, not unexercised interaction behavior.

## Test strategy by risk

### Domain and adapter contracts

Use shared fixtures to submit equivalent commands through CLI, MCP and HTTP. Cover omitted/null/empty/whitespace inputs, structured errors, invalid enums, expected revisions, authority and result parity. Test downstream validation too: an approval accepted by a surface must remain valid when the workflow later checks it.

Assert durable outcomes and invariants rather than the implementation's private sequence of helper calls. Schema tests confirm shape; behavioral tests establish optional-field meaning, dependency-scoped staleness, authority and safe replay. Reusable schema definitions and meaningful error contracts follow the principles in *Designing Web APIs*, first edition 2018, supplied PDF pp.61–69 and 131–140. The project-specific invariant choices are defined in the domain contract.

### Races and failure injection

Use deterministic barriers and fault points rather than relying on timing luck. Exercise both orders for approval/revision, accept/cancel, cap reduction/reservation and late completion/cancellation. Inject failure before transaction commit, after commit before response, before external dispatch, after dispatch before receipt, during projection rebuild and between migration validation/activation.

For paid work, use a controlled provider fixture with a durable request/charge log. No live expenditure is required for financial correctness tests. A lost provider response means uncertainty, not free work. Reconciliation, duplicate receipts and reservation retention must be observable in the ledger.

### Migration and rollback

Keep synthetic fixtures for every supported legacy version and for incomplete history. Verify original bytes, stable mapping, restartability, missing-reference quarantine and truthful unknowns. Test restore after both unchanged and divergent post-migration state. Check live-consistent backup restoration and the actual SQLite runtime/journal policy. Do not simulate recovery solely by catching an exception in the same process; include reopen/restart evidence at important boundaries.

### Browser and accessibility

The repository's existing `AGENTS.md` requires `playwright_fast` or `/pw-fast` planning followed by actual execution. Routine interaction changes use `affected` or `quick` with Chromium. Release uses `matrix` or `full` across configured Chromium, Firefox and WebKit projects. Preserve real traces/screenshots and interaction assertions. Pure documentation work does not itself require launching a browser; it also cannot establish a new product browser pass.

Exercise approval, annotation, viewport changes, forms, navigation, dialogs, errors, stale state, cancellation, retained drafts and hostile content. Keyboard and nondrag single-pointer alternatives are separate tests. Check semantic names/state, focus, applicable contrast, reflow/zoom, reduced motion and meaningful status updates. Automated scans cover only part of the accessibility target; report that boundary rather than claiming universal conformance.

Use the detailed [accessibility/performance specification](ACCESSIBILITY-AND-PERFORMANCE.md). Its numerical performance budgets are proposed fixture-specific engineering targets. The 7±2 memory shorthand and 400 ms engagement claim in introductory resources are not universal acceptance thresholds. For accessibility, consult the normative [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and criterion-specific interpretation; in particular, [dragging alternatives](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html) do not follow automatically from keyboard support.

### Host and integration checks

Use an actual supported MCP client/transport against the installed runtime. Verify observed tool/resource access, package paths and capability reporting. Exercise OMP discovery in the actual host; a direct-reading fallback can be a documented supported path but is not native discovery evidence. A stub host is valuable for fault tests, yet does not satisfy a claim that the real integration worked.

Keep model/provider tests controlled when possible. Record actual assignment and capability observations when claiming a host routed work. Requested names or configuration files alone are not proof. Check current-model preservation, role-default precedence and explicit fallback behavior without requiring arbitrary live provider spend.

## Distribution isolation matrix

| Deliverable | Isolated procedure | Required conclusion |
|---|---|---|
| Source ZIP | Build, hash, extract outside the checkout, clear source-path leakage, run documented project install and packaged verification | Every advertised source workflow has its scripts, docs, fixtures, license and resources; no hidden checkout dependency |
| sdist | Build, hash, extract into a clean directory, build a wheel using only supplied build inputs and declared dependencies | Wheel construction does not read the original checkout or omitted private files |
| Wheel | Install normally into a fresh environment, invoke from a nonrepository directory, inspect imports and package resources | Runtime, MCP, dashboard and bundled guides/assets work from installed package paths |

A wheel may intentionally omit repository-only installer/docs/tests. Record that in the distribution matrix and test its public contract using an external controlled harness. Do not require the wheel to carry the entire source tree merely to make tests convenient. Conversely, if the source ZIP advertises a packaged test suite, its required fixture/document dependencies must be present. Test from the extraction to catch the baseline missing-remediation-document failure.

Test installation with inherited destination/environment overrides in a disposable environment. Ensure `PIP_TARGET`, `PIP_PREFIX`, `PYTHONPATH` or a colliding user executable cannot redirect or impersonate the supported runtime. Test source ZIP paths containing spaces and a non-Git target root. Preserve unrelated instructions, configs, file modes and executables through upgrade/restore.

Scan full archive member lists and seeded sensitive canaries. Exclude private state, credentials, user project files/artwork, source books, caches and environments, including nested examples and path overrides. Verify manifests and required licenses. Keep package-version and bundled-schema/capability differences explicit.

## Substantive review and independence

The release plan's review pointer is:

```json
{
  "independent": false,
  "reviewer": "",
  "evidencePath": ""
}
```

These empty example values are intentionally not a completed review. The referenced review record contains:

- `schemaVersion`, `sourceFingerprintSha256` and `reviewedPlanSha256`.
- `reviewer.identity`, `reviewer.actorId`, `reviewer.independent`, `reviewer.implementationActorIds`, `reviewer.method` and an applicable `fallbackReason`.
- `findings.severeOpen` and a list of findings with severity, affected scope, evidence and resolution.
- `checkedAcceptance`: an entry for every release case with `acceptanceId`, actual `result`, existing `evidencePaths` and a substantive note.
- `recommendation`: `ready`, `ready-with-disclosed-fallback` or `blocked`, consistent with the findings and review method.

For `independent: true`, the reviewer actor must be genuinely distinct from the implementation actors. Prefer an independent inspection of behavior and assertions, not merely rereading the implementer's summary. The actor identity can be an auditable agent/session ID; personal identifying data is unnecessary.

When distinct review is unavailable, set `independent: false`, `method: declared-sequential-fallback`, and record the concrete reason and role separation procedure. The result is **PASS_WITH_DECLARED_REVIEW_FALLBACK**, never an independent-review pass. It still requires substantive checks, complete acceptance mapping, current fingerprints, existing evidence and zero unresolved severe findings. Human participant deferral does not remove this review obligation.

Severe findings include data loss/corruption, authorization bypass, duplicate paid dispatch, invalid approval binding, unsafe migration/restore, broken advertised installation and failure of a critical supported interaction. Cosmetic findings can be prioritized separately, but a failed required acceptance case cannot be hidden by calling it cosmetic. Resolve issues or revise scope openly with coordinated contracts.

## Final release procedure

1. Resolve the candidate and supported target matrix; complete required implementation and documentation.
2. Commit the intended source. Freeze the reviewed plan and record both digests.
3. Run the required profile with actual commands and inspect outputs, failures and skips.
4. Build and test exact source ZIP, sdist and wheel artifacts in isolation; retain digests and provenance.
5. Run the configured browser release matrix and review its actual traces/results.
6. Complete substantive review against the current source, plan and all release cases; fix severe findings and rerun affected checks.
7. Assemble a coherent readiness receipt and handoff with actual support/rollback evidence, deferred research and target limitations.
8. Perform push, merge, tag, publication or deployment only under the existing session/project authority for those actions. Readiness itself changes none of that authority.

If a required tool or environment remains unavailable, finish independent authorized work and report the specific blocked cases, exact error, safe alternatives tried and resumable next step. Do not silently weaken the gate, fabricate results or repeatedly retry unchanged inputs.
