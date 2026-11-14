#!/usr/bin/env python3
"""Offline, transactional, project-local installer for UI Design Studio.

The shell entry point supplies a temporary venv. No third-party packages are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from dataclasses import dataclass

VERSION = "1.4.1"
PACKAGE = Path(__file__).resolve().parents[1]
STATE = ".ui-design-studio/install-state.json"
BACKUPS = ".ui-design-studio/backups"
START = b"<!-- ui-design-studio:start -->"
END = b"<!-- ui-design-studio:end -->"
IGNORE_START = b"# ui-design-studio:start"
IGNORE_END = b"# ui-design-studio:end"
SKILLS = {
    "ui-design-studio", "ui-assess", "ui-plan", "ui-design", "ui-produce",
    "ui-review", "ui-finalize", "ui-theme", "ui-yolo",
}
AGENTS_BLOCK = b"""<!-- ui-design-studio:start -->
## UI Design Studio

For UI assessments, redesigns, theme work, storyboards, mockups, and visual
implementation, read `.omp/skills/ui-design-studio/SKILL.md` and
`ui-design-studio.json`. Read the project's current instructions, requirements,
architecture, and implementation; derive constraints from those sources.
Use the existing project workflow and Git policy. No profile is required.
Start with `/skill:ui-design-studio mode=guided`, or explicitly request its
`mode=yolo` design mode. Resume the recorded run and preserve approved decisions.
Pass all relevant project constraints to every delegated worker; do not assume
that workers inherit this file. See `docs/ui-design-studio/README.md` and
`docs/ui-design-studio/RUN-TYPES.md` for normal and /goal run examples.
<!-- ui-design-studio:end -->"""
IGNORE_BLOCK = b"""# ui-design-studio:start
/.venv-ui-design/
/.ui-design-studio/backups/
/.ui-design-studio/model-routing/
/.ui-design-studio/runtime/mcp/
**/.design-server.json
**/.design-status.json
# ui-design-studio:end"""


class InstallError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode()


def safe_relative(raw: str) -> str:
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or any(x in ("", ".", "..") for x in raw.split("/")) or "\\" in raw:
        raise InstallError(f"Unsafe relative path: {raw!r}")
    return str(path)


def target_path(root: Path, relative: str) -> Path:
    relative = safe_relative(relative)
    current = root
    parts = PurePosixPath(relative).parts
    for i, part in enumerate(parts):
        current = current / part
        if current.is_symlink():
            raise InstallError(f"Refusing a symlinked managed path: {relative}")
        if current.exists() and i < len(parts) - 1 and not current.is_dir():
            raise InstallError(f"Managed parent is not a directory: {current}")
    if current.exists() and not current.is_file():
        raise InstallError(f"Managed destination is not a regular file: {relative}")
    return current


def ensure_plain_directory(root: Path, relative: str) -> Path:
    current = root
    for part in PurePosixPath(safe_relative(relative)).parts:
        current = current / part
        if current.is_symlink():
            raise InstallError(f"Refusing a symlinked directory: {current}")
        if current.exists() and not current.is_dir():
            raise InstallError(f"Expected a directory: {current}")
    return current


def read_existing(path: Path) -> tuple[bytes | None, int | None]:
    if not path.exists():
        return None, None
    if not path.is_file() or path.is_symlink():
        raise InstallError(f"Not a plain regular file: {path}")
    return path.read_bytes(), stat.S_IMODE(path.stat().st_mode)


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=".ui-design-write-", dir=str(path.parent))
    temp = Path(raw)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temp.chmod(mode)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def marked_block(existing: bytes, start: bytes, end: bytes, block: bytes) -> bytes:
    """Change only bytes inside inclusive markers; preserve all surrounding bytes."""
    starts, ends = existing.count(start), existing.count(end)
    if starts != ends or starts > 1:
        raise InstallError("Managed block markers are missing, duplicated, or unbalanced.")
    if not starts:
        gap = b"" if not existing else (b"\n" if existing.endswith(b"\n") else b"\n\n")
        return existing + gap + block + b"\n"
    a, b = existing.index(start), existing.index(end)
    if b < a:
        raise InstallError("Managed block end precedes its start.")
    return existing[:a] + block + existing[b + len(end):]


def default_config() -> dict:
    return {
        "schemaVersion": "1.0", "mode": "guided", "maxWorkers": 3,
        "modelPolicy": "auto-models",
        "paths": {"runs": "docs/design/runs", "themes": "themes"},
        "budgets": {
            "maxThemeRawBytes": 131072, "maxThemeGzipBytes": 40960,
            "addedRuntimeDependencies": 0, "remoteRuntimeRequests": 0,
        },
        "quality": {"target": "WCAG-2.2-AA", "touchTargetCssPx": 44},
        "git": {"branchPrefix": "design/", "autoCommit": False, "autoPush": False, "autoMerge": False},
        "autonomy": {"laterThemeAction": "new", "maxReviewIterations": 3},
    }


@dataclass
class Change:
    relative: str
    before: bytes | None
    before_mode: int | None
    after: bytes | None
    after_mode: int | None


def source_files() -> dict[str, tuple[bytes, int]]:
    files: dict[str, tuple[bytes, int]] = {}

    def include(source: Path, relative: str, executable: bool = False) -> None:
        if source.is_symlink() or not source.is_file():
            raise InstallError(f"Package source must be a plain file: {source}")
        for parent in source.parents:
            if parent == PACKAGE:
                break
            if parent.is_symlink():
                raise InstallError(f"Package source must not have a symlinked parent: {source}")
        files[safe_relative(relative)] = (source.read_bytes(), 0o755 if executable else 0o644)

    for name in sorted(SKILLS):
        folder = PACKAGE / ".omp" / "skills" / name
        if not folder.exists():
            raise InstallError(f"Incomplete package: missing skill {name}")
        if folder.is_symlink():
            raise InstallError(f"Package source must not be symlinked: {folder}")
        if not (folder / "SKILL.md").is_file():
            raise InstallError(f"Incomplete package: missing {name}/SKILL.md")
        for source in sorted(folder.rglob("*")):
            if source.is_symlink():
                raise InstallError(f"Package source must not be symlinked: {source}")
            if source.is_file() and "__pycache__" not in source.parts and source.suffix != ".pyc":
                include(source, source.relative_to(PACKAGE).as_posix(), source.suffix == ".sh")
    required = ".omp/skills/ui-design-studio/scripts/studio.py"
    if required not in files:
        raise InstallError(f"Incomplete package: missing {required}")
    agents = sorted((PACKAGE / ".omp" / "agents").glob("ui-*.md"))
    if not agents:
        raise InstallError("Incomplete package: no UI specialist agent definitions")
    for source in agents:
        include(source, source.relative_to(PACKAGE).as_posix())
    for name in ("ui-design", "ui-yolo"):
        source = PACKAGE / ".omp" / "commands" / f"{name}.md"
        if not source.exists():
            raise InstallError(f"Incomplete package: missing command {name}")
        include(source, source.relative_to(PACKAGE).as_posix())
    extension = PACKAGE / ".omp" / "extensions" / "ui-design-progress.ts"
    if extension.exists() or extension.is_symlink():
        include(extension, extension.relative_to(PACKAGE).as_posix())
    for tree, destination in (("docs", "docs/ui-design-studio"), ("prompts", "docs/ui-design-studio/prompts")):
        source_root = PACKAGE / tree
        if source_root.exists():
            for source in sorted(source_root.rglob("*")):
                if source.is_symlink():
                    raise InstallError(f"Package source must not be symlinked: {source}")
                if source.is_file():
                    include(source, f"{destination}/{source.relative_to(source_root).as_posix()}")
    if (PACKAGE / "README.md").is_file():
        include(PACKAGE / "README.md", "docs/ui-design-studio/README.md")
        # The archive README sits above docs/, but its installed copy sits
        # beside those documents. Adjust only authored relative doc links.
        data, mode = files["docs/ui-design-studio/README.md"]
        files["docs/ui-design-studio/README.md"] = (data.replace(b"](docs/", b"]("), mode)
    for name in ("LICENSE.txt", "release.json"):
        if (PACKAGE / name).exists():
            include(PACKAGE / name, "docs/ui-design-studio/" + name)
    include(PACKAGE / "tools" / "ui-design", "tools/ui-design", executable=True)
    return files


def load_state(root: Path) -> dict:
    path = target_path(root, STATE)
    if not path.exists():
        return {"managedFiles": {}}
    try:
        state = json.loads(path.read_text())
        if state.get("package") != "ui-design-studio" or not isinstance(state.get("managedFiles"), dict):
            raise ValueError("not UI Design Studio state")
        for key in state["managedFiles"]:
            safe_relative(key)
        return state
    except (ValueError, TypeError, AttributeError) as exc:
        raise InstallError(f"Invalid install state at {STATE}: {exc}") from exc


def install_plan(root: Path, update: bool) -> tuple[list[Change], dict[str, tuple[bytes, int]]]:
    if target_path(root, ".ui-design-studio/model-routing/active.json").exists():
        raise InstallError("Temporary model routing is active. Run tools/ui-design models-restore --repo <project> --run <run-directory> before installing or updating the package.")
    payload = source_files()
    state = load_state(root)
    owned = state["managedFiles"]
    changes: list[Change] = []
    conflicts: list[str] = []
    for relative, (data, source_mode) in payload.items():
        path = target_path(root, relative)
        before, mode = read_existing(path)
        after_mode = source_mode
        if before == data and mode == after_mode:
            continue
        if before is not None:
            if relative not in owned:
                conflicts.append(f"{relative}: existing content was not installed by this package")
            else:
                previous = owned[relative]
                if not isinstance(previous, dict) or digest(before) != previous.get("sha256") or mode != previous.get("mode"):
                    conflicts.append(f"{relative}: managed file was edited since installation; preserve or reconcile it before updating")
                elif not update:
                    conflicts.append(f"{relative}: use --update to replace a previously installed file")
        changes.append(Change(relative, before, mode, data, after_mode))
    # Retire only previously managed, byte-identical files. Modified obsolete
    # files are a conflict, never silently discarded. The normal transaction
    # backs up removals and can restore them.
    for relative in sorted(set(owned) - set(payload)):
        before, mode = read_existing(target_path(root, relative))
        if before is None:
            continue
        previous = owned[relative]
        if not isinstance(previous, dict) or digest(before) != previous.get("sha256") or mode != previous.get("mode"):
            conflicts.append(f"{relative}: obsolete managed file was edited; preserve or relocate it before updating")
        elif not update:
            conflicts.append(f"{relative}: use --update to retire an obsolete package file")
        else:
            changes.append(Change(relative, before, mode, None, None))
    for relative, start, end, block in (
        ("AGENTS.md", START, END, AGENTS_BLOCK),
        (".gitignore", IGNORE_START, IGNORE_END, IGNORE_BLOCK),
    ):
        before, mode = read_existing(target_path(root, relative))
        after = marked_block(before or b"", start, end, block)
        if before == after:
            continue
        if before and start in before and not update:
            conflicts.append(f"{relative}: existing managed block differs; use --update")
        changes.append(Change(relative, before, mode, after, mode if mode is not None else 0o644))
    config_path = target_path(root, "ui-design-studio.json")
    if not config_path.exists():
        changes.append(Change("ui-design-studio.json", None, None, json_bytes(default_config()), 0o644))
    new_state = {
        "schemaVersion": 1, "package": "ui-design-studio", "version": VERSION,
        "managedFiles": {rel: {"sha256": digest(data), "mode": mode} for rel, (data, mode) in sorted(payload.items())},
    }
    before, mode = read_existing(target_path(root, STATE))
    after = json_bytes(new_state)
    if before != after:
        changes.append(Change(STATE, before, mode, after, mode if mode is not None else 0o644))
    ensure_plain_directory(root, BACKUPS)
    ensure_plain_directory(root, ".venv-ui-design")
    if conflicts:
        raise InstallError("Installation conflicts; no project files changed:\n  " + "\n  ".join(conflicts))
    return changes, payload


def require_unchanged(root: Path, changes: list[Change]) -> None:
    for change in changes:
        data, mode = read_existing(target_path(root, change.relative))
        if data != change.before or mode != change.before_mode:
            raise InstallError(f"File changed after preflight: {change.relative}")


def missing_parent_directories(root: Path, paths: list[str]) -> list[str]:
    missing: set[str] = set()
    for relative in paths:
        parent = (root / relative).parent
        while parent != root:
            if not parent.exists():
                missing.add(parent.relative_to(root).as_posix())
            parent = parent.parent
    return sorted(missing, key=lambda x: (len(PurePosixPath(x).parts), x))


def cleanup_empty_directories(root: Path, relatives: list[str]) -> None:
    for relative in sorted(relatives, key=lambda x: len(PurePosixPath(x).parts), reverse=True):
        directory = root / safe_relative(relative)
        if directory.is_symlink():
            continue
        try:
            directory.rmdir()
        except OSError:
            pass


def apply_changes(root: Path, changes: list[Change]) -> None:
    applied: list[Change] = []
    parents = missing_parent_directories(root, [c.relative for c in changes])
    try:
        for change in changes:
            path = target_path(root, change.relative)
            # Recheck just before writing as well as before creating any backup.
            before, mode = read_existing(path)
            if before != change.before or mode != change.before_mode:
                raise InstallError(f"File changed during installation: {change.relative}")
            if change.after is None:
                path.unlink()
            else:
                atomic_write(path, change.after, change.after_mode if change.after_mode is not None else 0o644)
            applied.append(change)
    except BaseException:
        for change in reversed(applied):
            path = root / change.relative
            if change.before is None:
                if path.exists():
                    path.unlink()
            else:
                atomic_write(path, change.before, change.before_mode if change.before_mode is not None else 0o644)
        cleanup_empty_directories(root, parents)
        raise


def reverse_changes(changes: list[Change]) -> list[Change]:
    return [Change(c.relative, c.after, c.after_mode, c.before, c.before_mode) for c in reversed(changes)]


def ensure_venv(root: Path) -> bool:
    target = ensure_plain_directory(root, ".venv-ui-design")
    python = target / "bin" / "python"
    if target.exists():
        if not (target / "pyvenv.cfg").is_file() or not python.is_file() or not os.access(python, os.X_OK):
            raise InstallError("Existing .venv-ui-design is incomplete. Repair or move it before installing.")
        return False
    try:
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(target)], check=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        import shutil
        if target.exists():
            shutil.rmtree(target)
        raise InstallError(f"Unable to create project venv: {exc}") from exc
    return True


def install(root: Path, update: bool, dry_run: bool) -> None:
    changes, payload = install_plan(root, update)
    venv = root / ".venv-ui-design"
    if venv.exists() and (not (venv / "pyvenv.cfg").is_file() or not (venv / "bin" / "python").is_file() or not os.access(venv / "bin" / "python", os.X_OK)):
        raise InstallError("Existing .venv-ui-design is incomplete. Repair or move it before installing.")
    if dry_run:
        print(f"Dry run: {len(changes)} file changes in {root}")
        for change in changes:
            print(f"  {'REMOVE' if change.after is None else 'CREATE' if change.before is None else 'UPDATE'} {change.relative}")
        print("  VENV " + ("reuse .venv-ui-design" if venv.exists() else "create .venv-ui-design"))
        print("No project files were changed.")
        return
    require_unchanged(root, changes)
    created_venv = ensure_venv(root)
    if not changes:
        print(f"UI Design Studio {VERSION} is already installed; no package files changed.")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_id = f"{stamp}-{secrets.token_hex(4)}"
    backup = ensure_plain_directory(root, f"{BACKUPS}/{backup_id}")
    parents = missing_parent_directories(root, [c.relative for c in changes])
    entries = []
    applied = False
    try:
        backup.mkdir(parents=True, mode=0o700)
        for change in changes:
            entry = {
                "path": change.relative,
                "action": "remove" if change.after is None else "create" if change.before is None else "replace",
                "previousSha256": None if change.before is None else digest(change.before),
                "previousMode": change.before_mode,
                "installedSha256": None if change.after is None else digest(change.after),
                "installedMode": change.after_mode,
            }
            if change.before is not None:
                stored = "files/" + change.relative
                atomic_write(backup / stored, change.before, 0o600)
                entry["backupPath"] = stored
            entries.append(entry)
        manifest = {
            "schemaVersion": 1, "package": "ui-design-studio", "version": VERSION,
            "projectRoot": str(root), "backupId": backup_id, "createdAt": stamp,
            "status": "prepared", "files": entries, "createdDirectories": parents,
            "venvCreated": created_venv,
        }
        atomic_write(backup / "manifest.json", json_bytes(manifest), 0o600)
        require_unchanged(root, changes)
        apply_changes(root, changes)
        applied = True
        manifest["status"] = "installed"
        atomic_write(backup / "manifest.json", json_bytes(manifest), 0o600)
    except BaseException:
        if applied:
            apply_changes(root, reverse_changes(changes))
            cleanup_empty_directories(root, parents)
        if created_venv:
            import shutil
            shutil.rmtree(venv, ignore_errors=True)
        if backup.exists():
            # A prepared manifest is retained for diagnosis if file application failed.
            print(f"Installation did not complete. Backup record: {backup / 'manifest.json'}", file=sys.stderr)
        raise
    print(f"Installed UI Design Studio {VERSION}: {len(changes)} file changes in {root}")
    print(f"Backup ID: {backup_id}")
    print("Existing ui-design-studio.json was preserved when present; no OMP config.yml was changed.")
    print("Next: ./tools/ui-design doctor --repo .; in OMP run /reload-plugins, then /skill:ui-design-studio mode=guided")


def restore(root: Path, backup_id: str, dry_run: bool) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", backup_id):
        raise InstallError("Backup ID must be a simple directory name, not a path.")
    backup = ensure_plain_directory(root, f"{BACKUPS}/{backup_id}")
    manifest_path = target_path(root, f"{BACKUPS}/{backup_id}/manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, ValueError) as exc:
        raise InstallError(f"Unable to read backup manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("package") != "ui-design-studio" or manifest.get("backupId") != backup_id:
        raise InstallError("Backup manifest does not identify this package and backup.")
    if manifest.get("projectRoot") != str(root):
        raise InstallError("Backup belongs to a different project path; automatic restore refused.")
    if manifest.get("status") == "restored":
        print(f"Backup {backup_id} has already been restored; no files changed.")
        return
    if manifest.get("status") != "installed" or not isinstance(manifest.get("files"), list):
        raise InstallError("Backup does not describe a completed installation.")
    created_directories = manifest.get("createdDirectories", [])
    if not isinstance(created_directories, list) or any(not isinstance(x, str) for x in created_directories):
        raise InstallError("Malformed backup directory records.")
    for directory in created_directories:
        safe_relative(directory)
        ensure_plain_directory(root, directory)
    changes: list[Change] = []
    conflicts: list[str] = []
    seen: set[str] = set()
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise InstallError("Malformed backup file record.")
        relative = safe_relative(entry["path"])
        if relative in seen or relative.startswith(BACKUPS + "/") or relative.startswith(".venv-ui-design/"):
            raise InstallError(f"Invalid or repeated backup destination: {relative}")
        seen.add(relative)
        before, mode = read_existing(target_path(root, relative))
        is_removal = entry.get("action") == "remove"
        if (is_removal and before is not None) or (not is_removal and (before is None or digest(before) != entry.get("installedSha256") or mode != entry.get("installedMode"))):
            conflicts.append(relative)
            continue
        after, after_mode = None, None
        if entry.get("action") in ("replace", "remove"):
            stored = safe_relative(entry.get("backupPath", ""))
            if stored != "files/" + relative:
                raise InstallError(f"Incorrect stored backup path: {relative}")
            source = target_path(backup, stored)
            after = source.read_bytes()
            if digest(after) != entry.get("previousSha256"):
                raise InstallError(f"Backup content hash mismatch: {relative}")
            after_mode = entry.get("previousMode")
            if not isinstance(after_mode, int) or not 0 <= after_mode <= 0o7777:
                raise InstallError(f"Invalid backup permissions: {relative}")
        elif entry.get("action") != "create":
            raise InstallError(f"Unknown backup action: {relative}")
        changes.append(Change(relative, before, mode, after, after_mode))
    if conflicts:
        raise InstallError("Restore refused; these files changed or disappeared since installation:\n  " + "\n  ".join(conflicts) + "\nNo project files were changed.")
    if dry_run:
        print(f"Dry run: restore {backup_id}; {len(changes)} file changes")
        for change in changes:
            print(f"  {'REMOVE' if change.after is None else 'RESTORE'} {change.relative}")
        print("No project files were changed. The virtual environment and backups are retained.")
        return
    require_unchanged(root, changes)
    apply_changes(root, changes)
    manifest["status"] = "restored"
    manifest["restoredAt"] = datetime.now(timezone.utc).isoformat()
    try:
        atomic_write(manifest_path, json_bytes(manifest), 0o600)
    except BaseException:
        apply_changes(root, reverse_changes(changes))
        raise
    cleanup_empty_directories(root, created_directories)
    print(f"Restored {backup_id}: {len(changes)} file changes.")
    print("The virtual environment and backup records were retained.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Absolute path to an existing project directory")
    parser.add_argument("--profile", choices=("tada", "generic"), default=None, help=argparse.SUPPRESS)
    parser.add_argument("--update", action="store_true", help="Update previously installed files, with backups")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without changing the project")
    parser.add_argument("--restore", metavar="BACKUP_ID", help="Restore an installation backup; edited files block restore")
    args = parser.parse_args(argv)
    if sys.prefix == sys.base_prefix:
        parser.error("Run ./install.sh, which bootstraps a virtual environment; do not run this with system Python.")
    project = Path(args.project).expanduser()
    if not project.is_absolute() or not project.is_dir():
        parser.error("--project must be an absolute path to an existing directory")
    root = project.resolve()
    if root == PACKAGE or PACKAGE in root.parents:
        parser.error("Choose a project outside the extracted package directory")
    if args.restore and args.update:
        parser.error("--restore and --update cannot be combined")
    if args.profile is not None:
        print("NOTICE: --profile is deprecated and ignored; the designer reads requirements from the project.", file=sys.stderr)
    try:
        if args.restore:
            restore(root, args.restore, args.dry_run)
        else:
            install(root, args.update, args.dry_run)
    except (InstallError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
