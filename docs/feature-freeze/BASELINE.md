# Feature-freeze baseline

## Repository state

The freeze starts from commit `95cfb11786f6aae8c15f308787b614520ca5718d`, release 1.4.1, on `main`.
The remote is `https://github.com/Geeboh/ui-design-studio.git`.
Recent history uses conventional, logically scoped commit messages.
No repository-specific branch protection configuration is available locally.

The original checkout contains existing unstaged user changes in these files:

- `.omp/skills/ui-design-studio/scripts/studio.py`.
- `docs/CHANGELOG.md`.

The observed delta is 96 insertions and four deletions. No staged changes were reported.
A binary-capable copy of that delta is retained outside the repository at `/tmp/ui-design-freeze-baseline/user-changes.patch`.
Those changes remain in the original checkout and are not included in remediation commits.
They include an initial-input transition and worker allowlist correction. Their integration requires separate review before combining branches.

## Isolation and rollback

Workspace policy rejected switching the shared checkout's branch.
The dedicated branch `feature-freeze/2026-11-15-hardening` therefore uses `/code/ui-design-studio-freeze`.
This worktree starts from the baseline commit without importing user edits.
All remediation writes and commits belong to that worktree.
No release, merge, force-push, destructive reset, or deployment is authorized by this work.
Rollback consists of reverting the individual remediation commits on a consuming branch.
The original checkout and its user edits do not require rollback.

## Toolchain and validation discovery

System Python is `python3`, version 3.12.3. The command `python` is unavailable.
Node is 24.22.2. An isolated validation environment is being prepared under `/tmp/ui-design-freeze-venv`.
The project uses Python unittest, Node's test runner, Hatchling wheel builds, and its own release manifest checker.
No lint, type-check, CI, or coverage configuration is tracked.
No language servers are configured in the host.

An attempted editable installation failed because Hatchling does not support the declared prefix-rewriting source layout in editable mode.
Validation uses a regular wheel installation instead. This is an observed development-install limitation, not evidence of a broken release wheel.
Baseline gate results are recorded in [TEST-MATRIX.md](TEST-MATRIX.md) as execution completes.

## Exit condition

The complete tracked repository must have recorded inspection coverage.
Every confirmed finding must have a verified correction or an explicit justified risk disposition.
All practical release gates must have recorded results, including exact prerequisites for blocked checks.
Independent review must cover the remediation.
All thirteen requested feature-freeze documents must reflect current evidence.
Changes must be committed in reviewable units without including existing user edits.
Any unverified required criterion prevents an unconditional release-ready verdict.
