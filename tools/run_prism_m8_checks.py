#!/usr/bin/env python3
"""Check current PRISM 2.0.0 artifacts and source manifest."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
artifacts = [
    ROOT / "dist/prism-v2/UI-Design-Studio-PRISM-v2.0.0.zip",
    ROOT / "dist/prism-v2/ui_design_studio_mcp-2.0.0.tar.gz",
    ROOT / "dist/prism-v2/ui_design_studio_mcp-2.0.0-py3-none-any.whl",
]
missing = [str(path) for path in artifacts if not path.is_file()]
manifest = subprocess.run([sys.executable, "scripts/package_release.py", "--check"], cwd=ROOT, text=True, capture_output=True, check=False)
checksums = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts if path.is_file()}
code = manifest.returncode or bool(missing)
receipt = ROOT / ".prism-state/m8-gate.txt"
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(f"status: {'passed' if code == 0 else 'failed'}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\nmissing: {missing}\nmanifest:\n{manifest.stdout}{manifest.stderr}\nsha256: {checksums}\n", encoding="utf-8")
sys.stdout.write(receipt.read_text(encoding="utf-8"))
raise SystemExit(1 if code else 0)
