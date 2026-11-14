#!/usr/bin/env python3
"""Build a reproducible, dependency-free distribution ZIP from reviewed sources.

Run through a virtual environment. This is a release-maintainer utility, not
the project theme packager. It does not publish or upload anything.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TREES = (".omp/agents", ".omp/commands", ".omp/extensions", ".omp/skills", "docs", "prompts", "scripts", "tests", "tools", "examples", "src")
TOP = ("README.md", "LICENSE.txt", "install.sh", "release.json", "pyproject.toml", "hatch_build.py")
SKIP = {"__pycache__", ".git", ".DS_Store", "node_modules"}
EXECUTABLE = {"install.sh", "tools/ui-design"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sources() -> list[Path]:
    paths = [ROOT / name for name in TOP]
    for name in TREES:
        directory = ROOT / name
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(f"Missing/plain source tree required: {name}")
        for path in directory.rglob("*"):
            relative = path.relative_to(ROOT)
            if any(part in SKIP or part.startswith(".venv") for part in relative.parts):
                continue
            if path.suffix in (".pyc", ".pyo"):
                continue
            if path.is_symlink():
                raise ValueError(f"Symlink is not distributable: {relative}")
            if path.is_file():
                paths.append(path)
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Missing/plain source file required: {path.relative_to(ROOT)}")
        if any(part in (".env", "credentials", ".ui-design-studio") for part in path.relative_to(ROOT).parts):
            raise ValueError("Runtime/private state must not enter a release")
    return sorted(set(paths), key=lambda path: path.relative_to(ROOT).as_posix())


def manifest(paths: list[Path]) -> str:
    return "".join(f"{sha(path.read_bytes())}  {path.relative_to(ROOT).as_posix()}\n" for path in paths)


def build(output: Path, check: bool = False) -> dict:
    release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
    paths = sources()
    if len(list((ROOT / ".omp/skills").glob("*/SKILL.md"))) != release["skillCount"]:
        raise ValueError("Skill count does not match release.json")
    if len(list((ROOT / ".omp/agents").glob("ui-*.md"))) != release["agentCount"]:
        raise ValueError("Agent count does not match release.json")
    expected = manifest(paths)
    checksum_path = ROOT / "MANIFEST.sha256"
    if check:
        if not checksum_path.is_file() or checksum_path.read_text(encoding="utf-8") != expected:
            raise ValueError("MANIFEST.sha256 is missing or stale")
        return {"status": "PASS", "filesVerified": len(paths), "version": release["version"]}
    if checksum_path.is_symlink():
        raise ValueError("Refusing symlinked manifest")
    checksum_path.write_text(expected, encoding="utf-8")
    paths.append(checksum_path)
    paths.sort(key=lambda path: path.relative_to(ROOT).as_posix())
    prefix = f"ui-design-studio-v{release['version']}"
    release_day = dt.date.fromisoformat(release["releaseDate"])
    timestamp = (release_day.year, release_day.month, release_day.day, 0, 0, 0)
    output = output.absolute()
    if output.suffix.lower() != ".zip":
        raise ValueError("Release output must end in .zip")
    if output.is_symlink() or output in paths:
        raise ValueError("Refusing to replace a source file or symlink")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".ui-release-", suffix=".zip", dir=output.parent)
    os.close(fd)
    temp_path = Path(temporary)
    try:
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in paths:
                relative = path.relative_to(ROOT).as_posix()
                info = zipfile.ZipInfo(f"{prefix}/{relative}", date_time=timestamp)
                info.create_system = 3
                mode = 0o755 if relative in EXECUTABLE or path.suffix == ".sh" else 0o644
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        with zipfile.ZipFile(temp_path) as archive:
            damaged = archive.testzip()
            if damaged:
                raise ValueError(f"ZIP CRC failed: {damaged}")
            for path in paths:
                relative = path.relative_to(ROOT).as_posix()
                if archive.read(f"{prefix}/{relative}") != path.read_bytes():
                    raise ValueError(f"ZIP content mismatch: {relative}")
        os.replace(temp_path, output)
    finally:
        temp_path.unlink(missing_ok=True)
    digest = sha(output.read_bytes())
    sidecar = output.with_name(output.name + ".sha256")
    if sidecar.is_symlink():
        raise ValueError("Refusing symlinked ZIP checksum")
    sidecar.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    return {"status": "PASS", "version": release["version"], "files": len(paths),
            "bytes": output.stat().st_size, "sha256": digest, "archive": str(output),
            "checksum": str(sidecar)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/UI-Design-Studio-OMP-v1.4.1.zip")
    parser.add_argument("--check", action="store_true", help="Check source hashes without building")
    args = parser.parse_args()
    if sys.prefix == sys.base_prefix:
        parser.error("Use a virtual environment; see docs/DISTRIBUTION.md")
    try:
        print(json.dumps(build(args.output, args.check), indent=2))
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
