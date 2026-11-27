#!/usr/bin/env python3
"""Check current PRISM release artifacts and source manifest."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def artifacts() -> list[Path]:
    release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    version = release["version"]
    return [
        ROOT / f"dist/prism-v2/UI-Design-Studio-PRISM-v{version}.zip",
        ROOT / f"dist/prism-v2/ui_design_studio_mcp-{version}.tar.gz",
        ROOT / f"dist/prism-v2/ui_design_studio_mcp-{version}-py3-none-any.whl",
    ]


def verify_reproducible_artifacts(expected: list[Path]) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="prism-m8-") as directory:
        output = Path(directory)
        generated_zip = output / "candidate.zip"
        zip_result = subprocess.run(
            [sys.executable, "scripts/package_release.py", "--output", str(generated_zip)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        python_result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--sdist", "--no-isolation", "--outdir", str(output)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        if zip_result.returncode or python_result.returncode:
            return False, (zip_result.stdout + zip_result.stderr + python_result.stdout + python_result.stderr).strip()
        generated = [generated_zip, output / expected[1].name, output / expected[2].name]
        if any(not path.is_file() for path in generated):
            return False, f"Generated artifact missing: {[str(path) for path in generated if not path.is_file()]}"
        observed = [hashlib.sha256(path.read_bytes()).hexdigest() for path in generated]
        required = [hashlib.sha256(path.read_bytes()).hexdigest() for path in expected]
        if observed != required:
            return False, f"Artifact hashes differ. expected={required} observed={observed}"
        return True, "Rebuilt artifacts match the reviewed source bytes."


def main() -> int:
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    ).stdout.strip()
    manifest_sha256 = hashlib.sha256((ROOT / "MANIFEST.sha256").read_bytes()).hexdigest()
    expected = artifacts()
    missing = [str(path) for path in expected if not path.is_file()]
    manifest = subprocess.run(
        [sys.executable, "scripts/package_release.py", "--check"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    artifacts_ok, artifact_detail = (False, "Skipped because an expected artifact is missing.") if missing else verify_reproducible_artifacts(expected)
    checksums = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in expected if path.is_file()
    }
    code = manifest.returncode or bool(missing) or not artifacts_ok
    receipt = ROOT / ".prism-state/m8-gate.txt"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        f"status: {'passed' if code == 0 else 'failed'}\n"
        f"sourceCommit: {source_commit}\n"
        f"manifestSha256: {manifest_sha256}\n"
        f"missing: {missing}\n"
        f"artifacts: {'passed' if artifacts_ok else 'failed'}\n"
        f"artifactDetail: {artifact_detail}\n"
        f"manifest:\n{manifest.stdout}{manifest.stderr}\n"
        f"sha256: {checksums}\n",
        encoding="utf-8",
    )
    sys.stdout.write(receipt.read_text(encoding="utf-8"))
    return 1 if code else 0


if __name__ == "__main__":
    raise SystemExit(main())
