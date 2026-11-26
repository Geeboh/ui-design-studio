# Product and UX specification

Status: implementation target for UI Design Studio 2.0.0, working name **PRISM Studio**. This document specifies proposed behaviour; it does not claim the current application provides it. Requirement IDs refer to [the requirement contract](../contracts/requirements.json). The current policy defers human participant research; automated verification remains required.

## Contents

- [Product outcome](#product-outcome)
- [Information architecture](#information-architecture)
- [Decisions and modes](#decisions-and-modes)
- [Focused revisions](#focused-revisions)
- [Decomposition and partial approvals](#decomposition-and-partial-approvals)
- [Design budget](#design-budget)
- [Persistent model settings](#persistent-model-settings)
- [Theme lifecycle](#theme-lifecycle)
- [Recovery and completion](#recovery-and-completion)

## Product outcome

Let a person turn a design goal into inspectable artifacts, make precise decisions, request bounded revisions and continue authorized work without losing accepted progress or spending blindly. Preserve the shared Python engine, CLI/MCP/dashboard parity, local installation and existing `ui-*` aliases. A new name does not justify a framework rewrite or a second workflow engine.

The primary context is a desktop creation and review tool with repeat users. Support narrow layouts and touch input without forcing the expert desktop workflow into a phone wizard. The important outcomes are time to first useful artifact, successful decision/revision completion, retained work, clear cost exposure and trustworthy resume. Aesthetic preference and stakeholder approval are evidence of those decisions, not proof of end-user usability.

Source basis: B10 PDF pp8–18,35–62,69,234–237; B08 pp41–47; U07's task-oriented review; C01/C06 cognitive walkthrough. Source IDs resolve in [the source register](../knowledge/SOURCES.md). These sources inform the proposal; the product's approval, cost and scope rules are project policy.

## Information architecture

| Surface | Primary task | Required content and behaviour |
|---|---|---|
| Landing / connection | Reach a real project and run | Product and installed version, connection state, selected project root, recent runs, create/resume actions, precise repair steps for incompatible bridge/runtime. Explain an unavailable capability before invoking it. |
| Run overview | Understand what needs attention | Goal, stage, mode, current artifact/component, next allowed actions, waiting reason, last committed revision, actual active work and budget summary. |
| Review workspace | Inspect and decide | Real artifact viewer, stable component list, version selection, annotations, before/after comparison and a decision panel bound to the displayed version. |
| Work queue | Understand and control work | Queued/running/waiting/unknown/failed/cancelled/completed attempts; dependencies, scope, actual model, cost reservation and cancellation/reconciliation actions. |
| History / evidence | Explain what happened | Version lineage, decisions and actors, changed scope, receipts, evidence status and exports; paginated or bounded presentation. |
| Settings | Change defaults deliberately | Project/personal/run scope, mode, model policy, budget policy, theme controls and capability diagnostics. Keep advanced controls discoverable without burdening every decision. |

The run identity, selected component/version, connection freshness and budget remain visible during review. Preserve selection, expanded sections and viewport when background updates arrive. Do not move focus or reorder the comparison merely because a new artifact appeared. Surface a visible “new version available” action instead.

### Landing and connection

Distinguish disconnected, connecting, connected, unauthorized, incompatible and stopped states. Show a safe user action for each; do not expose bearer credentials in page text, logs, screenshots or exports. The initial experience must reach an actual artifact and a persisted decision, not stop at a tool list.

Resolve the project root explicitly and retain it in the run. Offer a selectable recent root or a correctly validated new root. A non-Git project remains a supported, explicit case. Show which runtime and project the connection controls. Avoid silently switching from a project installation to a different global version.

### Real artifact review

Support raster, SVG, HTML and PDF through appropriate safe renderers; expose unsupported formats honestly. Show the retained artifact, its version and trustworthy provenance. A thumbnail is a derivative, not the approved source. Preserve a full-resolution view, fit/actual-size controls and accessible zoom. Clearly distinguish a live preview from an immutable review capture.

Treat user-produced HTML/SVG as untrusted content. Preview isolation, network policy and capability boundaries must prevent artifact scripts from receiving dashboard credentials or gaining dashboard authority. A missing or failed render is a visible failure, never a generic success placeholder.

Comparison starts with a stable side-by-side or explicit before/after selection, synchronized where useful. Label differences that are known from version/scope records; do not claim a visual diff proves semantic or accessibility equivalence. Dense comparison needs context, not decorative motion.

## Decisions and modes

Requirements: REQ-APPROVAL family; REQ-UX-001 through REQ-UX-006.

| Decision | Guided | YOLO |
|---|---|---|
| Choose among materially different design directions | Present a concrete reviewable choice and obtain the relevant user decision. | Select within the goal, constraints and design budget; record an agent decision and rationale. |
| Routine implementation detail inside authorized scope | Continue and record material tradeoffs. | Continue and record material tradeoffs. |
| Change scope, exceed a hard design cap or perform an otherwise unauthorized external action | Obtain the required authority before that action. | The same boundary applies; YOLO creates no additional authority. |
| Resume | Reuse stored mode, decisions and settings unless explicitly overridden. | Reuse stored mode, decisions and settings unless explicitly overridden. |

Each decision records actor type, selected component/artifact version, relevant dependency fingerprint, decision kind, feedback and expected request revision. Human “Approve” with no comment is valid; the core normalizes omitted, null, empty and whitespace feedback to an empty string. “Changes Requested” needs actionable text or at least one valid annotation reference; “Rejected” needs an explanatory reason; delegated agent approval needs a decision explanation. Enforce these same conditional rules at every interface and show the inline reason before submission.

Use server-provided allowed actions and disabled reasons. An accepted response returns the committed result immediately; a lagging projection must not turn it back into “pending.” A stale decision explains which relevant version changed and offers refresh/compare/reapply, without discarding the user's draft. Unrelated stage progress must not invalidate an otherwise applicable approval.

YOLO agent decisions must never be labelled human approval. Actual user decisions remain accepted in both modes. Switching modes records a new policy choice and affects subsequent decisions; it does not rewrite history. Continue already-authorized work without repeatedly asking for the same approval.

## Focused revisions

Requirements: REQ-REVISION-001 through REQ-REVISION-003 and REQ-REVISION-006.

Offer **Revise selected area**, **Revise component**, and **Decompose and revise** as different scopes. A request identifies what must change, what must remain stable, the desired result, affected component IDs and relevant acceptance checks. Preserve accepted independent work.

Use the architecture contract fields: `baseArtifactVersionId`, `baseArtifactSha256`, `annotationSetId`, `annotationSetRevision`, `componentIds`, `instructions` and `scopeFingerprint`. The selected base is immutable. If it is no longer current, offer a branch from that version or an explicit rebase with conflict review. Never silently attach old annotations to a new image.

### Annotation contract

- Bind each annotation set to the exact base capture, image dimensions and digest. Coordinates use `coordinateSpace: normalized_image` with finite `x` and `y` in [0,1]. Translate from the rendered image rectangle after object-fit, letterboxing, pan and zoom; never use surrounding stage bounds as the image.
- For HTML or PDF, create an immutable image capture with source-artifact dependency and capture viewport/device-pixel-ratio metadata before annotation. Changing the capture changes the base identity.
- Line, arrow, rectangle and ellipse use exactly two points: start and latest endpoint. A pin has one. Freehand uses 2–128 points; at most 256 annotations per set; annotation text is bounded at 4,000 characters. Obtain authoritative limits from capabilities and keep client/server validation consistent.
- Preserve the raw in-progress draft locally. If simplification is needed to meet the advertised point limit, preview its result; do not silently truncate the stroke. Save acknowledges the normalized persisted representation. Distinguish saved, local-only, conflicted and failed drafts.
- Provide keyboard-accessible shape selection, coordinate/region adjustment, annotation list and delete/undo; provide a separate click/tap alternative for applicable dragging actions. A freehand exception requires a narrow documented necessity, not an exemption for all tools.

The worker receives the pinned base/capture, region coordinates, relevant instructions and bounded dependencies. Return a new immutable version, a change summary, checks of protected regions and explicit limitations. Localized regeneration may affect surrounding pixels; promise bounded requested scope and verified comparison, not mathematically identical untouched pixels unless the implementation proves that guarantee.

## Decomposition and partial approvals

Requirements: REQ-REVISION-004 through REQ-REVISION-006.

Assign stable component IDs to logical units such as navigation, pricing card or checkout form. Record versioned dependency edges; validate the graph is acyclic. The graph is a workflow model, not a requirement to split the application into microservices.

A decomposition preview lists components, exact extracted/base versions, dependencies and expected cost before dispatch. Guided mode asks for the relevant decomposition decision; YOLO can choose within scope and budget. An existing accepted artifact remains historical evidence after decomposition; it must not become fabricated approval of newly extracted components.

Allow individual and batch decisions. A batch response has a per-item outcome and replayable receipt: successful items remain accepted even when another item conflicts. Validate each selected component/version and do not silently approve unselected dependencies. Surface “accepted,” “needs revision,” “blocked by dependency,” and “superseded” separately.

On revision, invalidate only the changed component versions and affected dependents. Preserve accepted independent versions. Reassemble a composition with exact input versions, then verify layout/integration/accessibility again. Component approval does not automatically approve a changed whole composition. A graph change or conflicting concurrent revision is visible and recoverable.

## Design budget

Requirements: REQ-BUDGET-001 through REQ-BUDGET-007.

The monetary cap is for **design work**: concepts, mockups, artwork and design revisions; critique is included when configured. Implementation and building this pack are separately tracked and excluded by default. A token target is useful for context efficiency but is not itself a monetary cap.

Choose an explicit currency and display it with all amounts. Use the domain contract's integer `Money` fields: `amountMinor`, `currencyCode` and `currencyExponent`; no floating-point monetary amount is accepted. Validate the configured currency/exponent pair, not merely a three-letter spelling. Never add unlike currencies or assume conversion. Version 2.0 performs no implicit foreign-exchange conversion; any future conversion feature needs an explicit rate, timestamp and policy. Unpriced work is **unknown**, not free.

Show cap, settled charges, outstanding reservations, pending unknown charges and available capacity. Make “estimated,” “reserved,” “settled,” “refunded,” and “unknown” visually distinct. Scope changes and cap increases are recorded; they do not retroactively reclassify historical spend. The revision dialog estimates only its requested scope and identifies assumptions.

Hard enforcement requires controlled dispatch, an admissible bounded charge and atomic reservation before every billable attempt. Concurrent workers cannot both claim the same remaining amount. If the host/provider cannot bound or control charges, label the mode **advisory** and state the limitation before calling it a hard cap. Provider choice and retries must honour the same admission path.

After timeout or cancellation, retain unresolved reservation/exposure until reconciliation establishes the charge. Cancellation can stop queued work immediately, but does not promise a running provider will stop billing or issue a refund. An unknown result offers inspect/reconcile/retry-with-explicit-duplicate-risk according to policy. Do not dispatch an automatic second paid attempt merely because a response was lost.

## Persistent model settings

Requirements: REQ-MODEL-001 through REQ-MODEL-005.

Store role defaults for the director, research/assessment, planning, design generation, implementation and review as capabilities and provider/model choices when known. Support **current-model** mode. Show requested policy and actual observed assignment separately; do not assert that a host used a model merely because a prompt requested it.

Precedence is explicit invocation override; persisted run policy on resume; project defaults; personal defaults; capability/cost-based auto selection. Resuming a run does not silently replace its policy with newly edited personal defaults. A deliberate “apply defaults to this run” action previews the changes.

Settings show their scope and inheritance. Validate availability, supported modalities/tools and enforceable cost bounds before dispatch. Query current capabilities and price data where available, recording provenance and retrieval time. No frozen model names, fabricated price tables or unsupported “minimum model” claims.

If a selected model becomes unavailable, expose the configured fallback choices: compatible substitute within budget, current model when adequate, or a visible wait. Do not silently downgrade a required capability or bypass a hard cap. Independent workers may run concurrently only within available slots, dependency constraints and budget reservations.

## Theme lifecycle

Requirements: REQ-THEME-001 through REQ-THEME-003.

Distinguish three scopes: dashboard appearance, generated product design tokens, and an installed OMP host theme. Naming a colour preference does not authorize replacing the host theme.

Support inspect, preview, install, activate, list, restore and uninstall where the host capability exists. Show the active theme and scope. Validate token completeness, contrast, focus and reduced-motion behaviour for each supported dashboard theme. A theme override must not alter artifact content or decision validity unless the generated design itself changes.

For host installation, stage validated files, detect conflicts, preserve originals and record an auditable ownership receipt. Restore only the receipt-owned version when current bytes match expected ownership; report user-modified conflicts without overwriting them. Upgrade and uninstall preserve unrelated themes/settings. If the installed OMP version lacks an operation, report that exact limitation and a supported recovery route. Do not claim successful activation from a copied file alone.

## Recovery and completion

Requirements: REQ-UX-003, REQ-UX-004; INSTALL, EVIDENCE and MIGRATION families.

Every slow operation exposes its actual state, useful progress when known, and cancellation/recovery options. Use an indeterminate indicator when completion percentage is unknowable. Keep previously committed artifacts reviewable while a provider is unavailable. Failure messages name the affected action, safe reason, retained work and next valid step.

Retain drafts through refresh, reconnect and recoverable conflicts with an appropriate local storage policy; never persist capabilities with them. Scope drafts to project/run/artifact/version to avoid cross-project leakage. Reconcile server acknowledgement before showing a final saved state.

The domain stages are `assess`, `plan`, `design`, `produce` and `finalize`; display labels can be friendlier without changing those values. Lifecycle (active, paused, completed, cancelled, recovery required or archived) is separate from stage. Design-only scope finishes with design/handoff evidence and does not imply production passed.

Completion states distinguish design accepted, implementation complete, automated checks passed, host integration verified and human participant research deferred. Deliver real artifacts, exact versions, decisions, cost status and outstanding limitations. A package verification receipt establishes pack integrity only. See [accessibility and performance](ACCESSIBILITY-AND-PERFORMANCE.md) and [skills/context](SKILLS-AND-CONTEXT.md) for the implementation and evidence boundaries.
