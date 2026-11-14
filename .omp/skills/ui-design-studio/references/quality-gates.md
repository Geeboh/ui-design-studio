# Quality gates and evidence

Use this reference during `ui-review` and before `ui-finalize`. Read the project's existing gates, resolved source-labelled context and current design contract. Unresolved requirements or unverified model routing must remain visible blockers; a package default or project label cannot settle them. The `tools/ui-design` helper checks the structures and properties it documents; its success is not proof of usability, complete accessibility, browser compatibility or runtime performance.

## Record honest results

For each required check, retain the method, command or procedure, source revision, environment, expected result, observed result and evidence path under `docs/design/runs/<id>/`. Distinguish pass, fail and unverified/blocked using the workflow's prescribed status values. A missing browser, inaccessible page or absent benchmark is not a pass. Describe what the check actually covers.

Use an independent reviewer for implementation approval. Reviewers inspect rendered output and task behavior, not just code or the author's summary. Yolo mode may make aesthetic choices automatically; it cannot relax acceptance criteria or convert missing evidence into approval.

Cap repair rounds at the project policy's `maxReviewIterations` value. After the cap, unresolved material findings remain `BLOCKED` with severity, reproducible case, evidence path and fix criterion; do not continue an infinite aesthetic loop.

## Accessibility and interaction

Apply the project's accessibility requirements and the host platform's guidance. The web checklist below targets [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/), applying criterion-specific exceptions accurately. For native desktop/mobile controls, use the actual platform accessibility tree, assistive technology, focus/input behaviour, text scaling and target-size rules; do not claim a web scanner or CSS-token pass establishes native accessibility. At minimum check the applicable items:

- Ordinary text contrast of 4.5:1; qualifying large text 3:1. Do not round a failing value upward. Check actual rendered backgrounds, including states and overlays. See [Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
- Applicable non-text controls and meaningful graphics at 3:1 against adjacent colours; communicate state without colour alone.
- Keyboard operation, visible focus, logical order and focus not entirely obscured. A strong 2px/3:1 focus outline can be a project policy; the corresponding Focus Appearance criterion is AAA, not AA.
- Pointer targets meeting 24×24 CSS pixels or the criterion's exceptions. Prefer comfortable 44px targets for important touch controls where feasible; do not describe 44px as the AA minimum. See [Target Size Minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum).
- Labels, names, headings, landmarks, errors, status announcements and meaningful reading order. Check representative screen-reader behavior when available and record when it was not tested.
- Text resizing, narrow layouts and equivalent 320px reflow. Maps and other essential two-dimensional content have scoped exceptions; surrounding text and controls still need usable layouts. See [Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html).
- Reduced motion and forced-colour behavior, readable disabled states, retained form input and accessible alternatives to essential gestures.

For custom widgets, follow relevant [WAI-ARIA APG patterns](https://www.w3.org/WAI/ARIA/apg/). Modal dialogs require sensible initial focus, contained tab navigation, appropriate closing behavior and logical focus restoration; consult the [dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/). Automated scans supplement manual checks; [W3C explicitly describes their limits](https://www.w3.org/WAI/test-evaluate/tools/).

## Visual and functional coverage

Reconcile every required surface/state in the inventory with a mockup, implementation and review result. Inspect long content, empty/error/loading states and responsive behavior. Exercise critical journeys end to end. Check that styling has not altered status meaning, permissions, data selection, form behavior or recovery paths.

Compare screenshots under controlled conditions, but do not equate pixel similarity with usability. Review intentional differences and dynamic-content exclusions explicitly. Verify theme switching, reload persistence, fallback after invalid selection and rollback. A later token or shared-component change invalidates affected screenshots and reviews.

## Performance and offline checks

Measure current and changed builds under the same conditions. For native applications, also measure the relevant native bundle/resource delta, startup and interaction performance using the platform's tools; CSS/gzip figures alone do not describe native runtime cost. Record raw and compressed CSS/JS bytes, fonts, icons, request count, total application shell and significant data payloads. Keep map/data costs visible as a separate category. Observe representative interaction latency and memory/CPU/GPU pressure where tools support it. Record sample count, warm-up and variability; do not claim a reliable speedup from a single noisy run.

Use configured budgets and baseline comparisons. Avoid adding a framework, font set, runtime theme engine or dependency simply to achieve an effect supported by existing components and CSS. Local assets, SVG subsets and no new theme-only JavaScript are preferred starting points, not fabricated benchmark results.

[Core Web Vitals](https://web.dev/articles/vitals) uses good thresholds of LCP ≤2.5s, INP ≤200ms and CLS ≤0.1 at field p75. Laboratory and offline appliance measurements must be labelled as such; they cannot establish field compliance. Treat TBT or a scripted click measurement as its own metric, not as INP under another name.

Resolve offline applicability from the recorded project context before selecting checks. A required offline check cannot be waived because testing is unavailable. Only a resolved `offline: "not-required"` scope may mark offline evidence not applicable, with a specific reason. Unknown applicability stays pending.

For `offline: "required"`, distinguish three conditions:

1. **Cold installed operation:** start with fresh browser state and installed local resources, without WAN access. This exposes hidden CDN/font/bootstrap dependencies.
2. **WAN-disabled operation:** preserve required LAN/local services while denying external connectivity. This is often the meaningful appliance condition.
3. **Warm cached operation:** repeat with caches populated and document their role. It cannot substitute for the cold check.

For `offline: "not-required"`, do not invent an offline product gate. Test relevant network failure and recovery behavior, and record why offline product operation is out of scope.

Browser “offline” may disable local server access too; do not confuse that with WAN loss. Verify actual requests and failure handling. Required application assets must be installed locally before claiming offline readiness. A service worker that only works after an online visit does not demonstrate a cold offline deployment.

## Release decision

Require the agreed coverage, functional checks, theme validation, project tests and documented performance/accessibility evidence. Resolve critical failures before release. Package versioned sources, generated assets, manifest, checksums, licensing information, decisions, limitations and rollback instructions. Set the first finalized theme as default only after required gates succeed; preserve the prior working theme during replacement.
