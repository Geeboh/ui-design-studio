# Release notes

## 1.4.1 · 14 November 2026

- Hardened evidence, status, coverage, resume, worker-packet, and host-feasibility validation.
- Added deterministic remediation benchmarks, compatibility records, and release handoff documentation.
- Added regression coverage for evidence-input binding, model-field normalization, bounded status output, and package integrity.
- Included three existing redacted synthetic dashboard screenshots as v1.4.1 visual references.

## 1.4.0 · 13 November 2026

- Added optional `install.sh --mcp-global` installation into one isolated user environment shared by all projects.
- Added `ui-design dashboard-serve` with verified local/LAN addresses, a locally generated QR, and foreground or parent-stdio cleanup.
- Made the OMP extension start and supervise a dashboard automatically, recover unexpected child exits, and expose explicit start/stop commands.
- Preserved authentication fragments, private discovery, explicit run-director ownership, and read-only `dashboard-info`.
- Isolated global pip installation from inherited destination configuration and preserved unrelated user executables during upgrades.
- Required authenticated identity verification before discovery output and preserved selected runs across recovery and cancelled session switches.
- Added [setup, recovery, and release limits](RELEASE-v1.4.0.md), backed by 91 Python tests, 49 Node tests, and actual Linux global-runtime and OMP lifecycle checks.
- Added shared evidence dependency validation, revision-bound compact/paged MCP status, explicit scoped completion, applicability-aware coverage, dependency-aware resume manifests, selected-role worker packets, early host-feasibility guidance, conditional offline review policy and deterministic offline benchmark evidence.

## 1.3.0 · 12 November 2026

### Portable local MCP adapter

- Added the installable `ui-design-studio-mcp` 1.3.0 Python package with local stdio tools, workflow prompts, and allowlisted guide resources.
- Added a per-connection authenticated waiting dashboard, identity-verified run reuse, and ownership-aware cleanup without creating a run during connection.
- Added validated loopback and LAN aliases, private connection discovery, and `ui-design dashboard-info` with locally generated terminal QR output.
- Extended the existing OMP progress widget with waiting-session details and `/ui-design-dashboard` while retaining explicit run-director ownership.
- Kept the OMP installer standard-library-only and separate from MCP configuration and package installation.
- Set the MCP initialization identity to the package version instead of the SDK's default version.
- Added [screenshots and runnable examples](RELEASE-v1.3.0.md) for connection setup, verified addresses, and retained artwork previews.

## 1.2.0 · 12 November 2026

### Live development progress and Design Server

- Added a native below-editor OMP status widget with actual progress bars, gate and coverage counts, next action, blockers and the complete server address. Pi Tasks keeps its own widget.
- Added a regular console status fallback and a standard-library Design Server with live workers, tasks, progress graphs and statistics.
- Added automatic artwork discovery, explicit contextual publication, immutable version browsing, clickable thumbnails and sandboxed full-size mockup previews.
- Added guided artistic requests and digest-bound user decisions without human approval waits in yolo mode.
- Added authenticated owned-server cleanup, all-run cleanup and automatic cleanup after successful yolo acceptance. Original design evidence and the artwork library remain intact.
- Documented private access URLs, trusted-LAN limits, worker publication and the cleanup lifecycle.

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
