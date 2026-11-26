#!/usr/bin/env python3
"""Run M0 preflight/fingerprint checks and refresh their evidence receipts."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
mode = sys.argv[1] if len(sys.argv) == 2 else ""
if mode == "preflight":
    command = [sys.executable, str(ROOT / ".prism-rebuild/tools/preflight.py"), "--repo", str(ROOT), "--json"]
    receipt = ROOT / ".prism-state/m0-preflight.txt"
elif mode == "fingerprint":
    command = [sys.executable, str(ROOT / ".prism-rebuild/tools/run-gates.py"), "--repo", str(ROOT), "--fingerprint"]
    receipt = ROOT / ".prism-state/m0-fingerprint.txt"
else:
    raise SystemExit("usage: run_prism_m0_checks.py preflight|fingerprint")
result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(f"mode: {mode}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\nexitCode: {result.returncode}\n{result.stdout}", encoding="utf-8")
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
raise SystemExit(result.returncode)
