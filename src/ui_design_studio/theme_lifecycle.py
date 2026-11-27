"""Versioned theme installation, activation, and conflict-aware restore."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any


class ThemeLifecycleError(RuntimeError):
    """Theme lifecycle operation failed without overwriting user-owned bytes."""


_THEME_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _validate_id(value: str, label: str) -> str:
    if not isinstance(value, str) or not _THEME_ID.fullmatch(value):
        raise ThemeLifecycleError(f"{label} must be an ASCII bounded identifier")
    return value
def _validate_scope(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 128 or "\x00" in value:
        raise ThemeLifecycleError("Theme scope must be a bounded string")
    return value


def _absolute_without_symlinks(value: str | os.PathLike[str]) -> Path:
    raw = Path(os.path.abspath(os.path.expanduser(os.fspath(value))))
    current = Path(raw.anchor)
    for part in raw.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ThemeLifecycleError(f"Path contains a symlink ancestor: {current}")
    return raw


def _safe_path(value: str | os.PathLike[str]) -> Path:
    return _absolute_without_symlinks(value).resolve(strict=False)


def _safe_child(root: Path, relative: str | os.PathLike[str]) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ThemeLifecycleError("Path escapes its owned root")
    root_path = _absolute_without_symlinks(root)
    candidate = _absolute_without_symlinks(root_path / relative_path)
    resolved_root = root_path.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ThemeLifecycleError("Path escapes its owned root") from exc
    return resolved_candidate


def _fsync_directory(path: Path) -> None:
    directory = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path = _safe_child(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    _absolute_without_symlinks(path.parent)
    with tempfile.TemporaryDirectory(prefix=".theme-write-", dir=path.parent) as staging:
        temporary = Path(staging) / path.name
        temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)


def _assert_no_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise ThemeLifecycleError("Theme trees cannot contain symlinks")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ThemeLifecycleError("Theme trees cannot contain symlinks")


def _file_digests(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def _digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


@dataclass(frozen=True)
class ThemeReceipt:
    receipt_id: str
    theme_id: str
    scope: str
    target: str
    installed_digest: str
    previous_digest: str | None
    installed_files: dict[str, str] = field(default_factory=dict)
    preserved_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_id(self.receipt_id, "Receipt ID")
        _validate_id(self.theme_id, "Theme ID")
        _validate_scope(self.scope)

    def as_dict(self) -> dict[str, Any]:
        return {"schemaVersion": "2.0.0", "receiptId": self.receipt_id, "themeId": self.theme_id, "scope": self.scope, "target": self.target, "installedDigest": self.installed_digest, "previousDigest": self.previous_digest, "installedFiles": self.installed_files, "preservedPaths": list(self.preserved_paths)}


class ThemeLifecycle:
    def __init__(self, state_root: str | Path) -> None:
        self.state_root = _safe_path(state_root)
        self.state_root.mkdir(parents=True, exist_ok=True)
        _absolute_without_symlinks(self.state_root)

    def _target(self, value: str | Path) -> Path:
        target = _safe_path(value)
        if target.exists() and not target.is_dir():
            raise ThemeLifecycleError("Theme target must be a directory")
        return target

    def _source(self, value: str | Path) -> Path:
        source = _safe_path(value)
        if not source.is_dir():
            raise ThemeLifecycleError("Theme source must be an existing directory")
        _assert_no_symlinks(source)
        return source

    def _receipt_path(self, receipt_id: str) -> Path:
        return _safe_child(self.state_root, f"{_validate_id(receipt_id, 'Receipt ID')}.json")

    def _backup_path(self, receipt_id: str) -> Path:
        return _safe_child(self.state_root, f"{_validate_id(receipt_id, 'Receipt ID')}.previous")

    def install(self, source: str | Path, target: str | Path, *, theme_id: str, scope: str, receipt_id: str) -> ThemeReceipt:
        source_path = self._source(source)
        target_path = self._target(target)
        _validate_id(theme_id, "Theme ID")
        _validate_scope(scope)
        _validate_id(receipt_id, "Receipt ID")
        if source_path.is_relative_to(target_path) or target_path.is_relative_to(source_path):
            raise ThemeLifecycleError("theme source and target must be separate directories")
        previous = _digest_tree(target_path) if target_path.is_dir() else None
        staging = Path(tempfile.mkdtemp(prefix="theme-stage-", dir=self.state_root))
        backup = self._backup_path(receipt_id)
        had_target = target_path.exists()
        try:
            shutil.copytree(source_path, staging / "theme")
            installed = _digest_tree(staging / "theme")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            _absolute_without_symlinks(target_path.parent)
            if backup.exists():
                shutil.rmtree(backup)
            if had_target:
                target_path.rename(backup)
            (staging / "theme").rename(target_path)
            _fsync_directory(target_path.parent)
            receipt = ThemeReceipt(receipt_id, theme_id, scope, str(target_path), installed, previous, _file_digests(target_path))
            _atomic_json(self._receipt_path(receipt_id), receipt.as_dict())
            return receipt
        except BaseException:
            if target_path.exists():
                shutil.rmtree(target_path)
            if had_target and backup.exists():
                backup.rename(target_path)
                _fsync_directory(target_path.parent)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def activate(self, receipt: ThemeReceipt) -> dict[str, Any]:
        _validate_id(receipt.receipt_id, "Receipt ID")
        target = self._target(receipt.target)
        _assert_no_symlinks(target)
        if not target.is_dir() or _digest_tree(target) != receipt.installed_digest:
            raise ThemeLifecycleError("theme target changed before activation; refusing activate")
        active = {"schemaVersion": "2.0.0", "receiptId": receipt.receipt_id, "themeId": receipt.theme_id, "scope": receipt.scope, "target": str(target), "installedDigest": receipt.installed_digest, "installedFiles": receipt.installed_files, "preservedPaths": list(receipt.preserved_paths)}
        _atomic_json(_safe_child(self.state_root, "active.json"), active)
        return active

    def upgrade(self, source: str | Path, target: str | Path, *, theme_id: str, scope: str, receipt_id: str) -> ThemeReceipt:
        source_path = self._source(source)
        target_path = self._target(target)
        _validate_id(theme_id, "Theme ID")
        _validate_scope(scope)
        _validate_id(receipt_id, "Receipt ID")
        if source_path.is_relative_to(target_path) or target_path.is_relative_to(source_path):
            raise ThemeLifecycleError("theme source and target must be separate directories")
        previous = _digest_tree(target_path) if target_path.is_dir() else None
        _assert_no_symlinks(target_path) if target_path.is_dir() else None
        current_files = _file_digests(target_path) if target_path.is_dir() else {}
        active_path = _safe_child(self.state_root, "active.json")
        active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.is_file() else {}
        managed_files = active.get("installedFiles", {}) if isinstance(active, dict) else {}
        if not managed_files:
            for receipt_path in sorted(self.state_root.glob("*.json"), key=lambda path: path.stat().st_mtime_ns, reverse=True):
                if receipt_path.is_symlink():
                    raise ThemeLifecycleError("Theme state contains a symlinked receipt")
                try:
                    candidate_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    continue
                if candidate_receipt.get("target") == str(target_path) and isinstance(candidate_receipt.get("installedFiles"), dict):
                    managed_files = candidate_receipt["installedFiles"]
                    break
        staging = Path(tempfile.mkdtemp(prefix="theme-upgrade-", dir=self.state_root))
        backup = self._backup_path(receipt_id)
        had_target = target_path.exists()
        preserved: list[str] = []
        try:
            shutil.copytree(source_path, staging / "theme")
            candidate = staging / "theme"
            for relative in sorted(set(managed_files) - set(current_files)):
                replacement = _safe_child(candidate, relative)
                if replacement.is_file():
                    replacement.unlink()
                    preserved.append(f"deleted:{relative}")
                elif replacement.is_dir():
                    shutil.rmtree(replacement)
                    preserved.append(f"deleted:{relative}")
            for relative, current_digest in current_files.items():
                current = _safe_child(target_path, relative)
                replacement = _safe_child(candidate, relative)
                if replacement.exists():
                    if managed_files.get(relative) != current_digest:
                        replacement.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(current, replacement)
                        preserved.append(relative)
                elif managed_files.get(relative) != current_digest:
                    replacement.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(current, replacement)
                    preserved.append(relative)
            installed = _digest_tree(candidate)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            _absolute_without_symlinks(target_path.parent)
            if backup.exists():
                shutil.rmtree(backup)
            if had_target:
                target_path.rename(backup)
            candidate.rename(target_path)
            _fsync_directory(target_path.parent)
            receipt = ThemeReceipt(receipt_id, theme_id, scope, str(target_path), installed, previous, _file_digests(target_path), tuple(sorted(preserved)))
            _atomic_json(self._receipt_path(receipt_id), receipt.as_dict())
            self.activate(receipt)
            return receipt
        except BaseException:
            if target_path.exists():
                shutil.rmtree(target_path)
            if had_target and backup.exists():
                backup.rename(target_path)
                _fsync_directory(target_path.parent)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def restore(self, receipt: ThemeReceipt) -> None:
        _validate_id(receipt.receipt_id, "Receipt ID")
        target = self._target(receipt.target)
        _assert_no_symlinks(target)
        if not target.is_dir() or _digest_tree(target) != receipt.installed_digest:
            raise ThemeLifecycleError("theme target changed after installation; refusing overwrite")
        backup = self._backup_path(receipt.receipt_id)
        if receipt.previous_digest is None:
            if backup.exists():
                raise ThemeLifecycleError("Unexpected theme backup exists; refusing destructive restore")
        else:
            if not backup.is_dir():
                raise ThemeLifecycleError("Theme backup is missing; refusing destructive restore")
            _assert_no_symlinks(backup)
            if _digest_tree(backup) != receipt.previous_digest:
                raise ThemeLifecycleError("Theme backup changed; refusing destructive restore")
        shutil.rmtree(target)
        if receipt.previous_digest is not None:
            backup.rename(target)
        _fsync_directory(target.parent)
        active = _safe_child(self.state_root, "active.json")
        if active.is_file():
            try:
                if json.loads(active.read_text(encoding="utf-8")).get("receiptId") == receipt.receipt_id:
                    active.unlink()
                    _fsync_directory(self.state_root)
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass
