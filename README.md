# UI Design Studio

**Version 1.2.0 · A portable UI design workflow for Oh My Pi**

Assess an interface, develop coherent visual directions, design its complete pages and dialogs, implement the selected system, and deliver a documented theme. UI Design Studio combines a design director, nine reusable skills, seven specialist agent roles, run records, and installation/theme utilities.

The designer learns the project from its own instructions, requirements, source code and existing design system. **No project profile is required.** Use the same package in different repositories without importing another project's assumptions.

**Start guided when you want to choose the visual direction. Start YOLO when you want the director to make those choices. Use OMP's `/goal` for sustained autonomous work.** Model selection defaults to `auto-models`; choose `current-model` to keep the session's active model across the design team.

## Documentation

| Read | What it covers |
| --- | --- |
| [Installation and maintenance](docs/INSTALLATION.md) | Requirements, installation, live-session discovery, configuration, upgrades, restore and troubleshooting |
| [Run types and copy/paste recipes](docs/RUN-TYPES.md) | Guided, YOLO, `/goal` with YOLO, assessment, mockups, references, themes, scoped work, resume and model choices |
| [Release notes](docs/CHANGELOG.md) | Changes in 1.2.0 and compatibility with existing installations |
| [Validation record](docs/VALIDATION.md) | Checks actually performed on this release and their limits |
| [Distribution and release maintenance](docs/DISTRIBUTION.md) | License, package contents, checksum verification and reproducible ZIP builds |
| [Primary sources](docs/SOURCES.md) | Upstream OMP behaviour, accessibility, tokens and performance references |

The installer places this documentation in `docs/ui-design-studio/` inside the target project. Reusable prompts are included in `prompts/` in the archive and `docs/ui-design-studio/prompts/` after installation.

## Quick start

From the extracted `ui-design-studio-v1.2.0` directory, install into the **actual project root**:

```bash
bash ./install.sh --project /absolute/path/to/project --dry-run
bash ./install.sh --project /absolute/path/to/project
cd /absolute/path/to/project
./tools/ui-design doctor --repo .
```

Replace `/absolute/path/to/project` with the repository you intend to redesign. The dry run is a preview of changes; the second command installs them. Package Python runs in a virtual environment and requires no third-party Python dependencies.

In OMP, already working in that project, submit these as separate commands:

```text
/reload-plugins
```

```text
/skill:ui-design-studio mode=guided
```

For an autonomous run:

```text
/skill:ui-design-studio mode=yolo
```

For either mode using the current model:

```text
/skill:ui-design-studio mode=guided models=current-model
```

`/ui-design` and `/ui-yolo` are the supplied convenience commands. Skill options are instructions interpreted by the director; they are not native OMP command-line flags. If your OMP version does not discover a command immediately, use the direct-reading prompts included in the package. An exit/restart is not part of the normal installation flow.

## Choose a run

| Goal | Recommended entry point | Expected checkpoint |
| --- | --- | --- |
| Redesign with your input | `/skill:ui-design-studio mode=guided` | Your concept choice and mockup approval |
| Complete a redesign autonomously | `/skill:ui-design-studio mode=yolo` | Verified result or a precise blocker |
| Sustain a longer autonomous redesign | `/goal` with the objective in the run guide | Verified full-scope completion |
| Report usability issues only | `/skill:ui-assess` | Assessment report; application unchanged |
| Explore and mock up a direction | Guided run with an explicit stop after Design | Mockups and design specification |
| Continue interrupted work | `/skill:ui-design-studio resume` | Next unmet dependency of the same run |
| Keep your chosen model | Add `models=current-model` | Main model and specialist assignments verified |

The [run guide](docs/RUN-TYPES.md) supplies complete prompts, expected outputs and stop/resume behaviour for each case.

## How the designer learns your project

At the start of a run, the director reads applicable `AGENTS.md` files and other project instructions, the README, relevant requirements/specifications and architecture decisions, existing design tokens/components, routes and dialogs, build/test commands, and the latest user direction. It records the relevant sources and constraints in the run's `project-context.md`.

Source code establishes current behaviour; it does not silently cancel a documented requirement. The director identifies conflicts and missing information, reuses existing answers, and asks only when a material unresolved choice requires input. It establishes whether offline operation is required from the project evidence. A directory name, a legacy profile value, or the supplied sample theme cannot decide that requirement.

The resolved context is hashed into the run's acceptance record. An unresolved or stale context prevents a full release from being marked complete. Workers receive the constraints they need explicitly; they do not depend on inheriting the main conversation.

## Design workflow

| Phase | Deliverables |
| --- | --- |
| **Assess** | Usability report, complete surface/state inventory, evidence-labelled findings, priorities, baseline and recommendations |
| **Plan** | Comparable visual concepts, semantic palettes, typography/spacing, component and icon samples, storyboards and tradeoffs |
| **Design** | Complete page/dialog mockups for the agreed inventory, relevant responsive layouts and states, interaction specifications and a shared design contract |
| **Produce** | Theme adapter and supported settings, implementation by bounded coding workers, rendered checks, tests and independent review/fixes |
| **Finalize** | Validated theme package, usage/customization documentation, coverage and verification report, default status, changelog and rollback instructions |

In guided mode, the director asks a compact preference interview after inspecting the project, then obtains your concept selection and mockup approval. It continues through routine implementation and review without repeated approval requests.

In YOLO mode, the director makes and records those aesthetic decisions, obtains independent critique, chooses a suitable theme name and works through finalization. Agent decisions are recorded as agent decisions. YOLO design does not change OMP's tool-approval settings or waive the project's quality/release rules.

## Model policy

| Option | Behaviour |
| --- | --- |
| **`auto-models` — default** | Inspect models available through the existing OMP configuration and select suitable assignments for design, coding, support and review. Verify and record the models actually used. |
| **`current-model` — explicit choice** | Use the active session model for the director and specialist workers. Preserve the selected model rather than making capability/cost substitutions. Verify existing agent overrides do not contradict the choice. |

Examples:

```text
/skill:ui-design-studio mode=yolo models=auto-models
/skill:ui-design-studio mode=yolo models=current-model
```

The director remains your active OMP session model in both modes. Automatic selection applies to specialist workers; it does not silently replace that main model.

No provider account, API credential or model subscription is supplied by this package. Availability and permitted routing come from your OMP installation. A requested assignment is not treated as successful until the runtime reports it. If a model cannot perform a required visual or technical check, the designer records the limitation and the work that remains.

The director applies the chosen worker assignments through the supported routing helper, checks live task metadata, and restores temporary agent settings before handover or a deliberate pause. A routing plan alone does not establish which models ran.

The project default is `modelPolicy` in `ui-design-studio.json`. A run's explicit option wins over that default. Resume preserves the recorded choice unless you explicitly change it. The agent-facing routing procedure is `.omp/skills/ui-design-studio/references/model-routing.md` after installation.

## Skills and team

| Skill | Responsibility |
| --- | --- |
| `ui-design-studio` | Direct the complete workflow and handover |
| `ui-assess` | Human factors, usability, inventory and baseline |
| `ui-plan` | Concepts, palettes, storyboards, icons and samples |
| `ui-design` | Full-page/dialog mockups and interaction specifications |
| `ui-produce` | Implementation and integration |
| `ui-review` | Independent visual, usability and engineering review |
| `ui-theme` | Theme contract, tokens, adapter and lifecycle |
| `ui-finalize` | Evidence, packaging, registration and documentation |
| `ui-yolo` | Autonomous complete design workflow |

The seven specialist roles are UX researcher, art director, page designer, theme engineer, implementer, quality reviewer and performance reviewer. Three concurrent workers is the starting policy. The director separates file ownership, keeps shared tokens/primitives under one owner, and uses independent review. Available native task capabilities and project limits control actual concurrency.

If no subagent capability is available, the director records that limitation and runs distinct role passes sequentially. It must not describe those passes as concurrent work.

## Themes and default behaviour

The supplied web theme format is **UI Theme Module v1**, a package-defined, versioned contract. Modules contain a manifest, typed token source, generated/scoped CSS, a small SVG symbol set, a preview and documentation. The tokens use a documented subset of the DTCG format. A real adapter connects the module to the project's existing theme mechanism.

The intended theme settings interface lets people inspect available themes, preview/select a theme, restore the default, and adjust only the preferences the implementation supports. Switching themes must preserve application state and provide a known-good fallback.

| Situation | Result |
| --- | --- |
| Install skills or create a scaffold | Application default does not change |
| First successfully finalized design run | Resulting module becomes the default, with prior styling recoverable |
| Later guided run | Choose modify-default or new, unless already specified |
| Later YOLO run | Make that choice autonomously; default to a new named module while keeping the current default |
| Modify a default theme | Preserve its ID, version the change, retain rollback evidence |
| Add a new theme | Register it as selectable; change the existing default only when chosen |

`Fieldstone` is the included format specimen, not a prescribed style for your project. Its preview is in `examples/studio-showcase.html`. The specimen has a light palette; it does not imply automatic dark-mode or application-wide coverage.

## Portability and quality

The assessment, design and team workflow can be applied across UI projects. The included executable theme compiler/validator and sample are for browser interfaces. React, Vue, Svelte, server-rendered applications and similar stacks still need the host adapter and actual integration checks. A native desktop/mobile project needs an adapter and validation appropriate to its toolkit; the director must establish that path before promising production-ready output. It must not force HTML/CSS into an incompatible native architecture.

Prefer code-native presentation, CSS/vector assets where supported, local fonts and existing components. Measure bandwidth, bytes, dependencies and runtime cost. The starting web-theme budget is 128 KiB raw and 40 KiB summed gzip, with no new theme runtime dependencies or remote runtime requests. These are adjustable package policies; they do not describe total application payload or measured speed.

For web work, target WCAG 2.2 AA and test keyboard/focus behaviour, labels, contrast, reflow, dialogs, reduced motion and applicable assistive technology. Use the corresponding platform requirements for native interfaces. A scanner or token-contrast pass alone does not establish accessibility conformance. Assessment observations, expert judgement and actual user research remain distinct.

## Records, status and handover

Default run location: `docs/design/runs/<run-id>/`. Default themes location: `themes/<theme-id>/`. The project configuration can change these paths.

A run records project context, model policy, actual routing, findings, coverage, decisions, evidence and blockers. The Design Server displays live progress, workers, tasks, coverage bars and gate statistics. Its Working feed shows generated artwork and mockups as clickable thumbnails. The accumulating Library retains browsable versions, and guided Approvals records submitted artistic choices against the reviewed bytes.

Start it in a retained foreground service after creating or resuming a run:

```bash
tools/ui-design design-serve docs/design/runs/RUN_ID --host 0.0.0.0 --port 0 --public-url http://YOUR_LAN_IP
```

Use the actual run directory and reachable LAN address. Readiness prints the complete URL with its actual port and access fragment. The installed OMP extension pins status and that address below the editor, separately from Pi Tasks. On hosts without that UI, `tools/ui-design status docs/design/runs/RUN_ID --watch` emits status regularly.

The URL authorizes its holder to inspect artwork and submit guided approvals. Keep it private. Plain HTTP is for trusted LAN use; use SSH forwarding or an existing HTTPS reverse proxy on untrusted networks. Starting the server does not create a public tunnel.

Use `tools/ui-design design-cleanup docs/design/runs/RUN_ID` to stop and completely remove owned server runtime resources. `design-cleanup --all --repo .` cleans all run servers in the configured run directory. Design evidence and the artwork library remain intact. Completed yolo runs automatically request cleanup and verify it at handover.

See `.omp/skills/ui-design-studio/references/run-records.md`, section "Live progress and Design Server", for publication, approvals and cleanup commands. Counts describe the actual declared scope; incomplete inventories do not become invented completion percentages.

A completed handover identifies the theme/version, package and preview, changed behaviour, default status, measured verification, known limitations, customization steps and rollback. A draft package or successful helper command is not, by itself, a completed redesign.

## Distribution and licensing

Keep the release archive, `MANIFEST.sha256`, documentation and license together. The installer and helpers use the Python standard library. The package includes no project source, credentials, provider accounts or collected user data.

`LICENSE.txt` contains the package's MIT license. Imported design references, icons, fonts and other project assets retain their actual licenses and provenance; this package does not relicense them. Consult the [validation record](docs/VALIDATION.md) for the scope of release checks. Your project's compatibility, visual quality and runtime performance are established by its own design run.
