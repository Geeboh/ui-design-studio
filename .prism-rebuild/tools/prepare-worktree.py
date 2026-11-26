#!/usr/bin/env python3
"""Create an isolated, reviewable rebuild workspace; never reset the source."""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from prism_pack import PACK_ROOT, SKIP_PARTS, emit, git, repo_root, stamp, state_path, verify_manifest, write_json

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--dest", required=True)
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--branch", default="overhaul/prism-v2")
    args = parser.parse_args()
    repo = repo_root(args.repo)
    dest = Path(args.dest).expanduser().resolve(strict=False)
    if dest.exists() or dest.is_symlink():
        raise ValueError("Destination already exists. Choose a new sibling directory; no files were replaced.")
    if dest.is_relative_to(repo) or repo.is_relative_to(dest):
        raise ValueError("Use a separate sibling worktree, outside the source repository.")
    if args.base.startswith("-"):
        raise ValueError("A Git revision cannot start with '-'")
    git(repo, "check-ref-format", "--branch", args.branch)
    info = verify_manifest(PACK_ROOT)
    base = git(repo, "rev-parse", "--verify", args.base + "^{commit}").decode().strip()
    source_dirty = bool(git(repo, "status", "--porcelain"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "-b", args.branch, str(dest), base)
    target = dest / ".prism-rebuild"
    try:
        prepare_receipt = state_path(dest, "prepare.json")
        if prepare_receipt.exists():
            raise ValueError("An existing prepare receipt is not owned by this preparation; no state was replaced")
        shutil.copytree(PACK_ROOT, target, ignore=lambda directory, names: [n for n in names if n in SKIP_PARTS or n.endswith((".pyc", ".pyo"))])
        verify_manifest(target)
        receipt = {"schemaVersion": "1.0.0", "operation": "prepare-worktree", "createdAt": stamp(), "sourceRepository": str(repo), "repository": str(dest), "branch": args.branch, "baseCommit": base, "sourceHadUncommittedChanges": source_dirty, "sourceUncommittedChangesIncluded": False, "pack": info}
        write_json(prepare_receipt, receipt)
        result = subprocess.run([sys.executable, str(target / "tools" / "install-rebuild-context.py"), "--repo", str(dest)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError(f"Worktree and pack created, but context installation needs attention: {result.stderr or result.stdout}")
        emit({"status": "PREPARED", **receipt, "context": "installed", "next": f"Read {target / 'START-HERE.md'}", "note": "The original working files were not reset, stashed, cleaned, or edited. Only the selected committed revision is in this worktree; Git worktree metadata and local excludes are recorded separately."})
    except Exception as exc:
        raise ValueError(f"Preparation stopped. Preserve and inspect {dest}; no automatic destructive cleanup was attempted. {exc}") from exc

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        emit({"status": "BLOCKED", "error": str(exc)})
        sys.exit(2)
