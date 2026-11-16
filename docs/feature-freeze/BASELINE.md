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

## Independent revalidation on 16 November 2026

The current audit uses branch `feature-freeze/2026-11-16-audit-unique` in `/code/ui-design-freeze-20261116-UKWQB8`.
It starts from the same `95cfb11786f6aae8c15f308787b614520ca5718d` baseline.
The initial user delta remains in `/code/ui-design-studio`.
Its separate backup is `/tmp/ui-design-feature-freeze-user-baseline.patch`.
The backup SHA-256 is `fb29118bac96bc2cd4a80991b40ac662f084614eaa50e9deb89bffde29ba229c`.

Existing remediation through `5b1d7313247eb33bae5319c4be72c63ef809357b` was integrated by fast-forward on this isolated branch.
Its earlier verification claims remain historical until repeated in this audit.
Four independent read-only reviewers inspect the actual engine, adapter, distribution, and workflow files.
The parent reviews browser and extension code.
The throughput checkpoint assigns independent review partitions while keeping mutation and final validation under one owner.

The current validation environment is `/tmp/ui-freeze-env-pLA7SH`, using Python 3.12.3 and Node 24.22.2.
The unchanged baseline ran 228 unittest cases and ended with five errors.
Four errors required the verification-only Pillow dependency.
Wheel test setup also required Hatchling for its explicit no-isolation build.
Those missing prerequisites were installed before candidate verification.
The baseline output is `/tmp/ui-freeze-evidence-UKWQB8/baseline-tests.log`.

### Setup incident

A failed worktree-creation command did not stop subsequent copies.
Those copies replaced `studio.py` and `docs/CHANGELOG.md` in the pre-existing `/code/ui-design-studio-freeze` worktree.
Both files were restored to that worktree's committed bytes before further work.
Their verified SHA-256 values are `04e36fb8b093a02d81586185026c1ad22c8658931da50d75db99497a65a55922` and `5470e75bb2e9f6e5af7f61eba63623b8b4a5d56d6d53c75eece4f6c8d10110e5`.
No pre-copy snapshot of that worktree exists for this session.
Unobserved pre-existing uncommitted edits there cannot be ruled out or recovered from this session's evidence.
The original checkout's two user files were not modified.

## Explicit shipping authorization

After the completed local audit, the user requested “Finish your work and ShipIt”. This supersedes the original no-automatic-shipping boundary for one normal branch push, GitHub PR and independently verified merge into `main`. GitHub CLI is used because no `origin` executable is installed. Remote `main` remained at the recorded `95cfb11786f6aae8c15f308787b614520ca5718d` baseline when shipping began. No force-push, package release, deployment or integration of the original user delta is authorized by this follow-up.
# Current checkout revalidation

The active checkout is `main` at `5a3c603e4f95c884d5b0535eb4aa52c2a7ff62c4` (`v1.4.2`), not the historical audit worktree named above. The working tree contains the three requested UI remediations, their tests, and changelog entries. Untracked `AGENTS.md` is preserved as project instructions.

The current verification environment uses CPython 3.12, Node 24.22.2, OMP 18.20.3, and a cached Chromium executable. The historical branch and worktree claims remain historical evidence and do not describe this checkout.
