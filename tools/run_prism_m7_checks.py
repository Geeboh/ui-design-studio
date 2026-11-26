#!/usr/bin/env python3
"""Run isolated distribution, installation, host, and security checks."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
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
receipt = ROOT / ".prism-state/m7-gate.txt"
receipt.parent.mkdir(parents=True, exist_ok=True)
receipt.write_text(f"status: {'passed' if code == 0 else 'failed'}\nobservedAt: {datetime.now(timezone.utc).isoformat()}\n", encoding="utf-8")
raise SystemExit(code)
