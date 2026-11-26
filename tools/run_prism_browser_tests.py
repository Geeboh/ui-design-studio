#!/usr/bin/env python3
"""Run PRISM dashboard browser tests and refresh a gate receipt."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
reports = []
code = 0
for engine in ("chromium", "firefox", "webkit"):
    environment = {**os.environ, "UI_DESIGN_TEST_ENGINE": engine}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "tests/test_dashboard_browser.py"), "-q"],
        cwd=ROOT, env=environment, text=True, capture_output=True, check=False,
    )
    reports.append(f"[{engine}]\n{result.stdout}{result.stderr}")
    code = code or result.returncode
receipt = ROOT / ".prism-state/m5-browser-gate.txt"
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(
    f"status: {'passed' if code == 0 else 'failed'}\n"
    f"observedAt: {datetime.now(timezone.utc).isoformat()}\n"
    "engines: chromium, firefox, webkit\n"
    + "\n".join(reports),
    encoding="utf-8",
)
sys.stdout.write("".join(reports))
raise SystemExit(code)
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(f"status: {'passed' if code == 0 else 'failed'}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")
raise SystemExit(code)
