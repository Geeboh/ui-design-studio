#!/usr/bin/env python3
"""Run a named PRISM milestone test file from a source checkout."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest


if len(sys.argv) != 2:
    raise SystemExit("usage: run_prism_milestone_tests.py TEST_PATH")
test_name = Path(sys.argv[1]).name
receipt_name = {"test_prism_migration.py": "m2-tests.txt", "test_prism_m3.py": "m3-workflow-tests.txt", "test_prism_m4.py": "m4-governance-tests.txt"}.get(test_name)
if receipt_name is None:
    raise SystemExit(f"unsupported milestone test: {test_name}")
code = pytest.main([str(ROOT / sys.argv[1]), "-q"])
receipt = ROOT / ".prism-state" / receipt_name
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(f"status: {'passed' if code == 0 else 'failed'}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")
raise SystemExit(code)
