#!/usr/bin/env python3
"""Install or restore only the project-local PRISM rebuild instructions."""
from __future__ import annotations
import argparse
from pathlib import Path
import os
import sys
from prism_pack import PACK_ROOT, atomic_write, b64, digest, emit, git, read_json, repo_root, stamp, state_path, unb64, verify_manifest, write_json

BEGIN = "<!-- PRISM-REBUILD:BEGIN v1 -->"
END = "<!-- PRISM-REBUILD:END v1 -->"
BLOCK = ("\n\n" + BEGIN + "\n## PRISM Studio rebuild\nDuring this rebuild, read `.prism-rebuild/AGENTS.md` and the assigned task's references. Preserve all applicable existing project instructions. These instructions govern the rebuild of this repository; do not ship this block into consumer projects.\n" + END + "\n").encode()

def capture(path):
    if path.is_symlink():
        raise ValueError(f"Refusing to replace a symlink: {path}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Expected a regular file: {path}")
    data = path.read_bytes() if path.exists() else None
    return data, (path.stat().st_mode & 0o777 if path.exists() else 0o644)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()
    root = repo_root(args.repo)
    receipt_path = state_path(root, "rebuild-context.json")
    exclude_raw = Path(git(root, "rev-parse", "--git-path", "info/exclude").decode().strip())
    common_raw = Path(git(root, "rev-parse", "--git-common-dir").decode().strip())
    common = (root / common_raw).resolve(strict=True) if not common_raw.is_absolute() else common_raw.resolve(strict=True)
    exclude = Path(os.path.abspath(root / exclude_raw if not exclude_raw.is_absolute() else exclude_raw))
    if not exclude.is_relative_to(common):
        raise ValueError("Git exclude path must be inside the actual common Git directory without redirected parents")
    current = common
    for part in exclude.relative_to(common).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Refusing a redirected Git exclude path: {current}")
        if current != exclude and current.exists() and not current.is_dir():
            raise ValueError(f"Git exclude parent must be a directory: {current}")
    targets = {"agents": root / "AGENTS.md", "skill": root / ".omp/skills/prism-rebuild/SKILL.md", "exclude": exclude}
    for key in ["agents", "skill"]:
        if not targets[key].parent.resolve().is_relative_to(root):
            raise ValueError("Instruction directory resolves outside the target repository")
    old = read_json(receipt_path) if receipt_path.exists() else None
    if old and Path(old.get("repository", "")).resolve() != root:
        raise ValueError("Context receipt belongs to another repository")
    if args.restore:
        if not old or old.get("state") == "restored":
            emit({"status": "NOT_INSTALLED", "repository": str(root)})
            return
        changes = old["changes"]
        for key, change in changes.items():
            current, _ = capture(targets[key])
            current_sha = digest(current) if current is not None else None
            if current_sha not in (change["beforeSha256"], change["afterSha256"]):
                raise ValueError(f"Restore conflict in {targets[key]}; preserve newer edits and reconcile manually. Nothing restored.")
        for key, change in changes.items():
            p = targets[key]
            if change["beforeBase64"] is None:
                if p.exists():
                    p.unlink()
            else:
                atomic_write(p, unb64(change["beforeBase64"]), change["beforeMode"])
        old.update(state="restored", restoredAt=stamp())
        write_json(receipt_path, old)
        emit({"status": "RESTORED", "repository": str(root), "note": "Only recorded context changes were restored; the pack and worktree remain."})
        return
    info = verify_manifest(PACK_ROOT)
    local_pack = root / ".prism-rebuild"
    if not local_pack.is_dir() or local_pack.resolve() != local_pack:
        raise ValueError("The target needs its own .prism-rebuild pack. Use prepare-worktree.py first; no context was installed.")
    local_info = verify_manifest(local_pack)
    if local_info["manifestSha256"] != info["manifestSha256"]:
        raise ValueError("Target rebuild pack differs from this installer; use the installer in the target's verified .prism-rebuild directory")
    if old and old.get("state") in ("installed", "installing"):
        previous_state = old["state"]
        if old["pack"]["manifestSha256"] != info["manifestSha256"]:
            raise ValueError("A different rebuild pack is installed. Restore its context before installing this version.")
        for key, change in old["changes"].items():
            current, _ = capture(targets[key])
            if (digest(current) if current is not None else None) not in (change["beforeSha256"], change["afterSha256"]):
                raise ValueError(f"Installed context changed: {targets[key]}. Reconcile it before retrying.")
        for key, change in old["changes"].items():
            atomic_write(targets[key], unb64(change["afterBase64"]), change["beforeMode"])
        old.update(state="installed", installedAt=stamp())
        write_json(receipt_path, old)
        emit({"status": "ALREADY_INSTALLED" if previous_state == "installed" else "INSTALLED", "repository": str(root)})
        return
    data = {key: capture(p) for key, p in targets.items()}
    agents = data["agents"][0] or b""
    if BEGIN.encode() in agents or END.encode() in agents:
        raise ValueError("An unmanaged PRISM context block exists; reconcile it before installation.")
    if data["skill"][0] is not None:
        raise ValueError("An existing prism-rebuild skill will not be overwritten.")
    skill = (PACK_ROOT / "blueprints/omp/skills/prism-rebuild/SKILL.md.in").read_bytes()
    exclude_before = data["exclude"][0] or b""
    addition = b"\n# PRISM rebuild private state\n.prism-state/\n.prism-tools-venv/\n"
    desired = {"agents": agents + BLOCK, "skill": skill, "exclude": exclude_before + addition}
    changes = {}
    for key, after in desired.items():
        before, mode = data[key]
        changes[key] = {"beforeBase64": b64(before) if before is not None else None, "beforeSha256": digest(before) if before is not None else None, "beforeMode": mode, "afterBase64": b64(after), "afterSha256": digest(after)}
    receipt = {"schemaVersion": "1.0.0", "repository": str(root), "state": "installing", "createdAt": stamp(), "pack": info, "changes": changes}
    write_json(receipt_path, receipt)
    for key, after in desired.items():
        atomic_write(targets[key], after, data[key][1])
    receipt.update(state="installed", installedAt=stamp())
    write_json(receipt_path, receipt)
    emit({"status": "INSTALLED", "repository": str(root), "skill": "prism-rebuild", "note": "Only the rebuild skill is active. Product skill blueprints remain inactive until implemented."})

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        emit({"status": "BLOCKED", "error": str(exc)})
        sys.exit(2)
