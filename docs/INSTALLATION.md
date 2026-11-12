# Installation, configuration and maintenance

**UI Design Studio 1.1.0**

## Contents

1. Requirements
2. Select the project and install
3. Start from a running OMP session
4. Installed files
5. Project configuration
6. Update an existing installation
7. Restore an installation update
8. Troubleshooting
9. Distribution checks and portability

## 1. Requirements

| Requirement | Purpose |
| --- | --- |
| Bash on Linux, macOS or a compatible environment | Installation entry point and installed wrapper |
| Python 3.10+ with `venv` | Standard-library installation and theme/run utilities |
| Oh My Pi configured for your project | Executes the designer and specialist work |
| Existing project dependencies | Builds and tests the actual application |
| Rendering/inspection capability for the target UI | Verifies mockups and actual implemented screens |

Use the project's supported environment. On Windows, a compatible Linux/WSL environment is appropriate for the supplied Bash installer; do not assume these shell scripts are native PowerShell commands. A Windows-hosted application may have a separate build/test environment to discover.

All package Python work runs in a virtual environment. The installer bootstraps one temporarily, then creates the project's `.venv-ui-design`. The helper uses the standard library; installation does not require pip packages, network downloads or `sudo`. On Ubuntu, missing Python/venv support is normally supplied by the OS packages `python3` and `python3-venv` using your established administration process.

The designer inspects available OMP capabilities at runtime. A particular Figma account, image-generation service, MCP server, provider or model is not required by the package. Rendered verification is still necessary when the requested result includes verified visuals. If the target rendering environment is missing, the run must report that precise gap.

## 2. Select the project and install

Extract the release. Open a shell in its `ui-design-studio-v1.1.0` directory. Point `--project` at the existing repository containing the application you want to redesign:

```bash
bash ./install.sh --project /absolute/path/to/project --dry-run
bash ./install.sh --project /absolute/path/to/project
```

`--dry-run` previews the complete set of installation changes. It does not install files. The second command performs them.

The project directory must already exist. The installer does not infer a project from your current shell location or create a replacement application. For example, `/code` may contain several repositories; select the intended one rather than installing into their parent directory.

Now check the installation from the project root:

```bash
cd /absolute/path/to/project
./tools/ui-design doctor --repo .
```

A `doctor` result reports discovered project/package information. It does not mean the application has passed usability, accessibility or performance checks.

**There is no profile argument to choose.** The design director reads the project's existing requirements. For compatibility, older invocations using the former installer `--profile` argument are accepted with a deprecation notice; new work does not use that value to choose project constraints.

## 3. Start from a running OMP session

When OMP is already open in the target project, refresh discovery:

```text
/reload-plugins
```

Then run:

```text
/skill:ui-design-studio mode=guided
```

Or use the installed convenience command:

```text
/ui-design mode=guided
```

Automatic model selection is the default. To use the active session model throughout the team:

```text
/skill:ui-design-studio mode=guided models=current-model
```

If command discovery is unavailable or differs in your OMP version, submit the direct-reading prompt in `docs/ui-design-studio/prompts/START-GUIDED.md`, or simply:

```text
Read .omp/skills/ui-design-studio/SKILL.md and start a guided UI Design Studio run for this project. Read the project's existing requirements. Use auto-models.
```

Do not exit OMP merely to hand-copy the installed files. If you are in a different repository, open or switch to the intended project's session using your existing OMP workflow first.

See [Run types](RUN-TYPES.md) for autonomous work, `/goal`, assessments, references and continuation.

## 4. Installed files

All paths below are relative to the selected project root.

| Path | Purpose |
| --- | --- |
| `.omp/skills/ui-*/` | Nine design skills and shared references/resources |
| `.omp/agents/ui-*.md` | Seven specialist role definitions |
| `.omp/commands/ui-design.md` | Guided/director convenience command |
| `.omp/commands/ui-yolo.md` | Autonomous design convenience command |
| `tools/ui-design` | Venv-backed theme and run helper |
| `ui-design-studio.json` | Project design policy; created once and preserved on update |
| `docs/ui-design-studio/` | User documentation and ready-to-use prompts |
| `.venv-ui-design/` | Local Python virtual environment |
| `.ui-design-studio/` | Installer ownership state and restore history |
| Marked block in `AGENTS.md` | Tells OMP when to load the designer and preserve project requirements |
| Marked block in `.gitignore` | Excludes the package venv and installation backups |

Existing surrounding `AGENTS.md` and `.gitignore` content is preserved. Installation does not switch the application's theme, replace its codebase, choose a remote provider, or install application dependencies. Model routing is resolved when a run starts under the selected policy.

The existing `.omp/config.yml` remains under the project's and operator's control. Any run-specific routing work follows the installed model-routing procedure and preserves unrelated settings.

## 5. Project configuration

The installer creates `ui-design-studio.json` only when it does not exist. Its default values are:

```json
{
  "schemaVersion": "1.0",
  "mode": "guided",
  "modelPolicy": "auto-models",
  "maxWorkers": 3,
  "paths": {
    "runs": "docs/design/runs",
    "themes": "themes"
  },
  "budgets": {
    "maxThemeRawBytes": 131072,
    "maxThemeGzipBytes": 40960,
    "addedRuntimeDependencies": 0,
    "remoteRuntimeRequests": 0
  },
  "quality": {
    "target": "WCAG-2.2-AA",
    "touchTargetCssPx": 44
  },
  "git": {
    "branchPrefix": "design/",
    "autoCommit": false,
    "autoPush": false,
    "autoMerge": false
  },
  "autonomy": {
    "laterThemeAction": "new",
    "maxReviewIterations": 3
  }
}
```

These are **Studio policy keys**, not native OMP settings. The helpers enforce their supported paths and byte limits; the director applies the workflow, quality, worker and Git preferences alongside the actual project's instructions.

| Setting | Meaning |
| --- | --- |
| `mode` | Default decision style, `guided` or `yolo` |
| `modelPolicy` | `auto-models` by default; `current-model` keeps the active model for the team |
| `maxWorkers` | Requested concurrency ceiling; the runtime may impose a lower limit |
| `paths` | Project-relative output locations |
| Theme byte budgets | Limits for declared runtime theme assets, separate from the whole application's payload |
| Dependency/request budgets | Director-enforced design targets, checked with real project evidence |
| `quality` | Starting accessibility and input-target policy; reconcile with the project's requirements |
| `git` | Branch naming and commit/push/merge preferences within existing authorization |
| `autonomy` | Later-theme default and bounded repair policy |

Set a preference by editing its existing key, preserving other project values. For example, change only `modelPolicy` to `current-model` if that should be the default for future runs. A run's explicit `models=...` option takes precedence. A resumed run retains its recorded policy unless you request a change.

An older configuration may retain a legacy `profile` key. You do not need to remove it manually: new runs discover requirements from the project. The update preserves your existing file rather than silently rewriting custom settings.

## 6. Update an existing installation

Let the current design run reach a checkpoint and have the director restore its temporary worker routing before updating package-owned agent files. This preserves active work and avoids mistaking a run-specific assignment for a user edit. An OMP exit/restart is not required.

Use the newly extracted release and the same project root:

```bash
bash ./install.sh --project /absolute/path/to/project --update --dry-run
bash ./install.sh --project /absolute/path/to/project --update
```

The updater preflights changes, checks package ownership, backs up replaced/retired managed files, and preserves the user's configuration and unrelated files. Local edits to a file it needs to replace or retire must be reconciled; `--update` is not a force-overwrite switch.

After updating, use `/reload-plugins` in the project session. Resume an existing design run when that is the intended work; do not begin a second overlapping run accidentally.

Version 1.1.0 reads existing 1.0 run dossiers without rewriting their accepted history. Completed dossiers stay immutable. When an incomplete 1.0 run needs the new workflow or model helpers, the director creates a linked 1.1 continuation, preserving the old dossier and recording its path/digest as provenance. It reuses the existing theme scaffold, retains the theme identity/action where valid, re-reads current requirements, resolves model routing, reconciles coverage and revalidates evidence. Authentic still-valid design choices remain traceable; final acceptance is never imported. Legacy TADA continuations retain the offline requirement. See [Continue interrupted work](RUN-TYPES.md#11-continue-interrupted-work) for the full procedure.

Use the ordinary resume prompt: you do not need to edit schemas or run migration commands. This is a procedure performed by the director, not a separate automatic migration utility. A successful installation update does not refresh old application test evidence by itself.

Keep the release used for the update and its printed backup ID until the new installation has been checked.

### Recover temporary routing after interruption

The model-routing helpers operate on 1.1 dossiers and their routing journals; an untouched 1.0 dossier has no new routing to restore. The director normally restores routing itself. If a 1.1 run was interrupted before it could do so, ask OMP to restore that run's temporary routing using the installed model-routing procedure. For manual recovery from the project root, use the exact run directory:

```bash
./tools/ui-design models-restore --repo . --run docs/design/runs/ACTUAL_RUN_ID
```

Replace `ACTUAL_RUN_ID` with the real identifier. Restore checks for later edits before changing any agent definition. Do not remove its journal to force an update. A resumed run can reapply its verified policy through `models-apply`; this helper consumes the director's routing record and does not choose models or create verification evidence by itself.

## 7. Restore an installation update

A changed install prints a backup ID. Substitute that exact value for `BACKUP_ID`:

```bash
bash ./install.sh --project /absolute/path/to/project --restore BACKUP_ID --dry-run
bash ./install.sh --project /absolute/path/to/project --restore BACKUP_ID
```

Restore checks the affected files' current content and permissions first. It stops if later edits would be overwritten. It preserves installation history and the venv.

This restores **package installation changes**. Application modifications made by a design run have their own project branch/release and theme rollback procedure. To undo a redesign, use its recorded rollback instructions and the application's previous theme/version; do not assume installer restore reverts the app.

There is no general-purpose `--uninstall` command in this release. If restoring the initial installation, the backup reverses its recorded changes subject to the same conflict checks. It does not recursively delete unrelated project work.

## 8. Troubleshooting

| Symptom | Check and next action |
| --- | --- |
| `tools/ui-design` cannot be found | Check the actual project root and the installer's `--project` path. The wrapper belongs in that repository's `tools/` directory. |
| Installer file is not executable | Use `bash ./install.sh ...`; archive extractors do not always preserve mode bits. |
| Python cannot create a venv | Install the Python/venv OS support appropriate to your environment, then rerun the installer. Keep helper execution in the created venv. |
| Skill or convenience command is missing | Confirm the installed `.omp` paths, refresh with `/reload-plugins` where supported, or use the direct-reading prompt. Inspect the installed OMP discovery configuration. |
| Installation reports a file conflict | Read the reported path. Compare local edits with the new package and preserve them deliberately; do not delete ownership state or bypass the preflight. |
| `/goal` is unavailable | Use the normal YOLO command. Check your installed OMP goal capability/settings if you want goal continuation. No goal mode is required for the skill itself. |
| Workers use unexpected models | Inspect the run's actual routing record and OMP's existing agent overrides. A planned assignment is not evidence of the launched model. Follow the model-routing reference. |
| No renderer/browser is available | Continue independent source assessment and artifact preparation, but leave required rendered verification blocked. |
| A worker wait times out | Inspect its status/output. A wait timeout is not evidence that the worker failed; avoid duplicate writers. |
| A valid CSS feature is rejected | The theme validator supports a conservative subset. Adapt it or deliberately extend the contract with tests and documentation. Do not disable a gate simply to obtain a pass. |
| `check-run` returns blocked | Read the missing/stale context, routing, coverage, decision or evidence entry. Perform the underlying work and update the record honestly. |
| A resume repeats earlier questions | Direct it to the relevant recorded run and existing decisions. The agent should revisit only materially changed or unapproved choices. |

Helper exit codes are `0` for the invoked operation passing, `1` for failed/invalid input, and `2` for blocked/incomplete work. A successful archive build or structural check does not prove the application was rendered or tested.

## 9. Distribution checks and portability

The archive's `MANIFEST.sha256` covers the shipped files other than the manifest itself. From the extracted package root, an environment with GNU-compatible checksum tools can verify it with:

```bash
sha256sum --check MANIFEST.sha256
```

An outer ZIP checksum detects transfer damage when provided with the release. Neither checksum is a publisher's digital signature.

Installation is project-local. Repeat the same install command for each target project; no global profile file or TADA-specific setting is needed. Use each project's own run records and theme registry.

The shared design process is reusable across UI stacks. The supplied theme validator and specimen target web interfaces. Native mobile/desktop systems require a deliberate toolkit-compatible adapter and checks, documented in the run. The package never treats a web preview as proof that a native implementation works.

Before redistributing a modified package, update its version and documentation, run its relevant checks, regenerate the manifest, and retain the applicable license. Exclude local project code, credentials, user screenshots, caches, venvs and installation backups. See [Validation](VALIDATION.md) and [Sources](SOURCES.md) for this release's verification scope and upstream references.
