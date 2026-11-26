#!/usr/bin/env python3
"""Run the M1 core acceptance file from a source checkout."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest


def record(status: str) -> None:
    path = ROOT / ".prism-state" / "m1-core-tests.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"status: {status}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")


code = pytest.main([str(ROOT / "tests/test_prism_core.py"), "-q"])
record("passed" if code == 0 else "failed")
raise SystemExit(code)
