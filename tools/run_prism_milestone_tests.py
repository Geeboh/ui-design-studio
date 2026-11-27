#!/usr/bin/env python3
"""Run one named PRISM milestone test from the repository checkout."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pytest


MILESTONES = {
    "test_prism_migration.py": "m2-tests.txt",
    "test_prism_m3.py": "m3-workflow-tests.txt",
    "test_prism_m4.py": "m4-governance-tests.txt",
}


def requested_test(argument: str) -> tuple[Path, str]:
    receipt_name = next(
        (receipt for name, receipt in MILESTONES.items() if argument == f"tests/{name}"),
        None,
    )
    if receipt_name is None:
        raise SystemExit(f"unsupported milestone test path: {argument}")
    test_path = ROOT / argument
    if test_path.is_symlink() or not test_path.is_file():
        raise SystemExit(f"missing repository milestone test: {argument}")
    return test_path, receipt_name


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: run_prism_milestone_tests.py TEST_PATH")
    test_path, receipt_name = requested_test(sys.argv[1])
    code = pytest.main([str(test_path), "-q"])
    state_root = ROOT / ".prism-state"
    if state_root.is_symlink():
        resolved = state_root.resolve(strict=False)
        expected = (ROOT / ".runtime" / "prism-state").resolve(strict=False)
        if resolved != expected or not resolved.is_relative_to(ROOT):
            raise SystemExit("unsafe milestone receipt directory")
        state_root = resolved
    elif state_root.exists() and not state_root.is_dir():
        raise SystemExit("unsafe milestone receipt directory")
    state_root.mkdir(parents=True, exist_ok=True)
    receipt = state_root / receipt_name
    if receipt.is_symlink() or (receipt.exists() and not receipt.is_file()):
        raise SystemExit("unsafe milestone receipt path")
    receipt.write_text(
        f"status: {'passed' if code == 0 else 'failed'}\n"
        f"observedAt: {datetime.now(timezone.utc).isoformat()}\n",
        encoding="utf-8",
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
