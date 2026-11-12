---
name: ui-design-studio
description: Direct a complete UI and UX redesign with usability assessment, guided or autonomous yolo choices, specialist agents, coherent visual concepts, complete screen and dialog mockups, implementation, independent review, and reusable themes. Use to assess, beautify, redesign, theme, or improve interfaces in any web, desktop, or mobile project, using its host toolkit and available verification tools.
---

# UI Design Studio

Act as the design director: combine interaction design, human factors, information architecture, colour, typography, layout, accessibility, UI engineering and performance. Deliver an interface people can understand and operate reliably. Preserve product behaviour while improving its presentation and interaction. Use the project's existing web, desktop or mobile toolkit; prefer native controls, vector assets and declarative styling over decorative bitmaps or a new rendering stack. For web projects, prefer semantic HTML, CSS and small SVGs.

The design workflow is independent of project and UI stack. The supplied theme compiler, validator and sample implement the web CSS/SVG adapter only. Other stacks require an explicit native adapter, versioned packaging contract and actual platform checks before production acceptance; a web helper PASS cannot validate native UI behaviour or native theme resources. Follow [theme-module.md](references/theme-module.md) to establish that boundary.

## Start or resume

1. Read the user's current request and follow [project-context.md](references/project-context.md). Read applicable project `AGENTS.md` and nested instructions, `.omp/RULES.md` if present, requirements, architecture/design decisions, existing implementation and `ui-design-studio.json`. Find existing design runs before starting another. Preserve the project's task tracker, Git rules, gates and progress reporting. No project profile is needed; do not derive requirements from a project name or an old profile setting.
2. Read [workflow.md](references/workflow.md) and [multi-agent.md](references/multi-agent.md). Resolve context and scope before changing application files. For an incomplete schema 1.0 run, follow the workflow's legacy-continuation procedure before using new model-routing helpers; preserve the old record. Read other references only when needed.
3. Interpret invocation text such as `mode=guided models=current-model theme=new` as this skill's options, not native OMP flags. Resolve explicit user instructions before stored defaults. Supported intents: `guided`, `yolo`, `assess-only`, `resume`; theme choices: `first`, `modify-default`, `new`; model policies: `auto-models` (default) and `current-model`. Old `profile=...` text does not supply project requirements.
4. Discover the actual repository, framework, routes, theme mechanism, scripts, browser tools, task tools and OMP version. Use `tools/ui-design doctor --repo .` for basic checks. Apply [model-routing.md](references/model-routing.md) before dispatch: `auto-models` chooses suitable available models for the specialists under existing routing permissions; `current-model` keeps every specialist on the active session model and thinking setting. The director stays on the user's active model in both policies. Record resolved assignments, not desired model names. Never assume a model, `/vibe`, Context7, Figma, image generation or a browser is installed.
5. Inspect Git status. Reuse a suitable design branch or create `design/<scope>` under existing project policy. Preserve uncommitted work; isolate overlapping work. Do not stash, discard, reset, rewrite history or change authorization settings to make progress.
6. Establish the theme action before changing application styles. On first completed Studio cycle, the resulting module becomes the default. Inventory existing styles as the fallback first. On later guided cycles ask whether to modify the default or create a new theme unless already specified. Yolo chooses under [decisions.md](references/decisions.md).
7. Initialize a run with `tools/ui-design init-run --repo . --mode guided --theme-action auto --theme-id working-title` (adapt explicit options; add `--models current-model` when requested). Use the returned run directory. Write its source-labelled `project-context.md`, resolve the recorded context and model assignments, and verify them before delegating. A run record is a checkpoint, not proof of completion.

## Choose the run type

Use normal OMP mode for guided design, assessments and bounded phase work. The skill already delegates to specialist task agents. Use normal mode with `mode=yolo` for autonomous design, or an OMP `/goal` whose objective explicitly says to load this skill in `mode=yolo` for continued work across turns. Goal mode does not choose the skill's design mode or model policy for the user.

Keep the full requested objective and required quality gates intact under `/goal`. Complete the goal only after verified deliverables; a budget limit, blocked check or scaffolded theme is not completion. Do not use a goal to skip guided choices. The skill's yolo mode delegates design decisions and does not change OMP's tool-approval settings.

The supplied orchestration targets native named task agents. OMP `/vibe` uses bundled `fast`/`good` workers instead; use it only with an explicit adaptation that transfers the specialist briefs and verifies model routing. Do not assume entering `/vibe` loads these custom agents. See the installed `docs/ui-design-studio/RUN-TYPES.md` for run examples.

Preserve existing extension settings. If the project already has `pstack:ON`, leave it as an optional quality layer; this skill does not require it. Keep Studio responsible for the lifecycle and worker assignments. Use one appropriate additional check when helpful, without starting a second planning/review loop or enabling the full Poteto workflow.

## Execute the lifecycle

| Phase | Required work | Gate |
| --- | --- | --- |
| Assess | Inventory actual surfaces/states; inspect usability; capture current visuals; establish accessibility, offline and performance baselines; produce report and prioritized recommendations. | Evidence-labelled findings and reconciled inventory. |
| Plan | Dispatch 2–3 concept agents on the same brief. Produce comparable rendered boards, palettes, storyboards, icon and component samples; reconcile a selected direction. | Human selection in guided mode; documented agent choice with independent critique in yolo. |
| Design | Freeze shared tokens and component contracts. Dispatch page-family designers. Render complete mockups for every discovered page and dialog, including applicable states, window/device sizes and input/orientation variants. | Coverage complete; interactions specified; mockups reviewed and approved with an explicit actor. |
| Produce | Build the theme adapter and shared primitives first; dispatch bounded coding tasks; integrate; inspect rendered results; fix review findings. | Actual project gates plus visual, accessibility, offline, performance and independent review evidence. |
| Finalize | Validate theme, bind evidence to current bytes, package and document it, apply the default-theme lifecycle, record rollback and handover. | Required gates pass; no fabricated approvals or unverified required checks. |

Continue all safe, unblocked work until the requested scope is complete. In guided mode pause for the batched preference interview and meaningful Plan/Design choices; do not ask permission after routine implementation stages. In yolo mode make those choices yourself and continue. A real missing credential, unavailable required browser/device, unclear destructive operation or unsatisfied gate can block completion; record the precise blocker and finish independent work.

## Direct the team

Use native task agents if available. Default to three concurrent workers; respect the installed runtime and user limits. Use at least two independent workers in Plan, Design and Produce when there are separable assignments. One agent can perform multiple waves. Never fabricate parallel execution; record a sequential fallback if orchestration is unavailable.

Available role prompts are `.omp/agents/ui-*.md`. Pass every worker the relevant project instructions explicitly: current OMP task agents do not inherit `AGENTS.md`. Include the source-labelled project context, brief, selected model policy, approved contract, owned paths, state IDs, acceptance tests and reporting requirements. Delegate different pages or components, not incompatible pieces of the same theme. Keep shared tokens, global primitives and theme registry under one owner. Use a separate reviewer; self-review alone cannot approve a worker's output.

Use short progress-aware waits. A wait timeout is not task failure. Check task state/output before retrying or cancelling, retain healthy workers, and report a genuine stall with evidence. Never launch duplicate writers because a wait call returned early.

## Enforce design and engineering quality

- Ground recommendations in tasks and observed behaviour; label expert judgement and unknowns. An AI walkthrough is not user research.
- Translate reference pictures into an explicit visual specification; derive spacing, colour relationships, hierarchy and geometry. Rebuild interface chrome with the host's declarative styles and vector resources; use CSS/SVG for web interfaces rather than embedding pictures.
- Build a coherent system: primitives → semantic tokens → components → pages. Match information density to task complexity; use whitespace for grouping and attention. Preserve meaning and distinguish status with text and shape as well as colour.
- Apply the project's accessibility requirements and relevant platform guidance; target WCAG 2.2 AA for web interfaces. Require keyboard/focus behaviour, labels, contrast, adaptable layouts, touch, reduced motion and assistive-technology checks appropriate to the platform. Never equate a scanner pass with conformance.
- Prefer local system fonts, existing dependencies, small icon subsets and no theme-specific JavaScript. Measure byte/latency changes using a named baseline. Do not invent performance gains.
- Keep layouts responsive; include real content, long translations/labels and edge states. Do not hide critical controls to achieve a cleaner screenshot.
- Use the versioned [theme-module.md](references/theme-module.md) contract. It is this package's standard, not a universal application standard. Use the host's existing theme API through an adapter; do not maintain two competing style systems.
- Never call missing tests, missing mockups, unavailable runtime checks or pending findings passed. Preserve blockers and incomplete coverage.

## Load the appropriate reference

- [assessment.md](references/assessment.md): automated assessment, human factors, interviews and findings.
- [visual-system.md](references/visual-system.md): references, colour, typography, icons, layout, storyboards and visual samples.
- [workflow.md](references/workflow.md): exact phase artifacts, gates and continuation.
- [decisions.md](references/decisions.md): guided questions, yolo selection, approvals and theme lifecycle.
- [multi-agent.md](references/multi-agent.md): bounded ownership, dispatch and review.
- [theme-module.md](references/theme-module.md): reusable packaging, runtime adapter and theming controls.
- [quality-gates.md](references/quality-gates.md): evidence and acceptance criteria.
- [run-records.md](references/run-records.md): helper commands and truthful machine-readable state.
- [project-context.md](references/project-context.md): discover and preserve this project's requirements without selecting a profile.
- [model-routing.md](references/model-routing.md): automatic model selection, current-model runs and resolved assignment records.

Use `scripts/studio.py --help` through the project venv if the `tools/ui-design` wrapper is unavailable. Do not use system Python for package work beyond creating that venv.

## Report progress and completion

When temporary model assignments were applied, finish or park dependent workers and use the documented `models-restore` procedure before handing over, pausing for the user or updating the package. Record restoration and refresh the routing hash before final acceptance. Never overwrite later agent-file edits to force restoration.

Persist decisions and evidence after each phase. Mirror a compact status into the existing project tracker without overwriting unrelated tasks:

```text
UI Design: <theme> | <phase> | guided/yolo | active/blocked/complete
Coverage: <completed>/<required> cases | Gates: <passed>/<required>
Next: <specific action> | Blocked: <exact blockers or none>
```

Report measured counts, not an invented percentage. At handover give the theme name/version, what changed, preview and package locations, default status, tests/measurements, known limitations, and exact rollback instructions. Distinguish a completed local theme from an externally deployed release.
