# Start rebuilding PRISM Studio

Use this guide to rebuild the **UI Design Studio repository itself**. Do not run these preparation steps in a different application merely using UI Design Studio.

## 1. Extract and verify the handoff

Extract the ZIP once. You should see `PRISM-Studio-Rebuild-Pack-v1.0.0/` with this guide, `tools/`, `contracts/`, `docs/`, `prompts/`, and `knowledge/`.

Set these three paths to your actual locations. The worktree destination must be new and outside the source checkout.

```bash
prism_pack="/absolute/path/PRISM-Studio-Rebuild-Pack-v1.0.0"
prism_repo="/code/ui-design-studio"
prism_worktree="/code/ui-design-studio-prism"
python3 "$prism_pack/tools/verify-pack.py" --root "$prism_pack" --integrity-only
```

Expected: a JSON `PASS` explicitly scoped to handoff file integrity. This first check uses only Python 3.10+ and does not claim product verification.

For full handoff validation, use an existing Python environment containing `jsonschema`, or create a local tools environment:

```bash
python3 -m venv "$prism_pack/.prism-tools-venv"
"$prism_pack/.prism-tools-venv/bin/python" -m pip install -r "$prism_pack/requirements-tools.txt"
"$prism_pack/.prism-tools-venv/bin/python" "$prism_pack/tools/verify-pack.py" --root "$prism_pack"
```

This installs one validation dependency into that local environment. It does not alter system Python or the application's dependencies. If `venv` is unavailable, record that prerequisite; do not silently install operating-system packages.

If you do not yet have the repository, clone it to the chosen source location before continuing:

```bash
git clone https://github.com/Geeboh/ui-design-studio.git "$prism_repo"
```

## 2. Prepare the isolated rebuild

```bash
python3 "$prism_pack/tools/prepare-worktree.py" --repo "$prism_repo" --dest "$prism_worktree"
cd "$prism_worktree"
python3 .prism-rebuild/tools/preflight.py --repo . --json
```

Preparation creates branch `overhaul/prism-v2`, checks out the selected committed `HEAD`, copies this pack to `.prism-rebuild/`, preserves existing `AGENTS.md` content, adds a short rebuild reference and installs the project-local `prism-rebuild` skill. It records originals and ownership under `.prism-state/`. Generated state and the tools environment are added to Git's local exclude file; existing exclude contents are preserved.

The original working files remain in place. Uncommitted edits in the source checkout are **not** included in the new worktree; the receipt reports their presence. If those edits belong in the rebuild, have the owner commit or deliberately transfer them first. The tool never stashes, resets, cleans, force-pushes or overwrites an existing destination.

To use another committed base or branch:

```bash
python3 "$prism_pack/tools/prepare-worktree.py" --repo "$prism_repo" --dest "$prism_worktree" --base main --branch overhaul/prism-v2-local
```

Run that instead of the default preparation, with a still-new destination. Do not run both against the same path.

## 3. Launch the rebuild in OMP

**Recommended: one OMP goal owns the rebuild.** Start OMP in the new worktree. In an existing session, refresh discovery if supported:

```text
/reload-plugins
```

Then send this as one message:

```text
/goal Read .prism-rebuild/prompts/MASTER-REBUILD.md and carry out its complete PRISM Studio rebuild objective for this repository through milestones M0–M8. Continue until a verified release candidate exists or a precise genuine blocker remains after all independent work is complete.
```

For a new interactive session whose installed version supports `--goal`:

```bash
omp --goal "Read .prism-rebuild/prompts/MASTER-REBUILD.md and execute the PRISM Studio rebuild through verified milestones M0-M8."
```

Use either the in-session goal or the new-session command. Do not combine `--goal` with a positional prompt, `@file`, piped input, resume flags or another startup mode. Do not nest `/skill` inside `/goal` and assume both commands execute. Inspect `omp --help` for the installed version.

If goal mode is unavailable, paste the contents of [MASTER-REBUILD.md](prompts/MASTER-REBUILD.md) into normal mode. The on-disk progress and continuation prompts still work. `/vibe`, pstack and compression extensions are optional; do not add a second director.

## 4. What the first milestone should produce

M0 must inventory the real checkout and host, compare it with the reviewed baseline, reproduce relevant defects, identify supported tools/models, record project constraints, and bind the first acceptance cases to actual tests. Expect files under `.prism-state/` such as:

- `progress.json`: milestone state and next tasks.
- `build-policy.json`: resolved choices and authority; start from the supplied example when useful.
- `discovery.md`: evidence and differences from the reviewed baseline.
- `decisions.md`: concrete choices and why they were made.
- `verification-plan.json`: actual command arrays, filled progressively.
- `blockers.md`: only genuine unresolved dependencies, with exact recovery actions.

The empty command arrays in the example verification plan are deliberate: a future test command cannot pass before it exists. OMP must implement meaningful tests, map them to acceptance IDs and run them.

## 5. Continue without starting over

If the same OMP goal is paused, use its supported resume control (currently `/goal resume`). Otherwise send:

```text
Read .prism-rebuild/prompts/RESUME.md. Continue the existing PRISM rebuild using its on-disk state; preserve valid decisions and completed work.
```

Inspect progress from a terminal:

```bash
python3 .prism-rebuild/tools/status.py --repo .
```

`NOT_RUN`, stale evidence, deferred human validation and selected-gate results are intentionally distinct from release readiness.

## 6. Verify actual implementation

After OMP has created a real plan and committed the intended candidate:

```bash
python3 .prism-rebuild/tools/run-gates.py --repo . --plan .prism-state/verification-plan.json --profile core
```

The plan's `targetProfile` must match the selected profile. Use a separately reviewed plan for `web` or `release`; the release plan needs review evidence tied to the exact source and plan hashes. See [tools](docs/TOOLS.md) and [quality and release](docs/QUALITY-AND-RELEASE.md).

The runner executes the configured programs. Review those argv arrays before running a plan obtained from another person. It checks completeness of the mappings and records execution; the independent reviewer must verify that the mapped tests actually assert the promised behavior.

## 7. Finish, publish, or roll back

The master objective ends with a verified release candidate, installable archives, CI, migration/rollback evidence and human-readable documentation. It does not silently publish a release or merge the default branch. [Publish](prompts/PUBLISH-RELEASE.md) provides a separate explicit-authority prompt when you are ready.

To remove only the temporary rebuild context:

```bash
python3 .prism-rebuild/tools/install-rebuild-context.py --repo . --restore
```

Restoration checks that the managed files still match the installation receipt. If someone changed them afterward, it reports a conflict and preserves those changes. It does not revert implementation commits or delete the worktree. Follow [preparation and rollback](docs/INSTALLATION-AND-ROLLBACK.md) for the distinct recovery paths.

## Two budgets and two kinds of validation

The rebuilt product's design budget limits concepts, mockups, artwork and design revisions. The cost of coding this rebuild is a separate implementation concern. Existing model-session charges are not made free or capped by this handoff.

Human participant testing is deferred. Automated browser interaction, accessibility checks, actual OMP/MCP integration and package-install checks remain required for the relevant release claims. A test plan, screenshot mockup, dry run or unavailable tool is not a passed test.
