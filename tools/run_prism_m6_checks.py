#!/usr/bin/env python3
"""Run M6 knowledge/theme tests and fixture performance measurement."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
environment = {**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")}
test = subprocess.run([sys.executable, "-m", "pytest", "tests/test_prism_m6.py", "-q"], cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
performance = subprocess.run([sys.executable, "tools/prism_performance.py", "--iterations", "50"], cwd=ROOT, env=environment, text=True, capture_output=True, check=False)
code = test.returncode or performance.returncode
receipt = ROOT / ".prism-state/m6-gate.txt"
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(f"status: {'passed' if code == 0 else 'failed'}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\ntests:\n{test.stdout}{test.stderr}\nperformance:\n{performance.stdout}{performance.stderr}", encoding="utf-8")
sys.stdout.write(test.stdout + performance.stdout)
sys.stderr.write(test.stderr + performance.stderr)
raise SystemExit(code)
