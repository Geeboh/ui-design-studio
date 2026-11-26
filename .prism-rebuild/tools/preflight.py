#!/usr/bin/env python3
"""Read-only environment inventory. Does not install tools or print credentials."""
from __future__ import annotations
import argparse
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sqlite3
from prism_pack import PACK_ROOT, emit, git, repo_root, stamp

def version(binary):
    path = shutil.which(binary)
    if not path:
        return {"available": False}
    try:
        p = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=8)
        return {"available": True, "path": path, "exitCode": p.returncode, "version": (p.stdout or p.stderr).strip().splitlines()[:2]}
    except subprocess.TimeoutExpired:
        return {"available": True, "path": path, "version": "probe timed out"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--json", action="store_true", help="Output is always JSON; retained for explicit invocation")
    args = parser.parse_args()
    root = repo_root(args.repo)
    with sqlite3.connect(":memory:") as connection:
        sqlite_version, sqlite_source_id = connection.execute("SELECT sqlite_version(), sqlite_source_id()").fetchone()
    result = {"status": "INVENTORIED", "observedAt": stamp(), "repository": str(root), "commit": git(root, "rev-parse", "HEAD").decode().strip(), "branch": git(root, "branch", "--show-current").decode().strip(), "dirty": bool(git(root, "status", "--porcelain")), "python": {"version": platform.python_version(), "meetsPackMinimum": sys.version_info >= (3,10)}, "tools": {name: version(name) for name in ["git", "node", "npm", "omp"]}, "projectInstructions": (root / "AGENTS.md").is_file(), "liveCapabilities": {"playwright_fast": "DISCOVER_IN_OMP_SESSION", "subagents": "DISCOVER_IN_OMP_SESSION", "models": "DISCOVER_IN_OMP_SESSION", "browserEngines": "RUN_ACTUAL_BROWSER_SMOKE", "pricing": "UNKNOWN_UNTIL_VERIFIED"}, "note": "Tool presence is not evidence that runtime integration or browser actions work. No packages installed and no authentication values collected."}
    result["sqlite"] = {"libraryVersion": sqlite_version, "sourceId": sqlite_source_id, "interpreter": sys.executable, "scope": "This helper interpreter only. Recheck the installed product runtime and vendor patch provenance before selecting WAL; no product journal mode was changed."}
    emit(result)
    if not result["python"]["meetsPackMinimum"]:
        sys.exit(2)

if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        emit({"status": "BLOCKED", "error": str(exc)})
        sys.exit(2)
