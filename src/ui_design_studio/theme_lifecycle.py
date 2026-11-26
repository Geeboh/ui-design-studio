"""Versioned theme installation, activation, and conflict-aware restore."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any


class ThemeLifecycleError(RuntimeError):
    """Theme lifecycle operation failed without overwriting user-owned bytes."""


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

    def as_dict(self) -> dict[str, Any]:
        return {"schemaVersion": "2.0.0", "receiptId": self.receipt_id, "themeId": self.theme_id, "scope": self.scope, "target": self.target, "installedDigest": self.installed_digest, "previousDigest": self.previous_digest}


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
        try:
            shutil.copytree(source, staging / "theme")
            installed = _digest_tree(staging / "theme")
            target.parent.mkdir(parents=True, exist_ok=True)
            backup = self.state_root / f"{receipt_id}.previous"
            if target.exists():
                if backup.exists():
                    shutil.rmtree(backup)
                target.rename(backup)
            (staging / "theme").rename(target)
            receipt = ThemeReceipt(receipt_id, theme_id, scope, str(target), installed, previous)
            (self.state_root / f"{receipt_id}.json").write_text(json.dumps(receipt.as_dict(), sort_keys=True) + "\n", encoding="utf-8")
            return receipt
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
