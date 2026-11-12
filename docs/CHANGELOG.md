# Release notes

## 1.1.0 — 12 November 2026

### Project context replaces profile selection

- Run and installation examples no longer require a `profile` argument.
- New runs derive requirements from the project's instructions, specifications, architecture decisions, design system and implementation.
- A source-labelled `project-context.md` records the discovered constraints. New run acceptance requires resolved context, a declared offline requirement and a current context hash.
- Predefined TADA/generic policy selection is retired from new runs. Older installer/helper profile arguments are compatibility inputs with a deprecation notice; they no longer determine the project's requirements.

### Explicit model policy

- `auto-models` is the new default worker policy. The director remains the active OMP session; specialist assignments are selected from eligible configured models and verified.
- `current-model` keeps the active provider/model and reasoning selection across the specialist team.
- Run instructions can select `models=auto-models` or `models=current-model`; project policy uses `modelPolicy`.
- New dossiers record the actual routing, session snapshot and role assignments. Routing evidence participates in final acceptance.
- Added journaled `models-apply` / `models-restore` helpers for temporary project-local worker assignments. Conflicting operator overrides and later edits are detected; the director checks live execution before resolving the record.
- Provider credentials, account setup and operator permission controls remain external to the package.

### Complete run documentation

- Added a complete run guide covering guided design, normal YOLO, `/goal` with YOLO, assessments, design-only handoffs, reference inputs, limited scope, default/new themes, resume, model changes, review and finalization.
- Added installation/configuration/update/restore guidance and troubleshooting.
- Added direct-reading starter and recovery prompts, including goal-managed YOLO and continuation.
- Clarified the difference between design phases and OMP session modes, and documented optional existing Tersio pstack usage.
- Reworked the distribution for reuse across projects. The included executable theme implementation remains CSS/SVG for compatible web interfaces; native UI stacks require a deliberate adapter and verification.

### Upgrade behaviour

- Existing project policy files remain untouched; missing `modelPolicy` defaults to `auto-models` for new runs. An old `profile` key does not need a manual cleanup before using the new workflow.
- New `run.json` records use schema version `1.1`. Coverage and decision formats, project configuration format and the web theme-module schema retain their existing versions.
- Existing version 1.0 run records remain readable and completed dossiers remain immutable. Incomplete legacy work needing 1.1 features uses a director-managed linked continuation with preserved provenance, current context/routing and revalidated evidence; final acceptance is not imported. Legacy TADA continuations retain the offline evidence requirement.
- Updates safely retire no-longer-shipped managed files with conflict checks and restore history.
- Installed documentation links are adjusted for the installed documentation location.

See [Installation](INSTALLATION.md) for the upgrade procedure and [Validation](VALIDATION.md) for the checks actually performed. Updating the skills does not itself verify or change the application.

## 1.0.0 — 12 November 2026

Initial release of the design director, nine skills, seven specialist agents, guided/YOLO decision workflow, transactional project-local installer, theme compiler/validator, run evidence checks and Fieldstone web theme specimen. The initial release used named project profiles and inherited existing OMP model routing without an explicit Studio model policy.
