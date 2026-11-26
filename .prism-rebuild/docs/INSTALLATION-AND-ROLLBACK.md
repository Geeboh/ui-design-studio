# Preparation, installation and rollback

Three operations have distinct recovery paths: preparing this implementation worktree, installing the eventual product into a consumer project, and migrating product data. Treating them as one generic “undo” risks losing later work.

## 1. Rebuild worktree preparation

`prepare-worktree.py` creates a new branch and sibling worktree from a selected committed base. It copies the handoff into `.prism-rebuild/`, records preparation state and installs only the local rebuild instructions. Existing uncommitted source edits stay in the original checkout. The source's working files are preserved; Git metadata changes because a worktree and branch are created.

The preparation receipt records source location, selected base commit, branch, destination, source dirtiness and pack manifest identity. A destination that already exists, a path inside the source checkout, a private-state symlink, an unowned preparation receipt or a conflicting skill is a blocker. Do not bypass these checks by deleting someone else's data.

If preparation stops after creating the worktree, inspect the reported path and receipt. Resolve the specific context conflict and rerun the context installer from the copied pack where safe. If the entire preparation should be discarded, first confirm that the worktree contains no work that must be retained, then use ordinary reviewed Git worktree removal. The helper deliberately does not run a destructive cleanup automatically.

## 2. Rebuild context ownership

The installer manages three files: the target's `AGENTS.md`, `.omp/skills/prism-rebuild/SKILL.md`, and Git's reported local `info/exclude` file. It stores original bytes and modes, desired bytes and hashes, installation state, repository identity and pack identity in `.prism-state/rebuild-context.json` before writing the managed files.

The managed AGENTS block points to the pack and retains all original project instructions. The product skill blueprints remain `.md.in`; they are inactive until the rebuilt engine and corresponding checks exist. These external OMP templates do not install a personal ChatGPT skill.

Git worktrees can share the common repository's `info/exclude`. Adding the private-state exclusions can therefore affect sibling worktrees' ignore behavior. It does not remove their files. The exact original exclude contents are recorded. A later owner edit to that file is a restore conflict; the installer will not overwrite it silently.

### Restore only the context

```bash
python3 .prism-rebuild/tools/install-rebuild-context.py --repo . --restore
```

Restore first checks every managed file against its recorded before/after digest. If any file changed after installation, it stops without restoring the others. Preserve the newer edit, inspect the receipt and deliberately merge the intended instruction/exclude changes. Do not change a receipt's hashes merely to force acceptance.

If there are no conflicts, original files and modes are restored; files created only by installation are removed. The receipt remains with state `restored`. Empty parent directories may remain. The worktree, rebuild pack, private evidence and product implementation commits remain intact. A later install can record a fresh baseline.

## 3. Product installation and upgrade

The eventual installer is a product deliverable in M7, with earlier foundations in M2 and final release qualification in M8. It must implement plan → validate → backup/receipt → apply → verify → activate. Its destinations, project root and ownership must come from an explicit validated plan, not from inherited host variables or unchecked archive paths.

Preserve consumer project instructions and customizations. Scope backups and restores to owned files. Repeated installs, partial failure, conflicting local edits, hostile inherited destination settings and uninstall/restore must have acceptance evidence. Installing the package must be checked independently from live OMP discovery and MCP startup. Keep existing public aliases during the documented compatibility period.

The handoff context installer is intentionally not reused as a pretend implementation of this broader product lifecycle. See [migration and compatibility](MIGRATION-AND-COMPATIBILITY.md), [security and operations](SECURITY-AND-OPERATIONS.md) and the INSTALL acceptance family.

## 4. Product data migration and rollback

Legacy project state is imported by copy into a candidate transactional store and immutable artifact directory. Archive and fingerprint the source before import. Preserve a source-to-target identity map; mark incomplete historical evidence and unknown historical spend honestly. Repeating an interrupted import must not create duplicate decisions, reservations or costs.

Verify the candidate store before activation. Record the chosen SQLite mode, actual runtime/source identity, integrity checks and migration version. A failure before activation leaves the original source usable. A failure after activation requires an explicit decision about later writes; never replace new valid decisions with an older backup as an automatic cleanup.

Rollback restores a recorded compatible data/version pair or exports/reconciles later work first. Keep referenced approved artifact versions through retention/garbage collection. Test this process against fixtures containing annotations, partial approvals, budget reservations, uncertain provider outcomes and theme customizations.

## Recovery decisions

| Situation | Safe next action |
| --- | --- |
| Original checkout has uncommitted work | Leave it there; have the owner commit or deliberately transfer it before selecting a new base |
| New worktree exists after partial preparation | Inspect its receipt and run the copied context installer only after resolving the stated conflict |
| Managed instructions changed after installation | Preserve them, compare recorded before/after content and merge deliberately |
| A gate failed or timed out | Keep the receipt/log, fix the stated cause and rerun the affected checks |
| Evidence or the plan changed after a pass | Treat the old pass as historical; bind new review and rerun required checks |
| Provider request timed out after possible acceptance | Reconcile using the stable operation/idempotency identity before deciding whether retry is safe |
| Migration verification failed before activation | Leave the original store active and fix/restart the candidate import |
| Data was written after activation | Export/reconcile later writes before any rollback to an older store |

Every recovery path should end with the next concrete action and the exact state it will use. “Start over” is not a substitute for preserving decisions, budget reservations or paid provider work.
