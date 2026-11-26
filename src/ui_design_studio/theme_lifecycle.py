"""Versioned theme installation, activation, and conflict-aware restore."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any


class ThemeLifecycleError(RuntimeError):
    """Theme lifecycle operation failed without overwriting user-owned bytes."""


def _file_digests(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()}


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

    def as_dict(self) -> dict[str, Any]:
        return {"schemaVersion": "2.0.0", "receiptId": self.receipt_id, "themeId": self.theme_id, "scope": self.scope, "target": self.target, "installedDigest": self.installed_digest, "previousDigest": self.previous_digest, "installedFiles": self.installed_files, "preservedPaths": list(self.preserved_paths)}


class ThemeLifecycle:
    def __init__(self, state_root: str | Path) -> None:
        self.state_root = Path(state_root).expanduser().resolve()
        self.state_root.mkdir(parents=True, exist_ok=True)

    def install(self, source: str | Path, target: str | Path, *, theme_id: str, scope: str, receipt_id: str) -> ThemeReceipt:
        source = Path(source).resolve()
        target = Path(target).expanduser().resolve()
        if not source.is_dir() or source == target or target.is_relative_to(source):
            raise ThemeLifecycleError("theme source and target must be separate directories")
        previous = _digest_tree(target) if target.is_dir() else None
        staging = Path(tempfile.mkdtemp(prefix="theme-stage-", dir=self.state_root))
        backup = self.state_root / f"{receipt_id}.previous"
        had_target = target.exists()
        try:
            shutil.copytree(source, staging / "theme")
            installed = _digest_tree(staging / "theme")
            target.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                shutil.rmtree(backup)
            if had_target:
                target.rename(backup)
            (staging / "theme").rename(target)
            receipt = ThemeReceipt(receipt_id, theme_id, scope, str(target), installed, previous, _file_digests(target))
            (self.state_root / f"{receipt_id}.json").write_text(json.dumps(receipt.as_dict(), sort_keys=True) + "\n", encoding="utf-8")
            return receipt
        except BaseException:
            if target.exists():
                shutil.rmtree(target)
            if had_target and backup.exists():
                backup.rename(target)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def activate(self, receipt: ThemeReceipt) -> dict[str, Any]:
        target = Path(receipt.target).resolve()
        if not target.is_dir() or _digest_tree(target) != receipt.installed_digest:
            raise ThemeLifecycleError("theme target changed before activation; refusing to activate")
        active = {"schemaVersion": "2.0.0", "receiptId": receipt.receipt_id, "themeId": receipt.theme_id, "scope": receipt.scope, "target": str(target), "installedDigest": receipt.installed_digest, "installedFiles": receipt.installed_files, "preservedPaths": list(receipt.preserved_paths)}
        temporary = self.state_root / ".active.json.tmp"
        temporary.write_text(json.dumps(active, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.state_root / "active.json")
        return active

    def upgrade(self, source: str | Path, target: str | Path, *, theme_id: str, scope: str, receipt_id: str) -> ThemeReceipt:
        source = Path(source).resolve()
        target = Path(target).expanduser().resolve()
        if not source.is_dir() or source == target or target.is_relative_to(source):
            raise ThemeLifecycleError("theme source and target must be separate directories")
        previous = _digest_tree(target) if target.is_dir() else None
        current_files = _file_digests(target) if target.is_dir() else {}
        active_path = self.state_root / "active.json"
        active = json.loads(active_path.read_text(encoding="utf-8")) if active_path.is_file() else {}
        managed_files = active.get("installedFiles", {}) if isinstance(active, dict) else {}
        staging = Path(tempfile.mkdtemp(prefix="theme-upgrade-", dir=self.state_root))
        backup = self.state_root / f"{receipt_id}.previous"
        had_target = target.exists()
        preserved = []
        try:
            shutil.copytree(source, staging / "theme")
            candidate = staging / "theme"
            for relative, current_digest in current_files.items():
                current = target / relative
                replacement = candidate / relative
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
            target.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                shutil.rmtree(backup)
            if had_target:
                target.rename(backup)
            candidate.rename(target)
            receipt = ThemeReceipt(receipt_id, theme_id, scope, str(target), installed, previous, _file_digests(target), tuple(sorted(preserved)))
            (self.state_root / f"{receipt_id}.json").write_text(json.dumps(receipt.as_dict(), sort_keys=True) + "\n", encoding="utf-8")
            self.activate(receipt)
            return receipt
        except BaseException:
            if target.exists():
                shutil.rmtree(target)
            if had_target and backup.exists():
                backup.rename(target)
            raise
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def restore(self, receipt: ThemeReceipt) -> None:
        target = Path(receipt.target).resolve()
        if not target.is_dir() or _digest_tree(target) != receipt.installed_digest:
            raise ThemeLifecycleError("theme target changed after installation; refusing overwrite")
        backup = self.state_root / f"{receipt.receipt_id}.previous"
        if target.exists():
            shutil.rmtree(target)
        if backup.exists():
            backup.rename(target)
        active = self.state_root / "active.json"
        if active.is_file():
            try:
                if json.loads(active.read_text(encoding="utf-8")).get("receiptId") == receipt.receipt_id:
                    active.unlink()
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass

