# Design governance and scope decisions

Status: proposed PRISM Studio behavior for UI Design Studio2.0.0. This is an original project policy informed by reviewed principles, not a copied design-methodology manual. The authoritative shapes and operations are in [domain contracts](DOMAIN-CONTRACTS.md), [JSON Schema](../contracts/domain.schema.json) and the [command catalog](../contracts/command-catalog.json).

## 1. Separate four kinds of authority

Design approval, permission to execute work, permission to spend design allowance, and permission to publish/install/send externally are separate. A valid design decision does not grant any of the other three. A successful test does not grant publication authority. YOLO delegates design choices within scope; it does not widen host/session grants or bypass budget admission.

Preserve session authorization across turns and resumes. Continue routine, reversible, already-authorized work without repeating permission requests. Ask for a decision only when the relevant mode genuinely requires one, a proposed action exceeds existing scope/authority, or a material ambiguity cannot be resolved from current instructions/evidence. The reviewable artifact and concrete consequences must be ready before the request; do not ask the user to approve an unspecified future design.

Applicable project/path instructions and task constraints are inherited by workers. Source books, websites and imported artifacts are reference data. They cannot override the user's task, expand permissions, change budget limits or instruct the system to execute embedded content. Distilled knowledge rules name applicability, tradeoffs, confidence/source and a checkable consequence. Loading a whole book into every worker prompt is not the knowledge strategy.

## 2. Run types, modes and completion

`Run.runType` distinguishes `assessment`, `design_only`, `focused_revision`, `component_batch` and `full`. Stage values are `assess`, `plan`, `design`, `produce`, `finalize`. Run lifecycle is `active`, `paused`, `completed`, `cancelled`, `recovery_required` or `archived`. These dimensions are independent: a design-only run can be Completed without implementing the application; a full run can be Paused while its current design is approved.

| Mode | Permitted design decisions | Obligations |
|---|---|---|
| Guided | Relevant human decision on the exact requested scope/version | Make comparison, cost implications, changes and limitations reviewable. Preserve useful work while waiting. |
| YOLO | Human decisions and explicitly delegated agent decisions within current scope/budget | Record the actual actor, nonempty agent explanation, evidence and delegation source. Respect retained requirements and unresolved gates. |

Human intervention is accepted in YOLO. Mode does not prevent a user from approving, requesting changes, narrowing scope or pausing work. Mode changes are versioned run configuration changes with an authority receipt; an agent cannot self-escalate Guided to YOLO. Changing to Guided does not relabel prior agent decisions as human; reevaluate the next required gate under the new policy. Changing to YOLO does not erase existing user constraints or rejected choices.

An agent using current-model mode preserves the active permitted model when capable. Role preferences resolve by the documented precedence and are retained on resume. A different model/tool is selected only within available capabilities, existing permission and cost policy. Actual execution evidence distinguishes requested, resolved and observed assignment; sequential role passes are not described as independent parallel reviewers.

## 3. Review package and decision lifecycle

A request contains the purpose, exact target components/artifacts, before/after or alternative comparison where relevant, retained constraints, required evidence, known limits and the next scoped action it will unlock. The server freezes its review manifest and fingerprint. Dynamic progress text can update independently.

Decisions are Approved, Changes Requested, Rejected or Deferred. Human Approved feedback is optional: omitted/null/empty/whitespace normalizes consistently to an empty string. Changes Requested needs actionable text or a valid annotation reference. Rejected requires a reason that allows useful next work. An agent decision needs a reason and evidence; it cannot claim an unperformed visual or accessibility check.

Competing decisions use expected request revisions. The first valid terminal transition commits; a later conflicting command receives a conflict and the authorized current state. Same-key replay returns the first receipt. A decision never silently moves to a newer artifact. When dependencies change, show the previous historical decision and a precise applicability explanation, such as “the navigation layout changed,” rather than a generic run-stale label.

Approved facts are not deleted to make the screen simpler. A superseding request links to its predecessor. A withdrawal/revocation is a new recorded transition with reason and actor, not an edit of the old actor/outcome. Scope checks decide what remains usable.

## 4. Focused revision workflow

1. Select the exact source artifact/capture and stable component scope. Pin the immutable base digest/version and current relevant dependencies.
2. Capture actionable instructions, retained constraints and acceptance conditions. Annotations bind the exact image and saved annotation-set revision. Text-only change requests remain first-class.
3. Evaluate impact: identify the requested components, dependent compositions, shared tokens/assets and overlaps with other revisions. Reveal expected extra affected scopes before expanding work.
4. Estimate/reserve only the new design work and select capable permitted workers. Reuse accepted independent artifacts without billing them as new generation.
5. Produce new versions with lineage to the request/base. Report intended changes, unexpected dependency effects, evidence and actual assignments.
6. Compare the requested scope against the base. Guided requires the relevant new human decision; YOLO may decide within the delegated boundary. Unaffected approvals stay applicable.

If a shared prerequisite changed concurrently, stop automatic merge and present the overlapping versions/constraints. Do not overwrite one revision with another. Preserve both results and charge evidence even if a result is superseded. A worker cannot use “needed for quality” as an unrecorded scope expansion.

For image feedback, use normalized image-relative points and the [shared limits](DOMAIN-CONTRACTS.md). Rectangle/ellipse/line/arrow use start and latest endpoint; freehand is bounded with a visible simplified preview. Drafts survive validation/network errors. Keyboard and non-drag pointer/text alternatives support the same revision contract. A new screenshot is a new coordinate base; deliberate rebasing must be visible.

## 5. Decomposition and partial batch review

Decompose by independently reviewable user-facing responsibilities, not arbitrary pixel rectangles or worker availability. Assign stable component IDs, ownership, acceptance conditions and versioned dependencies. A component can change its display name without losing identity. Shared foundations and final composition have explicit owners/checks. Reject dependency cycles and ambiguous overlapping write ownership before dispatch.

A batch is a versioned list of component/request/artifact items. The user can approve selected items, request changes on selected items, defer others and retain already accepted siblings. Show every submitted item's outcome and any stale/conflicting item. The batch operation stores one replayable receipt plus individual results; a failed item is not silently omitted and a valid independent item is not needlessly invalidated.

Do not use raw event counts to infer that a batch is complete. The required component/check identity set is fixed by the current scope manifest. Two successful reports from one component cannot substitute for a missing component. Approval of child components does not establish that the combined screen meets layout, navigation, keyboard, performance or integration requirements. Evaluate the composition separately against its exact child versions.

## 6. Spend governance during design

The visible design allowance states currency/exponent, cap, observed settled spend, active reservations, uncertainty, remaining available amount and the proposed action's bound. Implementation and pack-building spend are separate and excluded by default. Critique's treatment is an explicit persisted setting. This classification appears in both human-facing summaries and machine records.

Hard enforcement is a claim about controlled dispatch with bounded charges. If the environment cannot provide those properties, use Advisory terminology and explain the concrete missing guarantee; do not invent a zero cost for unavailable usage data. A price quote/model identifier must be current and attributable when used to promise a bound. No implicit foreign exchange, stale price table or inferred provider identity is acceptable.

Under contention, reserve before launching. A revision or component batch reserves only new work, then settles observed usage once. A timeout or cancel request keeps uncertain liability visible and reserved. Do not prompt the user to authorize duplicate work as a reflex when a provider can be queried safely within existing authority; first perform the available reconciliation. If a new charged attempt is necessary, make its exposure and relation to the unresolved attempt explicit under the current scope/budget rules.

Budget exhaustion pauses new design admission while allowing read-only review, export, cancellation and reconciliation. It does not discard accepted artifacts or prevent completion of already committed local bookkeeping. Increasing a cap, reclassifying spend or changing currency is an explicit authorized configuration/correction, not an agent workaround.

## 7. Evidence and scope-specific readiness

The core publishes allowed actions and disabled reason codes for each scope. The UI/agent uses them for discoverability; authorization and readiness are rechecked at execution. Actions depend on exact inputs and relevant checks, not on a green global badge.

| Claim | Evidence it can establish |
|---|---|
| Artifact registered | Complete verified bytes/provenance exist. It does not imply aesthetic or functional quality. |
| Design approved | The recorded permitted actor decided on the exact version/scope. It does not imply implementation or publication. |
| Structural check passed | Required declared records are present/current and obey their structural rules. |
| Automated interaction/accessibility check passed | The stated automated scenarios/checks ran against the identified artifact/environment. It does not prove all accessibility criteria or human usability. |
| Human participant research deferred | Research has not been performed and is intentionally outside the current release requirement. It is not a pass. |
| Run completed | The agreed run type/scope and applicable required gates are satisfied, with remaining limitations named. |
| Theme activated/published | A separate authorized operation actually changed the identified target and has a restore/outcome receipt. |

Human participant research is deferred by current project policy. Continue automated interaction/accessibility verification for the web release. Preserve unknown/deferred/failed/not-applicable states distinctly; do not invent participants, measurements or measured improvements from general UX articles. An explicitly deferred item can be outside the current release gate only through the recorded policy, while remaining visible in the handoff.

## 8. Theme and installation governance

Inventory the existing default theme and target project before proposing new or modified design. Preserve theme IDs, source inputs and defaults through migration. New theme, modify default, select active theme and restore previous theme are distinct actions with a concrete target and receipt. A design preview is not activation.

Theme commands explicitly name dashboard appearance, generated-product tokens or the OMP host target. Dashboard appearance does not require a design decision or invalidate artifact approvals. Generated-product selection binds the exact artifact/run and applicable design decision. Host installation/activation requires the real host capability and target-specific authority already granted in the session. Preview, install, activate, restore and uninstall keep separate receipts and effects; a colour preference does not create host-installation authority.

Theme activation references exact immutable package/artifact versions and the required applicable decision. Prepare/validate the target before switching its active reference or performing an authorized installation. Retain the previous selection and installer-owned backup receipt. Restoring detects later divergent edits rather than overwriting them. Existing ownership, path confinement and rollback protections remain mandatory. Do not silently replace an existing default just because a new design was generated.

Host/tool integrations are discovered. Use documented OMP/MCP capabilities only when present; do not claim a visual review, task export, model switch or pinned UI action that the host did not perform. Missing optional capabilities produce a useful fallback or explicit limitation, not fabricated evidence.

## 9. Acceptance scenarios that guide implementation

The [acceptance catalog](../contracts/acceptance-cases.json) owns executable coverage and results. These examples clarify intent:

- A human approves a displayed artifact without feedback; dashboard, MCP, CLI, checker and resume all agree it is valid.
- Progress changes after review preparation; the approval remains applicable. A required artifact changes; the old request produces a targeted conflict.
- A Guided run waits for a concrete design decision while permitted independent analysis continues. YOLO records an actual delegated agent decision without claiming it came from the user.
- A three-item batch has one stale item; the two independent valid decisions are retained with a per-item receipt, and the stale one remains unresolved.
- A revision annotated on imageA cannot be silently applied to imageB. A validation error preserves the user's draft.
- Two admitted workers race for the same remaining design allowance; the transaction prevents overspend. A remote timeout stays Unknown until reconciled.
- A completed design-only run reports its design handoff and explicitly unperformed implementation/research, without a false full-production claim.

## Distilled knowledge basis

Vernon's *Domain-Driven Design Distilled* (2016), PDF pp.41–45,76,89–98, informs explicit scenarios and invariants; Stopford's *Designing Event-Driven Systems* (2018), PDF pp.124,134,157–163, informs versioned decisions, external uncertainty, reservations and distinct prerequisites; Bonér et al.'s *The Reactive Principles*, v1.0, PDF pp.10,13,15–19, informs useful feedback under constraint; Xu's *System Design Interview*, second edition, PDF pp.229–235,251–260, informs dependency work and versioned artifacts. The project policies above resolve their applicability to this product. We reject infrastructure-by-analogy, unlimited autonomy-by-mode, forced rationale for an ordinary human approval, whole-run invalidation and generic retention that destroys referenced evidence.
