#!/usr/bin/env python3
"""Check current PRISM release artifacts and source manifest."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def artifacts() -> list[Path]:
    release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    version = release["version"]
    return [
        ROOT / f"dist/prism-v2/UI-Design-Studio-PRISM-v{version}.zip",
        ROOT / f"dist/prism-v2/ui_design_studio_mcp-{version}.tar.gz",
        ROOT / f"dist/prism-v2/ui_design_studio_mcp-{version}-py3-none-any.whl",
    ]


def main() -> int:
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    ).stdout.strip()
    manifest_sha256 = hashlib.sha256((ROOT / "MANIFEST.sha256").read_bytes()).hexdigest()
    expected = artifacts()
    missing = [str(path) for path in expected if not path.is_file()]
    manifest = subprocess.run(
        [sys.executable, "scripts/package_release.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    checksums = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in expected if path.is_file()
    }
    code = manifest.returncode or bool(missing)
    receipt = ROOT / ".prism-state/m8-gate.txt"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        f"status: {'passed' if code == 0 else 'failed'}\n"
        f"sourceCommit: {source_commit}\n"
        f"manifestSha256: {manifest_sha256}\n"
        f"missing: {missing}\n"
        f"manifest:\n{manifest.stdout}{manifest.stderr}\n"
        f"sha256: {checksums}\n",
        encoding="utf-8",
    )
    sys.stdout.write(receipt.read_text(encoding="utf-8"))
    return 1 if code else 0


if __name__ == "__main__":
    raise SystemExit(main())
