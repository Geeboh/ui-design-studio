# Configuration

## Project configuration

The installer creates ui-design-studio.json only when absent. Source-defined defaults:

    schemaVersion: 1.0
    mode: guided
    maxWorkers: 3
    modelPolicy: auto-models
    paths.runs: docs/design/runs
    paths.themes: themes
    budgets.maxThemeRawBytes: 131072
    budgets.maxThemeGzipBytes: 40960
    budgets.addedRuntimeDependencies: 0
    budgets.remoteRuntimeRequests: 0
    quality.target: WCAG-2.2-AA
    quality.touchTargetCssPx: 44
    git.branchPrefix: design/
    git.autoCommit/autoPush/autoMerge: false
    autonomy.laterThemeAction: new
    autonomy.maxReviewIterations: 3

An existing configuration is preserved by installation. The workflow reads project requirements and current instructions instead of requiring a profile.

## Run storage

The configured paths.runs directory contains run directories. The design server records metadata, status snapshots, evidence, artwork, approvals, and locks there. Runtime files such as .design-server.json, .design-status.json, and ownership/lock files are private runtime state for release tooling.

## Theme and model configuration

Themes use a versioned module contract. The checked-in example uses semantic tokens, local CSS/SVG assets, forced-colors and reduced-motion handling, contrast pairs, and raw/gzip budgets. Exact requirements are in .omp/skills/ui-design-studio/schemas/theme.schema.json and references/theme-module.md.

Model policy distinguishes automatic routing from current-model routing. The source requires recording actual route evidence and restoring temporary routing state before installation or update. Provider availability is not established by this review.

Sources: scripts/install.py:141-153,243-307, .omp/skills/ui-design-studio/references/project-context.md, model-routing.md, theme-module.md, schemas/theme.schema.json, release.json.
