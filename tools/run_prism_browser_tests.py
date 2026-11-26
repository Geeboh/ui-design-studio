#!/usr/bin/env python3
"""Run PRISM dashboard browser tests and refresh a gate receipt."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import sys
import re
ROOT = Path(__file__).resolve().parents[1]
reports = []
code = 0
for engine in ("chromium", "firefox", "webkit"):
    environment = {**os.environ, "UI_DESIGN_TEST_ENGINE": engine}
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "tests/test_dashboard_browser.py"), "-q"],
        cwd=ROOT, env=environment, text=True, capture_output=True, check=False,
    )
    report = f"[{engine}]\n{result.stdout}{result.stderr}"
    if result.returncode == 0 and not re.search(r"\b[1-9]\d* passed\b", result.stdout):
        result = subprocess.CompletedProcess(result.args, 1, result.stdout, result.stderr + "\nNo browser test passed; skipped-only execution is not release evidence.\n")
        report += "No browser test passed; skipped-only execution is not release evidence.\n"
    reports.append(report)
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
