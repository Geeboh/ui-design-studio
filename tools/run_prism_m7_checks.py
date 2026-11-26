#!/usr/bin/env python3
"""Run isolated distribution, installation, host, and security checks."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest

files = [
    "tests/test_mcp_package.py",
    "tests/test_release_builder.py",
    "tests/test_install.py",
    "tests/test_global_mcp_install.py",
    "tests/test_mcp_dashboard.py",
]
code = pytest.main([str(ROOT / path) for path in files] + ["-q"])
host = subprocess.run(["node", "--test", "tests/test_progress_extension.mjs"], cwd=ROOT, text=True, capture_output=True, check=False)
code = code or host.returncode
try:
    live = subprocess.run([os.environ.get("PRISM_OMP_COMMAND", "omp"), "--no-session", "--mode", "rpc", "--max-time", "5", "--no-tools"], input="", cwd=ROOT, text=True, capture_output=True, timeout=15, check=False)
    live_ok = live.returncode == 0 and '"type":"ready"' in live.stdout and ("ui-design-studio" in live.stdout or "ui-design" in live.stdout)
except (OSError, subprocess.TimeoutExpired) as exc:
    live = None
    live_ok = False
    live_error = str(exc)
else:
    live_error = ""
code = code or (0 if live_ok else 1)
receipt = ROOT / ".prism-state/m7-gate.txt"
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(f"status: {'passed' if code == 0 else 'failed'}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\npytestStatus: {'passed' if code == 0 else 'failed'}\nhost:\n{host.stdout}{host.stderr}\nliveOmpStatus: {'passed' if live_ok else 'failed'}\nliveOmpError: {live_error}\nliveOmpOutput:\n{(live.stdout if live else '')[:20000]}\n", encoding="utf-8")
sys.stdout.write(host.stdout)
sys.stderr.write(host.stderr)
raise SystemExit(code)
