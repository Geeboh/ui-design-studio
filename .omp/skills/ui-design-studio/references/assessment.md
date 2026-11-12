# Assessment and user guidance

Use this reference during `ui-assess` and when a later design decision exposes a gap in the brief. Store the assessment, inventory and supporting evidence under `docs/design/runs/<id>/`. Read the director's current workflow and configured gates before writing results.

## Establish the evidence

Follow [project-context.md](project-context.md) to derive requirements from the real project before recommending a framework, component library or theme architecture. Do not request or infer a named project profile. Read applicable `AGENTS.md` instructions, requirements, existing design decisions, routes, navigation, dialogs, style entry points, test scripts and build configuration. Identify the current branch and uncommitted work. Discover the existing development URL and authentication or fixture needs; do not invent a working preview.

Build a baseline using representative content and tasks. Capture relevant screenshots, console/network observations, build sizes and test results where tools permit. Record the source revision, browser or native runtime, window/viewport, device or emulation, cache condition and commands beside each measurement. Prefer small evidence excerpts and linked artifacts to enormous logs.

Label every substantive claim as one of:

| Label | Meaning |
| --- | --- |
| Observed | Reproduced in the application or directly established from source. |
| Measured | Produced by a recorded command or instrument under stated conditions. |
| Inferred | Expert interpretation supported by specified evidence. |
| Hypothesis | A plausible user need or consequence requiring investigation. |
| Unverified | Necessary evidence or execution access is missing. |

An agent walkthrough is an expert review. It is not a user study. Do not invent user quotations, task-success rates, time savings, accessibility certification or benchmark improvements. Name assumptions about people and usage conditions instead of disguising them as research.

## Inventory every surface

Reconcile routing definitions, navigation, source searches and runtime exploration. Include pages, nested panels with distinct behavior, dialogs, drawers, wizards, settings, help, errors and feature/role-dependent screens. Record route or trigger, source location, purpose, user task, dependencies and implementation status. A route scan alone cannot establish completeness.

Keep planned or missing screens explicit. An unimplemented page may receive an agreed concept, but its mockup must not be presented as a working feature. Identify gaps between requirements and implementation without silently expanding the redesign into new product capabilities.

For each surface, inventory applicable states: initial, populated, loading, empty, filtered-empty, validation failure, unavailable/offline, permission failure, server error, partial result, stale data, success, destructive confirmation and recovery. Mark genuinely inapplicable states with a reason. Include long labels, long values, large datasets, localization expansion and narrow layouts. Test every distinct interaction; do not multiply identical states merely to inflate coverage.

## Evaluate task quality

Walk the important journeys from a user's goal through completion and recovery. Assess:

- **Orientation:** current location, available actions, navigation labels and return paths.
- **Comprehension:** hierarchy, plain language, grouping, information density and progressive disclosure.
- **Interaction:** discoverability, feedback, keyboard/touch operation, predictable focus and consistent controls.
- **Trust:** accurate status, data freshness, irreversible-action explanation, error prevention and recovery.
- **Efficiency:** recognition over recall, useful defaults, retained input and unnecessary repetition.
- **Inclusion:** visual, motor, cognitive and assistive-technology needs under realistic conditions.
- **Resilience:** slow responses, offline operation, missing resources, interrupted work and recovery.

Do not apply a “law of UX” mechanically. Explain the specific task and evidence behind a recommendation. Reducing clicks can make an operation less safe or comprehensible; spaciousness can help scanning but obscure relationships when overused.

## Write actionable findings

Give each finding a stable ID, affected surfaces, evidence, observed behavior, user impact, confidence, severity, proposed change, effort/dependencies and a verifiable acceptance condition. Distinguish severity from confidence: an uncertain catastrophic issue deserves investigation, not a falsely precise score. Prioritize broken critical tasks, accessibility barriers and misleading status before decorative inconsistencies.

The report should open with scope, strongest findings and recommended work, then link to detail. Explain what is already effective. Map recommendations to the later concept, component and page IDs so implementation can demonstrate which problems were addressed. Retain unresolved findings with an owner or next action.

## Ask useful design questions

In guided mode, show the assessment and ask only unanswered questions that affect decisions. Prefer a small batch with concrete alternatives:

1. Which tasks and frustrations deserve priority?
2. Which references are appealing, and which aspects: colour, type, spacing, shape or navigation?
3. What should remain familiar, and what may change substantially?
4. Which devices, input methods, lighting conditions and density preferences matter?
5. On subsequent runs, modify the default theme or create a new theme, unless already specified?

Record answers in the brief. In yolo mode, use established preferences, evidence and the director's decision rubric, recording `agent-yolo` as the decision maker. Do not repeatedly ask for preferences already supplied.

Accessibility assessment must combine automation and direct inspection; [W3C's evaluation guidance](https://www.w3.org/WAI/test-evaluate/tools/) explains why tools alone cannot establish accessibility.
