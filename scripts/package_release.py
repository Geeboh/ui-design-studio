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
REBUILD_CONTEXT = Path(".omp/skills/prism-rebuild")
RUNTIME_DIRECTORIES = {Path("docs/design/runs")}
RUNTIME_FILES = {".design-server.json", ".design-status.json", ".design-owner.json",
                 ".design-server.lock", ".design-records.lock", ".design-theme-sources.json"}
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
            if relative == REBUILD_CONTEXT or REBUILD_CONTEXT in relative.parents:
                continue
            if any(relative == runtime or runtime in relative.parents for runtime in RUNTIME_DIRECTORIES):
                continue
            if path.name in RUNTIME_FILES:
                continue
            if (any(part.startswith(".env.") for part in relative.parts[:-1])
                    or (path.name.startswith(".env.") and path.name != ".env.example")):
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
    if len([path for path in (ROOT / ".omp/skills").glob("*/SKILL.md") if path.parent.name != "prism-rebuild"]) != release["skillCount"]:
        raise ValueError("Skill count does not match release.json")
    if len(list((ROOT / ".omp/agents").glob("ui-*.md"))) != release["agentCount"]:
        raise ValueError("Agent count does not match release.json")
    expected = manifest(paths)
    checksum_path = ROOT / "MANIFEST.sha256"
    if checksum_path.is_symlink() or (checksum_path.exists() and not checksum_path.is_file()):
        raise ValueError("Refusing non-regular manifest")
    if check:
        if not checksum_path.is_file() or checksum_path.read_text(encoding="utf-8") != expected:
            raise ValueError("MANIFEST.sha256 is missing or stale")
        return {"status": "PASS", "filesVerified": len(paths), "version": release["version"]}
    output = output.absolute()
    if output.suffix.lower() != ".zip":
        raise ValueError("Release output must end in .zip")
    sidecar = output.with_name(output.name + ".sha256")
    source_trees = tuple((ROOT / name).resolve() for name in TREES)
    for destination in (output, sidecar):
        if destination.is_symlink() or (destination.exists() and not destination.is_file()):
            raise ValueError(f"Release destination must be a plain file: {destination}")
        resolved = destination.resolve()
        if resolved in paths or resolved == checksum_path or any(resolved.is_relative_to(tree) for tree in source_trees):
            raise ValueError("Release destination must be outside packaged sources")
    for parent in output.parents:
        if (parent.exists() or parent.is_symlink()) and not parent.is_dir():
            raise ValueError(f"Release output parent must be a directory: {parent}")
    output.parent.mkdir(parents=True, exist_ok=True)
    expected_manifest = expected.encode("utf-8")
    paths.append(checksum_path)
    paths.sort(key=lambda path: path.relative_to(ROOT).as_posix())
    def content(path):
        return expected_manifest if path == checksum_path else path.read_bytes()
    prefix = f"ui-design-studio-v{release['version']}"
    release_day = dt.date.fromisoformat(release["releaseDate"])
    timestamp = (release_day.year, release_day.month, release_day.day, 0, 0, 0)
    fd, temporary = tempfile.mkstemp(prefix=".ui-release-", suffix=".zip", dir=output.parent)
    os.close(fd)
    temp_path = Path(temporary)
    manifest_fd, temporary_manifest = tempfile.mkstemp(prefix=".ui-manifest-", dir=ROOT)
    manifest_temp = Path(temporary_manifest)
    checksum_temp = None
    archive_backup = None
    manifest_backup = None
    try:
        with os.fdopen(manifest_fd, "wb") as handle:
            handle.write(expected_manifest)
            handle.flush()
            os.fsync(handle.fileno())
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in paths:
                relative = path.relative_to(ROOT).as_posix()
                info = zipfile.ZipInfo(f"{prefix}/{relative}", date_time=timestamp)
                info.create_system = 3
                mode = 0o755 if relative in EXECUTABLE or path.suffix == ".sh" else 0o644
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, content(path), compresslevel=9)
        with zipfile.ZipFile(temp_path) as archive:
            damaged = archive.testzip()
            if damaged:
                raise ValueError(f"ZIP CRC failed: {damaged}")
            for path in paths:
                relative = path.relative_to(ROOT).as_posix()
                if archive.read(f"{prefix}/{relative}") != content(path):
                    raise ValueError(f"ZIP content mismatch: {relative}")
        digest = sha(temp_path.read_bytes())
        checksum_fd, temporary_checksum = tempfile.mkstemp(prefix=".ui-checksum-", dir=output.parent)
        checksum_temp = Path(temporary_checksum)
        with os.fdopen(checksum_fd, "w", encoding="utf-8") as handle:
            handle.write(f"{digest}  {output.name}\n")
            handle.flush()
            os.fsync(handle.fileno())
        if output.exists():
            backup_fd, temporary_backup = tempfile.mkstemp(prefix=".ui-release-backup-", dir=output.parent)
            os.close(backup_fd)
            archive_backup = Path(temporary_backup)
            archive_backup.unlink()
            os.link(output, archive_backup, follow_symlinks=False)
        if checksum_path.exists():
            manifest_fd, temporary_backup = tempfile.mkstemp(prefix=".ui-manifest-backup-", dir=ROOT)
            os.close(manifest_fd)
            manifest_backup = Path(temporary_backup)
            manifest_backup.unlink()
            os.link(checksum_path, manifest_backup, follow_symlinks=False)
        archive_published = False
        manifest_published = False
        try:
            os.replace(temp_path, output)
            archive_published = True
            os.replace(manifest_temp, checksum_path)
            manifest_published = True
            os.replace(checksum_temp, sidecar)
        except BaseException:
            if manifest_published:
                if manifest_backup is not None:
                    os.replace(manifest_backup, checksum_path)
                else:
                    checksum_path.unlink()
            if archive_published:
                if archive_backup is not None:
                    os.replace(archive_backup, output)
                else:
                    output.unlink()
            raise
        else:
            if archive_backup is not None:
                archive_backup.unlink()
            if manifest_backup is not None:
                manifest_backup.unlink()
    finally:
        temp_path.unlink(missing_ok=True)
        manifest_temp.unlink(missing_ok=True)
        if checksum_temp is not None:
            checksum_temp.unlink(missing_ok=True)
        if archive_backup is not None:
            archive_backup.unlink(missing_ok=True)
        if manifest_backup is not None:
            manifest_backup.unlink(missing_ok=True)
    return {"status": "PASS", "version": release["version"], "files": len(paths),
            "bytes": output.stat().st_size, "sha256": digest, "archive": str(output),
            "checksum": str(sidecar)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/PRISM-Studio-2.0.10.zip")
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
