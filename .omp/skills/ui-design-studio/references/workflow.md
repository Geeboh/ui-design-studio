# Workflow and deliverables

## Contents

1. Discovery and assessment
2. Plan
3. Design
4. Produce
5. Finalize
6. Resume and scope changes
7. Continue a legacy 1.0 run

Use the existing project's development workflow and host UI toolkit. These stages apply to web, desktop and mobile interfaces where the necessary tools are available; they add UI requirements and artifacts without replacing existing acceptance gates. Read “page” as the host's full screen or window and include dialogs, sheets and overlays. The supplied theme helpers implement the web CSS/SVG adapter; native delivery requires the explicit adapter and platform validation described in `theme-module.md`. Run from the verified project root. The package's Plan stage creates visual artifacts and is unrelated to a harness's read-only plan mode.

## 1. Discovery and assessment

Create `docs/design/runs/<run-id>/` using the helper. Resolve the source-labelled project context through [project-context.md](project-context.md); no profile selector is needed. Record source revision, dirty files, runtime version, mode, model policy, branch, real test commands and available tools in `brief.md`. Apply [model-routing.md](model-routing.md), then record actual director/worker assignments before relying on delegated work. Determine which existing task owns the redesign and which business behaviour must remain stable. A request to redesign the whole application includes every discoverable screen; reconcile router definitions, navigation, feature flags, component/dialog searches and observed runtime flows.

Read `assessment.md` and the project requirements summarized in `project-context.md`. Read the original applicable instructions before delegating their implementation. Divide the initial read-only audit between a usability specialist and an engineering/performance specialist. The director consolidates results into:

- `report.md`: executive findings, top tasks, annotated observations, priority/effort/confidence, recommendations, baseline measurements, risks and unanswered questions.
- `findings.json`: issue records with stable IDs and acceptance tests.
- `coverage.json`: exhaustive observed page/dialog inventory with required state and viewport cases.
- `baseline/`: actual measurements, local screenshots and environment descriptions; distinguish restricted/private source material from shareable output.
- `brief.md`: agreed audience, task priorities, design objectives, constraints, budget and scope.
- `project-context.md`: sources, current requirements, important preserved behaviour, offline applicability and unresolved facts; keep its hash and resolved state in `run.json`.
- Model-routing record: selected policy, available/approved choices, resolved assignments and any limitations, using `model-routing.md`.

Generate a navigable local `report.html` when it helps review; keep all required assets local. Derived charts use measured data, not invented scores. Source inspection alone can produce an assessment, but its runtime claims remain unverified. `doctor` is an environment inventory, not an automated usability evaluator.

In guided mode ask a single compact interview after showing the assessment (see `decisions.md`). In yolo, fill missing aesthetic preferences with explicit, reversible assumptions. Unknown hardware or unavailable evidence remains unknown in either mode.

**Gate A:** Findings link to evidence; inventory reconciled; project requirements and model routing are established; priorities, constraints and baseline are explicit. `assess-only` ends with the report and recommendations, without changing application styles.

## 2. Plan: coherent directions

Give 2–3 concept workers the same assessment, task scenario, content and representative page. Assign each a coherent direction. Each worker owns `plan/concept-<id>/`, never the shared theme directory. Deliver renderable local boards and specimens using HTML/CSS/SVG or the native toolkit. A web presentation of a native concept is allowed, but label it as a concept and verify native behaviour later:

1. A concept board with the visual rationale tied to findings.
2. Semantic colour swatches with token names, actual values and contrast pairs.
3. Type and spacing scale, shape/elevation rules and density settings.
4. A consistent SVG icon set and component sheet: navigation, buttons, fields, tables, status badges, alerts, cards, empty/error/loading cases.
5. Storyboards for at least one common task and one failure/recovery task; frames show intent → action → response → recovery → completion.
6. A representative complete screen/window and dialog at the applicable window/device sizes, including orientation or input variants that affect the layout.
7. Estimated incremental cost and dependency implications, labelled estimates.

Render and inspect each concept. Build `plan/index.html` for side-by-side comparison using identical data, with tradeoffs and a recommended direction. In guided mode request a selection, or specific features to combine. In yolo apply the rubric and independent critique in `decisions.md`. A hybrid must be unified by the director into one token/component contract, not a collage of incompatible controls.

Record `plan/selection.md` and a Plan approval with actor, chosen elements, rejected alternatives, rationale and hashes of the actual approved artifacts. Do not claim the user saw artifacts that could not be presented.

**Gate P:** Actual rendered alternatives exist; one coherent direction is selected; scope and design constraints are stable.

## 3. Design: every page and dialog

The theme engineer freezes `design/contract.md`: tokens, semantic roles, shared components, states, responsive breakpoints, focus behaviour, icon grammar, density/motion axes, and intended theme API. Keep this readable by every worker. Allocate page families across at least two workers when the inventory permits; one additional reviewer checks coherence.

Deliver `design/index.html` linking every mockup. Each mockup is a full page/dialog with realistic content, its surface ID and state, rather than a cropped hero or an unlabelled image. Reuse the shared host components and vector/style resources. Render the applicable window/device sizes and every distinct state, including orientation, safe-area, scaling and on-screen-keyboard effects where relevant. Specify the navigation/focus path and error recovery. Include settings, installation, management, progress, overlays and destructive confirmation surfaces; omit a state only with a recorded applicability reason.

For large inventories use waves of page families, but keep the Design gate closed until all scoped surfaces are covered. The helper requires each surface's declared state × viewport cases. Avoid meaningless combinations by splitting a materially distinct surface/state family or documenting why a state does not apply; never quietly shrink inventory to achieve a pass.

The director and independent critic inspect mockups for task clarity, hierarchy, spacing, consistency, clipping, contrast and implementation cost. Guided mode presents the complete index and asks for approval or specific changes. Yolo approves only after addressing findings. Record the approved mockup hashes and contract. Do not substitute a successful web or native build for rendered inspection on the relevant host.

**Gate D:** Full inventory coverage; unified contract; reviewed, actor-labelled design approval.

## 4. Produce: implement and review

Integrate a vertical slice first: theme registry/adapter → shared primitives → one real page and its edge states. Verify the approach before distributing all page families. Preserve current behaviour, application state, validation, navigation, offline paths and API contracts.

Then dispatch bounded coding tasks in parallel. Freeze shared files or assign a single owner. Workers report exact changed files, checks run, screenshots/evidence, known gaps and deviations. The integrator reviews and incorporates changes sequentially; resolve conflicts intentionally. Do not equate each worker's green tests with an integrated pass.

Use the existing host's theme system where possible. Implement a settings interface that lists valid installed modules, shows a local preview, selects a theme, restores a known-good default and supports applicable preferences. The application adapter loads only prevalidated local assets; it never executes arbitrary hooks supplied by a theme. Selection should preserve route, forms, data and business state. Distinguish a device/global default from an individual user's preference.

Render the real application against approved mockups, including long data, narrow widths and relevant failure states. Run existing project gates plus the checks in `quality-gates.md`. An independent reviewer checks implementation, usability, accessibility, offline behaviour and performance. Fix defects, then rerun only affected checks plus required integration gates. Record genuine untestable requirements as blocked.

**Gate I:** Current implementation is reviewed; required project and UI checks pass with evidence; no unresolved critical or major regressions.

## 5. Finalize

Read `theme-module.md` and `run-records.md`. Ensure the theme package and evidence refer to the current files, not earlier mockups. Update version, attribution/license, usage guide, design decisions, compatibility, coverage, measurement conditions, changelog and rollback.

Use the declared host adapter's build, theme validation and platform gates. The supplied build/theme/register/package commands validate web modules only; a native module needs explicit native tooling and any required contract extension before full Studio acceptance. Finish or park workers that depend on temporary model routing, run `models-restore` when assignments were applied, record restoration and refresh the routing digest. For the supported web pipeline, run the helper's theme and run checks, complete finalization approval against the returned review digest, then register and package the theme. The first successful Studio theme becomes the default; later new themes stay selectable unless default replacement was selected. The registry is metadata: verify that the real application adapter consumes it and that changing/defaulting a theme actually works in the app.

Retain the prior theme and registry so rollback is a pointer/version restoration, not a destructive rewrite. Validate rollback in development. Do not erase run history. Commit/push/merge/deploy only within the project's established authorization; yolo design does not change it. Finish any authorized release steps, and distinguish missing external release authorization from a UI implementation failure.

**Gate F:** Theme package, documentation, coverage, independent reviews and current-byte evidence are complete; default lifecycle and rollback verified.

## 6. Resume and scope changes

On `resume`, find the latest relevant run and read its project context, model-routing record, brief, decisions, coverage, blockers and evidence. Recheck the current project instructions and changed source requirements; verify file hashes/source revision before trusting prior approvals. Preserve recorded mode, theme choice and model policy unless the user explicitly changes them. For `current-model`, recapture the active session model as directed by `model-routing.md`; never silently retain a different old worker model. Document an explicit model-policy change and verify the new resolved assignments before new work. Continue the earliest unmet dependency; do not restart the interview or discard selected designs.

If an approved token, component, content model or route changes, record the change, invalidate affected downstream approvals, regenerate relevant mockups and recheck affected cases. In guided mode ask only if it changes an accepted design decision materially. In yolo, reappraise and record a new agent decision. A small verified bug fix does not require a fresh concept competition.

## 7. Continue a legacy 1.0 run

The new helper can read/check schema 1.0 dossiers but its context and model-routing operations require schema 1.1. An update does not rewrite historical records. A completed legacy run remains a completed historical artifact; further requested changes follow the normal new/modify theme lifecycle.

For incomplete legacy work, the director performs a linked continuation without asking the user to rewrite JSON:

1. Read the old run, actual source revision, theme registry, artifacts, decisions and unresolved checks. Record the old run's project-relative path and the SHA-256 of its original `run.json` in the continuation's context and brief. Leave the old directory and its accepted history intact.
2. Use `init-run` to create a new schema 1.1 dossier with the intended mode, selected model policy and the same theme ID/action when still valid against the current registry. Reuse an existing theme scaffold; do not call `theme-new` over it. If the registry changed materially, resolve the real theme action using the normal lifecycle instead of pretending the old action remains valid.
3. Copy only useful, safe artifacts into the new dossier with confined relative paths; do not follow symlinks or copy unrelated application secrets. Retain a provenance map. Reconcile coverage against current source. Do not copy the old `run.json` over the new record or label the continuation finalized.
4. Re-read current project requirements and resolve the new project-context record. Carry forward a legacy required offline gate, including a schema 1.0 TADA run's offline requirement. An upgrade is not a waiver; a genuinely different scope must be recorded as new work, not disguised as a continuation.
5. Preserve authentic prior Plan/Design selections as provenance. Reuse an approval only after verifying its actual actor, original decision, current scope and identical approved inputs; never invent a new human approval. Re-review changed inputs under the current guided/yolo policy, asking only for material user choices. Never import final acceptance into the new dossier.
6. Discover/apply/observe current model routing using the new record. Revalidate copied evidence against the current implementation, refresh hashes and mark stale or unavailable checks pending. Copying a passed file is not a fresh application test.
7. Record `Continues: <old-run-path>` and the next unmet dependency in the project tracker. Continue from that point. The new dossier alone receives the new routing operations and eventual finalization; the old record remains available for audit.

This is a documented director workflow, not an automatic JSON migration command. If any step cannot be performed safely with the available tools, preserve both records and name the exact blocker while completing independent work.
