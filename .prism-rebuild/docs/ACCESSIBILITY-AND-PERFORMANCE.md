# Accessibility and performance contract

Status: proposed implementation requirements and measurement protocol. Passing the handoff verifier does not exercise the product. Requirements: A11Y, PERF, UX and EVIDENCE families in [requirements.json](../contracts/requirements.json); concrete release gates belong to [gates.json](../contracts/gates.json).

## Accessibility target and claim boundary

Target WCAG 2.2 Level AA for the shipped dashboard, landing and review flows, documenting the supported surface and any criterion-specific exception. The normative reference is [WCAG 2.2](https://www.w3.org/TR/WCAG22/), not a blog checklist. Automated scans cover only a subset of criteria. A clean scan, visual screenshot or agent walkthrough cannot establish comprehensive conformance or usability for all users.

Human participant research is deferred by project policy. Do not fabricate participants, interview findings, satisfaction scores or representative usability validation. Automated browser interactions, DOM/ARIA inspection, contrast measurements and assistive-technology checks where actually available remain useful, separately labelled evidence. A required gate blocked by an unavailable browser or tool stays blocked; a test skip does not become a pass.

## Required interaction behaviour

| Area | Required behaviour | Evidence |
|---|---|---|
| Structure and names | Use semantic landmarks, heading levels, native controls and meaningful accessible names. Keep visual hierarchy independent of document semantics. Decorative images use empty alt; informative artifacts need a useful description and accessible metadata. | Inspect DOM/accessibility tree plus representative screen-reader output when available. |
| Keyboard | Complete create/resume, artifact selection, zoom, annotate by available alternatives, decision, revision, settings and recovery with the keyboard. Use conventional composite-widget keyboard patterns; not every internal item needs a separate Tab stop. | Exercise the actual browser flow and verify active element, action results and no keyboard trap. |
| Focus | Make focus visible and unobscured. Dialog entry and exit manage focus; Escape closes dismissible surfaces; closing returns focus to a sensible invoking element. Background updates do not steal it. | Tab at normal and enlarged layouts, open/close dialogs and inject background updates. |
| Dragging and pointing | Provide a single-pointer alternative without dragging for applicable drag operations, separately from keyboard access. Shapes can use click/tap start and end; region fields and the annotation list support precise adjustment. | Complete the same operation with discrete clicks/taps; keyboard tests alone are insufficient for SC 2.5.7. |
| Target size | Meet SC 2.5.8's 24-by-24 CSS px minimum or an applicable exception, including sufficient spacing. Prefer at least 44 CSS px for primary touch actions where feasible; distinguish that recommendation from AAA requirements and native platform units. | Measure actual hit areas, spacing and layout at supported input modes. |
| Contrast and meaning | Meet applicable text and non-text contrast criteria. Never distinguish acceptance, rejection, cost or connectivity only by colour. Test all theme/state/background combinations. | Computed contrast, visible text/icons, forced-colour checks when available. |
| Motion and status | Respect reduced-motion preferences; avoid decorative continuous activity. Announce relevant committed status changes without shifting focus; avoid announcing every polling tick or percentage. | Emulate preference, inspect live regions and test milestones rather than repetitive noise. |
| Errors and recovery | Associate field errors, keep entered data, explain the correction and provide a reachable recovery action. Keep high-consequence failures visible until resolved or dismissed. | Submit invalid/empty/stale inputs, then correct them without losing draft work. |
| Reflow and zoom | Keep the page usable at 320 CSS px equivalent width, text enlargement and 400% browser zoom under applicable SC 1.4.10 conditions. Only content requiring two-dimensional layout uses the relevant exception. | Test narrow/wide and zoomed layouts. The artifact canvas may pan, but surrounding controls must remain reachable. |

Primary details: [dragging movements](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html), [target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html), and [decorative images](https://www.w3.org/WAI/tutorials/images/decorative/). These override simplified wording in U02/U06/U07/U12.

A freehand-drawing exception must be justified for that functionality; it does not exempt moving, selecting, deleting, commenting on or resizing annotations. An accessible textual revision request remains available even when drawing is unavailable. Match input capability, not only viewport width: a narrow window can still have a mouse and keyboard.

## Performance: measure the work that matters

Separate four measurements: server computation, network transfer, browser rendering/interaction, and the end-to-end design workflow. Provider generation latency does not excuse a frozen cancel control. A loading indicator reduces uncertainty; it does not make an indefinitely stalled request acceptable.

Sources B02 pp25–35,155–160,441 and B05 pp191–215,269–290 support measurement, critical-path analysis and avoiding repeated work. Their dated browser/protocol recipes do not define modern targets. Use [current forced-reflow guidance](https://developer.chrome.com/docs/performance/insights/forced-reflow) for read/write layout behaviour.

### Reproducible fixture profiles

Agree the machine/browser/storage profile and thresholds in the verification plan before collecting release results. Record build/commit, cold or warm cache, fixture digest, artifact count and sizes, iterations, raw samples and measurement method. Report p50/p95 where the sample count supports them and disclose the count. Never silently relax a threshold after observing a failure.

| Scenario | Fixture and measurement | Proposed initial project target |
|---|---|---|
| Idle run | 20 retained 256 KiB artifacts; unchanged snapshots over at least 30 observed refresh cycles | Zero rereads of immutable artifact bytes after warm-up on the unchanged snapshot path; projection metadata access stays bounded. |
| Snapshot response | Same fixture plus 100 history entries; 50 measured warm requests | Initial p95 server response target 200 ms on the named development profile; keep raw measurements and establish a justified profile-specific release threshold. |
| Pointer/keyboard feedback | Select, draw a bounded stroke, change region and submit a local decision | Immediate visible acknowledgement target 100 ms; next meaningful presentation target 200 ms excluding provider completion. Measure input-to-paint, not only handler duration. |
| Large history | At least 1,000 metadata entries and 200 artifact references | Bound initial payload and rendered window; request additional pages on demand. No inline original binaries in status responses. |
| Reconnect/cancel | Slow, failed and disconnected responses; cancelled queued and running work | Controls remain responsive; no duplicate dispatch; one active polling request per view; actual terminal or unresolved state is visible. |
| Repeated open/close | 100 viewer/annotation cycles with stable fixture | No unbounded retained observers, handlers, DOM nodes or requests; inspect retained growth rather than a single heap value. |

These numbers are proposed engineering targets, not established measurements, scientific thresholds or promises about all hardware. The verification plan is authoritative for gate configuration. If a target is unsuitable, record the evidence and approve a revised profile explicitly. Correctness invariants, such as no duplicate paid dispatch, are not relaxed by performance tuning.

### Implementation priorities

1. Build metadata projections from committed state and invalidate only relevant dependencies. Keep large blobs out of snapshot construction and event records. Verify approved content freshly at the decision boundary even when preview/read projections are cached.
2. Preserve immutable originals; use suitable display derivatives with declared dimensions. Retain lazy loading for off-screen previews. Do not lazy-load the primary above-the-fold artifact by default or destructively compress the approved source.
3. Use single-flight polling with cancellation, stale-response protection, visibility/idle adaptation and bounded failure backoff. Retain correct pagehide/pageshow recovery. Refresh immediately after a relevant committed action; do not wait for an arbitrary timer to acknowledge it.
4. Consider authenticated change streams only after removing redundant computation. SSE describes a useful one-way update pattern, but native EventSource does not offer arbitrary Authorization headers. Current bearer authentication needs an appropriate authenticated stream design; never move secrets into URLs for convenience. Preserve cursor/reconnect recovery.
5. Separate layout reads from writes; batch presentation work when measurements justify it. Do not import B02's obsolete claim that every consecutive style assignment creates a separate reflow. Fix annotation geometry before optimizing its rendering.
6. Cache by resource identity and sensitivity. Immutable non-sensitive shell assets may use long-lived caching; private snapshots, capability-bearing responses and approvals need their explicit policy. A global cache relaxation is not a performance fix.
7. Keep the current lightweight frontend unless measurements establish a concrete reason for architectural change. Profile expensive work before adding workers, dependencies or infrastructure.

Primary references: [EventSource](https://html.spec.whatwg.org/multipage/server-sent-events.html) and [HTTP caching, RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html). HTTP/2 server push and SSE are different mechanisms; retiring one does not invalidate the other.

## Web output versus Studio workflow metrics

For websites produced by Studio, evaluate relevant Core Web Vitals and representative device/network conditions. Current guidance uses good thresholds of LCP <=2.5 seconds, INP <=200 milliseconds and CLS <=0.1 at the 75th percentile of field observations. See [Web Vitals thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds). A local synthetic p95 or Lighthouse run does not establish those field percentiles.

For the Studio tool itself, also measure time to first reviewable artifact, time blocked on decisions, scope-specific revision latency, failed recovery rate and known/unknown design spend. Do not add external analytics or session recording merely because a source recommends it. Choose telemetry deliberately, minimise sensitive content and label local diagnostics separately.

## Evidence record

Each result identifies the requirement, scenario, exact build/artifact, environment, command or procedure, observations and status: passed, failed, blocked, not run or explicitly deferred. Store raw traces/screenshots where they substantiate a conclusion. A screenshot supports appearance at that state; a scripted interaction supports the exercised behaviour; neither proves an unexercised flow. Link exceptions and limitations to the exact scope they affect.
