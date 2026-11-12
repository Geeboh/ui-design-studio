# Run types and practical recipes

**UI Design Studio 1.1.0**

Run the commands below in an OMP session whose working directory is the target project root. The package must already be installed in that project. For installation and troubleshooting, see [Installation](INSTALLATION.md).

No command needs `profile=`. Every new run begins by reading the project's instructions and requirements. The designer uses the same workflow in different projects and records the applicable context instead of selecting a predefined project identity.

## Contents

1. Choose the run and model policy
2. Guided complete redesign
3. Autonomous YOLO in normal mode
4. Autonomous `/goal` run with YOLO
5. Assessment only
6. Concepts and mockups without implementation
7. Use reference pictures or a visual brief
8. Improve a limited area
9. Modify the default theme
10. Create a new theme or variant
11. Continue interrupted work
12. Change decision mode or model policy mid-run
13. Review or finish existing work
14. Use the package in another project
15. OMP modes, pstack and optional tooling
16. Understand outputs, approvals and completion

## 1. Choose the run and model policy

### Run selection

| Intent | OMP session mode | Studio instruction | Stops for design choices? |
| --- | --- | --- | --- |
| Choose the visual direction yourself | Normal | `mode=guided` | Yes: meaningful preferences, concept choice and mockup approval |
| Delegate design choices | Normal | `mode=yolo` | No aesthetic checkpoints |
| Sustain an autonomous full redesign | `/goal` | `mode=yolo` in the goal objective | No aesthetic checkpoints |
| Audit only | Normal | `ui-assess` or `assess-only` | Only a material missing input |
| Explore/mock up only | Normal | Guided or YOLO with a written stop after Design | According to chosen decision mode |
| Resume a dossier | Normal or its existing goal | `resume` | Retains the recorded mode |

Normal OMP mode already supports the package's specialist task agents. `/vibe` is not required to get multiple agents. The package's Plan phase is a design activity that writes visual artifacts; it is separate from OMP's native read-only plan mode.

### Model selection

| Option | Meaning |
| --- | --- |
| `models=auto-models` | Default. Keep your active session as director; choose suitable specialist worker models from the eligible configured models and record the actual assignments. |
| `models=current-model` | Keep the active provider/model and reasoning selection for the director and all seven specialist roles. |

You can omit `models=auto-models` unless you want to override a project default of `current-model`. The `modelPolicy` key in `ui-design-studio.json` sets that project's default. The explicit run option takes precedence; resume otherwise keeps the run's recorded policy.

Auto-models does not activate new providers or create credentials. It considers task difficulty, visual capabilities, quality, available cost/latency information and existing operator constraints. A suitable active-model fallback is recorded when another choice is unavailable. It does not silently change the main session's selected model.

Current-model snapshots the active model and reasoning setting when routing is resolved. Existing per-agent overrides must be reconciled through supported routing before claiming the workers use it. If the runtime cannot honour the choice, the director reports the conflict. Changing the main model later does not silently rewrite an already-recorded worker policy; explicitly request a routing refresh.

The director manages `models-apply` and `models-restore` for the run. These temporarily route only the seven project-local UI agent definitions, preserving their original bytes and refusing conflicting operator overrides. Existing global settings and the main model remain unchanged. The director restores routing before handover or a deliberate pause and reapplies it on resume when needed. You do not need to hand-edit seven agent files.

The run records `model-routing.md`, the chosen policy, the session snapshot and each specialist's actual model/reasoning assignment. A full release requires resolved, current routing evidence. The internal record format and procedure are documented in `.omp/skills/ui-design-studio/references/model-routing.md`.

## 2. Guided complete redesign

**Use when:** you want to inspect alternatives and choose the final direction.

```text
/skill:ui-design-studio mode=guided
```

With the active model throughout:

```text
/skill:ui-design-studio mode=guided models=current-model
```

Expected flow:

1. Read project instructions, requirements, implementation and prior design runs. Capture the current state and assess the interface.
2. Present the usability report and ask a compact set of unanswered design questions.
3. Produce comparable concept boards with palettes, typography, components, icons and storyboards. Present a recommendation and ask for your selection.
4. Build complete mockups for every required page/dialog/state and present an index for your approval.
5. Implement, independently review, fix, verify, package and document the approved result.

You can give precise feedback such as “Use concept B's layout, concept A's colour relationships, and reduce card density.” The director reconciles that request into one shared system before splitting page work across agents.

**Output:** assessment, selected design contract, complete mockups, implemented theme, evidence and handover. Ordinary implementation stages do not need repeated “continue?” approvals.

## 3. Autonomous YOLO in normal mode

**Use when:** you delegate visual choices and want the complete workflow without concept/mockup checkpoints.

```text
/skill:ui-design-studio mode=yolo
```

Equivalent convenience command:

```text
/ui-yolo
```

Current-model variant:

```text
/skill:ui-design-studio mode=yolo models=current-model
```

The director assesses the actual project, compares coherent concepts, requests independent critique, chooses and records a direction, verifies the complete mockups, selects an appropriate theme name, implements the result and performs the release checks.

Aesthetic approvals are attributed to the agent. Required evidence, project constraints and known failures still control acceptance. Genuine missing access or required unavailable testing can block completion; the director finishes independent work and states what remains.

**Output:** the same full deliverables as guided mode, with documented autonomous decisions. Normal mode is sufficient when you do not need an additional goal-continuation mechanism.

## 4. Autonomous `/goal` run with YOLO

**Use when:** the redesign is substantial and you want OMP to maintain the objective across turns while the skill handles design decisions.

OMP's goal capability must be available/enabled in your installation. Start in normal mode with no conflicting active or paused plan/vibe mode. Keep an existing relevant goal if it already owns this redesign; resume it instead of creating a competing objective.

### Start from a running OMP session

Paste this as one message:

```text
/goal Read .omp/skills/ui-design-studio/SKILL.md and use the installed UI Design Studio workflow for this project with mode=yolo and models=auto-models. Discover and follow the project's existing instructions, requirements and design system; do not require a profile. Complete Assess, Plan, Design, Produce and Finalize for the complete existing UI, including every discovered page, dialog and applicable state. Use specialist task agents with bounded ownership and independent reviewers. Compare coherent concepts, make and record aesthetic choices, verify complete mockups, choose an appropriate theme name, implement the selected design, and package and document the result. Follow the default-theme lifecycle and existing project Git/release policy. Preserve decisions, coverage, evidence, actual model assignments and blockers so the run can resume. Mark the goal complete only when all required deliverables and checks for the full agreed scope are verified. Resolve ordinary choices autonomously; report a precise genuine blocker when required work cannot be completed.
```

For current-model operation, replace only `models=auto-models` with `models=current-model`.

This is an OMP goal objective that instructs the agent to read the skill. Do not nest another slash command such as `/skill:...` inside `/goal` and expect a second command to be executed automatically.

### What the two settings control

| Setting | Responsibility |
| --- | --- |
| OMP `/goal` | Maintains the task objective and continuation/completion lifecycle |
| Studio `mode=yolo` | Delegates preferences, concept selection, mockup approval and naming to the director |
| Studio `models=...` | Chooses the worker model policy; the director remains the active session model |

The skill's YOLO option does not require OMP's `--yolo` approval flag. Keep the project's existing tool permissions. A budget limit, interruption or failed required test is not verified completion.

### Optional new-session launch

For an OMP version supporting the documented `--goal` launch flag, a fresh interactive session can begin directly:

```bash
cd /absolute/path/to/project
omp --goal "Read .omp/skills/ui-design-studio/SKILL.md. Run mode=yolo models=auto-models for the complete project UI through verified finalization. Discover existing requirements, use specialist agents and independent reviews, preserve evidence and follow the default-theme lifecycle."
```

Use this only when you want a new session. It is unnecessary when OMP is already running. Do not substitute `omp '/goal ...'`: a positional string is not a reliable way to activate a native session mode. Installed-version restrictions for `--goal`, budget controls and resumption are in the upstream [CLI reference](https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md).

### Interrupt, resume and finish

Use OMP's existing goal controls to inspect or pause the objective. When the goal is paused and you are ready to continue, current upstream OMP supports:

```text
/goal resume
```

If the original goal no longer exists, use a new goal whose objective explicitly **resumes the existing Studio dossier**; see section 11. Do not rerun the initial concept competition merely because the OMP process restarted.

**Output:** the complete design deliverables and a verified goal completion. The director must leave incomplete work visibly incomplete, with the exact gate or access issue recorded.

## 5. Assessment only

**Use when:** you want an audit and recommendations before authorizing design or implementation.

```text
/skill:ui-assess
```

Or, through the director:

```text
/skill:ui-design-studio assess-only
```

An explicitly bounded assessment:

```text
/skill:ui-assess Assess the administrative setup and onboarding flows. Read the existing requirements, inspect every relevant page/dialog/state, and produce a usability report with evidence, priorities, confidence, recommendations and implementation considerations. Stop after the report. Do not change application UI code.
```

The skill may write its report, inventory and measurement artifacts. “Assessment only” does not mean nothing is saved; it means the application is not redesigned or modified as part of the assessment.

**Output:** source-backed project context, inventory, findings, recommendations and baseline. Missing runtime observations are labelled. A completed assessment is not a finalized theme release, and its dossier must not claim later phases passed.

## 6. Concepts and mockups without implementation

**Use when:** you want material to evaluate or hand to another implementation team.

```text
/skill:ui-design-studio mode=guided Scope: the complete existing interface. Perform Assess, Plan and Design. Present comparable visual concepts, then full page/dialog mockups and the interaction specification. Stop after Design approval and package the design artifacts as a draft handoff. Do not implement application changes or register a default theme in this run.
```

For autonomous concept selection, change `mode=guided` to `mode=yolo`; retain the explicit stopping boundary.

The written scope is authoritative. `stop after Design` is a plain-language boundary, not an invented native CLI flag. Mockups still require complete agreed coverage and actual rendering where claimed.

**Output:** assessment, concepts, chosen direction, token/component specification and mockups. Label the handoff “design only” or “draft”; no production release or changed default is implied.

## 7. Use reference pictures or a visual brief

Attach images through your OMP environment, or supply project-local paths that the agent can read. State which properties matter when you know them:

```text
/skill:ui-design-studio mode=guided Use the attached reference images as visual direction. Carry over the restrained palette, spacious grouping and compact navigation. Preserve the project's existing tasks and requirements. Derive a coherent token/component system and rebuild interface presentation with the target stack's code-native styling and vector assets where appropriate. Assess fit and accessibility before presenting concepts.
```

A written brief also works:

```text
/skill:ui-design-studio mode=yolo Create a calm, practical interface for frequent use in poor lighting. Keep critical status obvious, use whitespace to group tasks, and prefer clear typography over decoration. Infer the detailed constraints from this project's requirements and verify them against the existing implementation.
```

The director extracts colour relationships, hierarchy, spacing, geometry, density and typography from the references. It must not embed a screenshot as the production interface or infer that a pictured decorative pattern is a product requirement.

If a reference cannot be viewed with available tools/models, it is recorded as unread rather than described from imagination. The run may continue independent discovery while resolving that gap.

## 8. Improve a limited area

**Use when:** the rest of the product should stay outside the current design scope.

```text
/skill:ui-design-studio mode=guided Scope: the settings pages and their dialogs only. Reuse the existing design language where it remains suitable. Assess the affected flows, show focused concepts and complete mockups, then implement and verify this scope. Record any shared-token changes and test their effects on other screens before accepting them.
```

Name actual routes, components or user tasks if possible. The director resolves the affected inventory from the codebase. A small scope does not excuse missing error, keyboard, narrow-screen or permission states within that area.

If an existing finalized theme is involved, specify `theme=modify-default` when that is your intention. The package's first/new/default rules still apply when a run creates and finalizes a Studio theme; a one-dialog request is not permission to silently retheme unrelated pages.

## 9. Modify the default theme

**Use when:** you want to evolve the existing default rather than add another selectable theme.

```text
/skill:ui-design-studio mode=guided theme=modify-default
```

Autonomous variant:

```text
/skill:ui-design-studio mode=yolo theme=modify-default models=current-model
```

The director checks that a default exists, preserves its stable ID, scopes the changes, updates its version when content changes, and retains previous module/registry evidence for rollback. It respects any individual user theme preferences.

If no Studio default exists, the director inventories the application's current styling and establishes the first-theme path. It must not invent a default theme record solely to satisfy the requested operation.

## 10. Create a new theme or variant

**Use when:** you want an additional style without replacing the existing default.

```text
/skill:ui-design-studio mode=guided theme=new
```

An autonomous variant with a clear brief:

```text
/skill:ui-design-studio mode=yolo theme=new Create an additional high-contrast theme consistent with the existing component system. Keep the current default and existing user preferences. Verify the relevant contrast, focus, state and responsive behaviour, then package and document the new selectable module.
```

On a later run, a new module normally leaves the current default unchanged. If you also want it to become the default, say that explicitly in the same request. The first successfully finalized Studio theme becomes the default under the package lifecycle.

Dark/light modes, density and motion are separate concerns. The included light-palette specimen does not automatically supply another mode. Each new variant needs its own declared token coverage, implementation and verification.

## 11. Continue interrupted work

### Resume in normal OMP mode

```text
/skill:ui-design-studio resume
```

If more than one run is relevant, identify the actual run directory or theme:

```text
/skill:ui-design-studio resume Resume the existing run at docs/design/runs/ACTUAL_RUN_ID. Preserve its scope, decision mode, model policy, approved direction and theme action. Check current files and evidence, then continue from the next unmet dependency.
```

Replace `ACTUAL_RUN_ID` with the real directory. Do not type that placeholder literally. The director checks for meaningful changes, refreshes stale evidence and retains valid decisions. It does not restart the interview because the conversation was compacted.

### Continue a version 1.0 dossier after upgrading

A completed 1.0 dossier remains readable and immutable. For an incomplete 1.0 dossier that needs the current workflow, the director performs a linked continuation automatically:

1. Preserve the original dossier and record its path and digest in a new 1.1 run created with `init-run`. Keep the existing theme ID/action when valid against the current registry, and reuse its scaffold without overwriting it.
2. Copy only useful, safe artifacts; reconcile the current surface/state coverage. Re-read current requirements and resolve the new model policy/routing. The new model helpers apply only to this continuation.
3. Preserve authentic, still-valid Plan/Design choices as provenance. Verify their actual inputs; do not manufacture user approval. Revisit a choice only when materially changed inputs require it.
4. Revalidate current evidence and obtain fresh final acceptance. Never import a prior final-acceptance result as the new run's completion.

A continuation of a legacy TADA run retains its required offline evidence. A genuinely separate, re-scoped project request must be identified as new work, not used to weaken that requirement while claiming a resume.

The ordinary resume command and included direct-reading resume prompts instruct the director to handle this procedure. You do not hand-edit `schemaVersion` or run a migration utility. If the legacy dossier has no model policy, the explicit current instruction or project default determines the continuation's policy; its earlier model history is preserved as known or unknown.

### Resume an existing paused goal

If the correct goal remains recorded in the OMP session:

```text
/goal resume
```

Check its objective before resuming if the session has served several projects. The Studio dossier and OMP goal are separate records: one tracks the design evidence; the other tracks the session objective.

### Recover the goal wrapper around an existing dossier

If the goal is gone but the project files remain, use:

```text
/goal Read .omp/skills/ui-design-studio/SKILL.md and resume the latest relevant incomplete UI Design Studio run in this project. Preserve its recorded scope, decision mode, model policy, theme action and valid approvals. Re-read current project requirements, verify context and evidence freshness, and continue through the remaining required work. Create a linked 1.1 continuation only when an incomplete legacy 1.0 dossier needs it; preserve its original record and required constraints. Do not create an unrelated duplicate run or repeat approved concept selection without a material change. Mark this goal complete only after the run's full agreed deliverables are verified.
```

If the existing dossier is guided and you now want autonomous choices, explicitly add: “Change this run to `mode=yolo`; record that I am delegating the remaining aesthetic decisions.” Otherwise the original guided checkpoints remain meaningful.

## 12. Change decision mode or model policy mid-run

A clear user instruction can change future decisions without rewriting the past:

```text
Continue the current UI Design Studio run in mode=yolo. I delegate the remaining concept/mockup/name choices to you. Preserve already approved decisions and the agreed scope, and record the mode change.
```

To change model policy:

```text
Continue this run with models=current-model. Resolve the current session's provider/model and reasoning setting, apply that selection to subsequent specialist work using the supported routing procedure, verify it, and record the change. Preserve completed work and its actual model history.
```

A reverse change to `models=auto-models` follows the same principle. Record the updated policy and actual assignments; earlier work keeps its original provenance. Do not claim existing workers changed model merely because a configuration value changed. Reused/active workers need runtime verification or a new bounded assignment when necessary.

## 13. Review or finish existing work

A review is useful when another team or an earlier run has already implemented changes:

```text
/skill:ui-review Review the existing UI changes against the project's requirements, approved design artifacts and current coverage. Inspect the rendered application, interaction/accessibility behaviour and measured performance where available. Report concrete findings and evidence. Do not approve unverified checks or treat the implementer's report as independent review.
```

To finalize an already verified run:

```text
/skill:ui-finalize Resume the current design dossier. Verify the final theme bytes, project context, actual model routing, decisions, coverage and required review/test evidence. Package, document and register the theme only when the required gates are satisfied. Record the resulting default state and rollback procedure.
```

A phase-specific skill does not waive earlier prerequisites. If the evidence is missing or stale, it reports exactly what must be completed rather than synthesizing successful records.

## 14. Use the package in another project

From the extracted release:

```bash
bash ./install.sh --project /absolute/path/to/another-project
```

Then invoke the same Studio command in that project's OMP session. No `generic` or TADA profile is selected. Each repository has its own instructions, configuration, runs, theme registry and installation history.

The director discovers the actual UI stack. For a browser application, it adapts the included CSS/SVG theme contract to the host's existing mechanisms. For a native application, the run must establish and verify an appropriate platform adapter. A shared process and portable tokens do not imply that a web theme archive can be loaded unchanged by every UI toolkit.

## 15. OMP modes, pstack and optional tooling

### Normal, goal and vibe modes

Use normal mode for guided work and phase-specific tasks. Use `/goal` when sustained autonomous completion is helpful. `/vibe` uses OMP's persistent bundled `fast`/`good` workers rather than directly selecting these named UI specialists, so it needs an explicit adaptation of their role briefs and routing. This package does not require that adaptation. Current upstream Vibe and active/paused plan/goal modes are mutually exclusive. See the upstream [Vibe reference](https://github.com/can1357/oh-my-pi/blob/main/docs/vibe-mode.md).

### The design Plan phase and native `/plan`

Studio's Plan phase creates and evaluates visual concepts. Native OMP plan mode restricts execution and is not a substitute for that phase. Leave native read-only planning when the requested work needs generated artifacts, implementation and verification. Do not equate OMP's `--plan-yolo` option with Studio's `mode=yolo`.

### Should pstack be on?

If your project already uses **Tersio pstack**, keep that established quality layer on. Let UI Design Studio own the design phases and their artifacts; use pstack for its additional rigor checks without launching a duplicate planning or review workflow. It is optional, not an installation dependency, and this package does not toggle it automatically.

For an installed Tersio version exposing its documented commands, `/pstack status` checks its state and `/pstack on` enables it. Submit them as separate OMP commands. `pstack` is an extension capability, not a universal OMP command: do not assume another tool with that name behaves identically. Source: [Tersio package documentation](https://www.npmjs.com/package/@krtclcdy/tersio).

### Other optional capabilities

Figma, image generation, browser automation and knowledge/documentation integrations can help when already available and relevant. Their availability should be discovered; no service is silently assumed or installed. Prefer code-native mockups, CSS/SVG/vector assets and the existing component system for production presentation.

## 16. Understand outputs, approvals and completion

A normal run stores its dossier at `docs/design/runs/<run-id>/`, unless configured otherwise. Its documents explain the project context, actual model routing, scope, observed findings, concepts, chosen design, coverage, approvals, implementation, review, measurements and blockers.

| Status/result | What it establishes |
| --- | --- |
| Assessment finished | The requested audit/report scope is complete |
| Plan selected | A named concept or reconciled direction was chosen by the recorded actor |
| Design approved | The actual complete mockup set was reviewed by the recorded actor |
| Theme package built | The module passed the invoked packaging checks; it may still be a draft |
| `check-run` passed | Required declared records are structurally complete and current |
| Full run finalized | Actual integration and required checks have also been performed and reviewed |
| Goal completed | The agreed objective was verified, not merely that a turn ended |

Guided Plan/Design approval must come from your actual instruction. YOLO choices use an explicit agent actor. Neither a label nor a hash creates evidence that a check occurred.

The final handover should make it easy to find the theme, preview, changed surfaces, usability report, test results, default selection, known limitations, customization steps and rollback. Where runtime evidence is unavailable, the output must state what remains unverified and avoid claiming a completed production redesign.
