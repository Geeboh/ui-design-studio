# User choices and yolo mode

## Guided assessment

Inspect the project and resolve its source-labelled requirements before asking questions. Do not ask the user to choose a profile. Reuse known preferences, requirements and prior answers. Show concrete findings, then ask only unresolved questions that can alter the outcome:

1. Which tasks deserve the most attention? Present the actual top tasks found, with a suggested order.
2. Which visual direction fits: restrained/calm, practical/technical, or more expressive? Offer reference samples when available, not labels alone.
3. For supplied pictures, which properties matter: palette, typography, whitespace, density, geometry, navigation or overall mood? Ask what to avoid.
4. Which devices, input types, lighting and accessibility needs must guide design? Mark unspecified hardware as unknown.
5. What must remain familiar and what is frustrating now?
6. If a Studio default already exists, modify it or create a new named theme? Do not ask again if the invocation answers this.

Present Plan alternatives with screenshots or runnable local HTML, their major tradeoffs and a recommendation. Allow a combination of specific elements; then reconcile it into one system. Present the entire Design index for approval, not a single representative page. Record user approval only when a real user instruction approves the named artifacts; silence is not approval. Continue implementation and finalization without redundant permission requests.

## Yolo design authorization

`mode=yolo` delegates aesthetic selection, hybrid reconciliation, theme naming, Plan approval, Design approval and final design acceptance to the director. It applies to the current run unless explicitly made a project preference. It does not change harness permissions, expand project scope, waive quality gates or authorize unrelated external deployment.

Do not ask cosmetic questions in this mode. Use the actual assessment, known constraints and reference inputs. Select a clear direction, explain it in the decision log and continue end to end. Ask only for a genuine blocker that cannot be safely resolved, and first finish independent work.

### Selection rubric

Eliminate directions that violate hard constraints before scoring. Missing mandatory pages, critical task failures, known accessibility failures, forbidden remote dependencies and unresolved budget breaches cannot be offset by visual appeal.

Score each surviving concept 1–5 on the following package-defined criteria:

| Criterion | Weight |
| --- | ---: |
| Task clarity, discoverability, feedback and recovery | 30% |
| Accessibility and readability | 25% |
| Visual coherence, hierarchy and craft | 20% |
| Offline simplicity, bandwidth and performance | 15% |
| Fit with existing code and ease of maintenance | 10% |

Weighted score = sum(weight × score / 5). These scores are structured expert judgement, not measured user satisfaction. Link each rating to artifacts and findings. Have an independent critic challenge the winner, identify at least the strongest alternative and test weak assumptions. Resolve material findings before approval. Tie-break toward clearer task execution, lower measured/expected cost and lower integration risk.

For mockups, inspect all required cases with the quality rubric rather than repeatedly scoring brand aesthetics. Iterate against concrete findings. Default to three focused repair attempts per unresolved blocker; after that change the approach or report the blocker. Continue unaffected work. Do not loop indefinitely or lower acceptance criteria to manufacture success.

### Naming

Choose a distinctive, descriptive 1–3 word theme name appropriate to the project. Use a lowercase hyphenated ASCII ID, validate collisions, and keep the ID stable on later edits. Avoid claiming association with an organization or copying a reference brand's identity. Naming does not change the application/product name. `Fieldstone` is the included demonstration, not a required TADA choice.

### Decision provenance

Each decision records stage, actor (`user` or `agent-yolo`), outcome, rationale and hashes of the actual inputs. Record preferences and assumptions separately. Never write `user-approved` for an autonomous appraisal. A reviewer approval proves that a review was recorded; it does not magically prove every claim in that review. See `run-records.md` for the machine contract.

## Theme lifecycle

1. Inventory an existing theme system, imported themes, hardcoded styles and user preferences first. Missing `themes/registry.json` does not mean no prior design exists. Preserve a legacy fallback, mapping it to the host API as needed.
2. On the first successfully finalized Studio run, register the produced module as the default and verify it in the application. Scaffolding/installing the skills never changes the default by itself.
3. On subsequent guided runs, resolve `modify-default` versus `new`. For modify-default, keep the stable ID, increment its version and retain rollback evidence. For new, create a new ID and retain the existing default unless explicitly requested otherwise.
4. On subsequent yolo runs without a specified action, choose a new named module and preserve the existing default. An explicit request to modify/default a theme wins. Record this decision rather than interrupting for confirmation.
5. Changing the global default must not silently erase existing individual preferences. Distinguish first-time/default selection from user overrides, and document migration behaviour.
6. Register only after current theme/run validation and independent review. Test missing/invalid selection fallback, persistence, theme switching, state preservation and rollback. An edited registry alone is not an implemented theming interface.
