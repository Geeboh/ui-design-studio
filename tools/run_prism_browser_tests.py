#!/usr/bin/env python3
"""Run PRISM dashboard browser tests and refresh a gate receipt."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest


code = pytest.main([str(ROOT / "tests/test_dashboard_browser.py"), "-q"])
receipt = ROOT / ".prism-state/m5-browser-gate.txt"
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(f"status: {'passed' if code == 0 else 'failed'}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")
raise SystemExit(code)
