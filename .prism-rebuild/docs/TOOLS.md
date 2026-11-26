# Handoff tool reference

These tools operate on the rebuild pack and its implementation worktree. They are not the rebuilt product's runtime commands. Run them with Python 3.10 or later; full schema verification additionally needs `jsonschema` from [requirements-tools.txt](../requirements-tools.txt). No helper installs operating-system packages or sends messages.

Use absolute paths for the first preparation. After preparation, examples assume the current directory is the target Git worktree and the pack lives at `.prism-rebuild/`. Keep private state on a local filesystem. The helpers reject symlinked private-state paths and escaping destinations.

## Verify the handoff

```bash
python3 .prism-rebuild/tools/verify-pack.py --root .prism-rebuild
```

Full verification checks the SHA-256 manifest, complete file inventory, local Markdown links, all JSON parsing, requirement/case/milestone/gate references, the milestone dependency graph, knowledge-source references, ten inactive skill templates, the domain schema and its positive/negative fixtures. Duplicate JSON keys and non-finite numbers are rejected. `--integrity-only` performs the file/hash check without the optional schema library. Neither mode runs product tests.

Exit 0 means the requested pack check passed; exit 1 means the handoff failed that check. A changed pack must be reviewed and re-manifested before distribution; editing a file and ignoring its manifest mismatch defeats the check.

## Prepare a worktree

```bash
python3 /path/to/pack/tools/prepare-worktree.py \
  --repo /code/ui-design-studio \
  --dest /code/ui-design-studio-prism \
  --base HEAD \
  --branch overhaul/prism-v2
```

The destination must be new, outside the source checkout, and not its ancestor. Symlink and `..` resolution happens before that comparison. The base must identify a commit. Existing branch/destination conflicts stop the operation. Only committed source at that base is included; the receipt explicitly records source dirtiness without stashing or discarding it.

Preparation copies the verified pack, creates `.prism-state/prepare.json`, and invokes context installation. Existing unowned preparation receipts are not overwritten. A later failure preserves the partial worktree for inspection and returns `BLOCKED`; it does not automatically delete files or branches. The original working files remain untouched, while Git necessarily records the new worktree/branch and local excludes.

## Install or restore rebuild context

```bash
python3 .prism-rebuild/tools/install-rebuild-context.py --repo .
python3 .prism-rebuild/tools/install-rebuild-context.py --repo . --restore
```

Use one command for the intended operation. Installation requires the target's own verified `.prism-rebuild` copy matching the installer. It adds a managed reference to `AGENTS.md`, materializes only the `prism-rebuild` skill, and appends local Git exclusions for private state and a tools environment. It records exact original bytes, modes and replacement hashes before editing. Retrying an unchanged installation is idempotent; a partially written installation can resume from its receipt.

Restore preflights every recorded file before changing any. A newer edit causes a conflict and no restore writes. The operation restores recorded context only; it does not undo product commits, remove the worktree or roll back a product database. See [installation and rollback](INSTALLATION-AND-ROLLBACK.md).

## Inspect prerequisites

```bash
python3 .prism-rebuild/tools/preflight.py --repo . --json
```

This reports source identity, dirty state, Python support, this interpreter's actual SQLite version/source ID and visible Git/Node/npm/OMP executables. Recheck SQLite in the installed product runtime and verify patch provenance before selecting WAL. The helper does not prove that a discovered executable works for the required host integration. In-session skills, browser engines, model IDs, role routing and provider pricing still require actual discovery and smoke checks. Environment variable values and credentials are not printed.

## Fingerprint a candidate and plan

```bash
python3 .prism-rebuild/tools/run-gates.py --repo . \
  --plan .prism-state/verification-plan.release.json --fingerprint
```

The source fingerprint includes the Git commit plus tracked and nonignored untracked file contents, executable bits, symlink targets, submodule identity/state and dirtiness. Generated private state and the named tools environment are excluded. The plan hash is an exact byte hash. Commit the intended release candidate before generating the final review binding. An ignored arbitrary file is not made part of the source fingerprint; external tools, dependencies and test inputs therefore require explicit environment/version evidence.

`--fingerprint` does not run tests, validate a plan's semantics or create a pass. It can omit `--plan` when only source identity is needed.

## Bind and run implementation gates

Copy [the example plan](../config/verification-plan.example.json) into private state. Replace its empty command arrays with existing tests, actual argument vectors and precise acceptance mappings. Its `targetProfile` must equal the requested profile.

| Profile | Required gates | Scope |
| --- | --- | --- |
| `core` | G0–G4 | Discovery, shared domain, migration, design decisions, budget/models/workers |
| `web` | G0–G7 | Core plus dashboard, accessibility/performance, knowledge/themes and operations |
| `release` | G0–G8 | All required checks, packaging/host integration and exact-candidate review |

```bash
python3 .prism-rebuild/tools/run-gates.py --repo . \
  --plan .prism-state/verification-plan.core.json --profile core
```

For a focused iteration, add `--gate G0` or repeat `--gate` for several relevant gates. A subset result is `PASSED_SELECTED_GATES`, never a complete profile pass. Release mode still requires full current review evidence when selecting individual release gates.

Each command needs a unique ID, literal `argv`, repository-contained existing `cwd`, a timeout of 1–7200 seconds, `expectedExitCodes: [0]`, acceptance IDs belonging to that gate, and a list of expected evidence files. The runner does not invoke a shell. An intentional negative product response must be asserted inside a test harness that returns zero only when the assertion holds. Nonzero exits, timeouts, missing evidence and unchanged preexisting evidence fail.

The union of mappings must cover every case in the selected gates. This is necessary bookkeeping, not a semantic proof: a reviewer must inspect whether the test actually exercises the stated behavior. An `echo` command cannot meaningfully establish acceptance merely because its plan lists all IDs. Even a command with no separate evidence artifact retains its complete redacted execution log.

### Evidence and freshness

The runner creates a unique directory under `.prism-state/evidence/`. It saves the plan, source snapshot, complete redacted combined command output, captured copies of declared artifacts and a structured receipt. It records hashes, exit status, duration, timeout state, mapped cases, host details and whether source/plan/review remained unchanged.

Declared artifact files must be created or rewritten by the current command. An unchanged hash **and** modification timestamp is treated as stale. Captured copies remain available even if a later command removes the original report. Later deletion or alteration of a captured copy, log, review evidence or plan snapshot invalidates the result. This detects accidental staleness; it is not a sandbox against a malicious test program with the user's filesystem authority.

Commands receive these environment values for binding their reports:

| Variable | Meaning |
| --- | --- |
| `PRISM_GATE_RUN_ID` | Unique execution ID |
| `PRISM_GATE_COMMAND_ID` | Current plan command ID |
| `PRISM_GATE_SOURCE_SHA256` | Tested source fingerprint |
| `PRISM_GATE_PLAN_SHA256` | Reviewed plan byte hash |
| `PRISM_GATE_EVIDENCE_DIR` | Private evidence directory for this run |

Use reports with structured assertions and these identities where practical. Avoid credentials in command arguments, logs or artifacts. Known credential environment values and common token patterns are redacted from logs; automatic redaction cannot guarantee detection of every secret. Private logs are complete after redaction, not silently cut at a console-size limit. Captured artifacts are expected to be nonsecret.

### Review binding

Release review uses [REVIEW.example.json](../templates/REVIEW.example.json). It must identify the reviewer and implementation actors, cover all distinct release cases with passed evidence and substantive notes, bind the source and plan hashes, and report zero unresolved severe findings. Its paths must exist inside the worktree.

Independent review requires a reviewer actor distinct from every implementation actor. When a separate reviewer is unavailable, an explicitly declared sequential fallback needs a reason and the readiness recommendation `ready-with-disclosed-fallback`; successful status includes `_WITH_DECLARED_REVIEW_FALLBACK`. Identity fields do not prove independence on their own: retain the actual review record and task provenance.

### Exit codes and statuses

| Exit | Status | Interpretation |
| --- | --- | --- |
| 0 | `PASS` | All requested profile gates executed successfully against unchanged inputs |
| 0 | `PASSED_SELECTED_GATES` | Only the explicitly selected gates passed |
| 0 | Either status with `_WITH_DECLARED_REVIEW_FALLBACK` | Review used the disclosed sequential fallback |
| 1 | `FAILED` | One or more executed checks, freshness constraints or retained-evidence checks failed |
| 2 | `BLOCKED` | Configuration, prerequisites, ownership or review binding prevented qualification |

Human participant validation remains `DEFERRED` in every profile. A real browser/host check required by a profile cannot be waived by that policy.

## Inspect current status

```bash
python3 .prism-rebuild/tools/status.py --repo .
```

The tool reports the progress ledger separately from observed verification. It rechecks source, current plan, review, receipt, captured artifacts and logs. A recorded result can remain historically passed while `current` is false. `NOT_RUN` is explicit. Missing or malformed evidence cannot become current qualification by editing the progress ledger.

## Test the helper tools

```bash
python3 .prism-rebuild/tools/test_tools.py
```

The tests create disposable Git repositories and subprocess fixtures. They verify the handoff's lifecycle and failure handling; they do not exercise UI Design Studio's production behavior. Read [pack validation](../validation/PACK-VALIDATION.md) for the delivered pack's actual observed results and limits.

## Build a deterministic handoff ZIP

```bash
python3 .prism-rebuild/tools/build-pack.py --root .prism-rebuild \
  --output /absolute/path/PRISM-Studio-Rebuild-Pack-v1.0.0.zip
```

The output must be a new path outside the pack. The tool requires a valid manifest, uses the versioned canonical archive root from pack metadata plus sorted entries/fixed timestamps/normalized file modes, excludes private scratch/caches and rejects sourcebook PDFs. Renaming the input directory, including to `.prism-rebuild`, does not change the archive. It does not build or publish the product. ZIP reproducibility is defined for the same files and compression runtime; record Python/zlib when comparing across hosts.
