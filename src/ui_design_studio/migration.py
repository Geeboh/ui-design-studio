"""Copy-first legacy migration and recovery primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any


class MigrationError(RuntimeError):
    """Migration cannot proceed without risking source or candidate integrity."""


class MigrationConflict(MigrationError):
    """Source or activated candidate changed under an existing receipt."""


class MigrationPhase(StrEnum):
    INVENTORIED = "inventoried"
    BACKED_UP = "backed_up"
    IMPORTING = "importing"
    VALIDATED = "validated"
    PREPARED = "prepared"
    ACTIVE = "active"
    BLOCKED = "blocked"
    RESTORED = "restored"


_MIGRATION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _validate_migration_id(value: str) -> str:
    if not isinstance(value, str) or not _MIGRATION_ID.fullmatch(value):
        raise MigrationError("Migration ID must be an ASCII bounded identifier")
    return value


def _absolute_without_symlinks(value: str | os.PathLike[str]) -> Path:
    raw = Path(os.path.abspath(os.path.expanduser(os.fspath(value))))
    current = Path(raw.anchor)
    for part in raw.parts[1:]:
        current /= part
        if current.is_symlink():
            raise MigrationError(f"Path contains a symlink ancestor: {current}")
    return raw


def _safe_child(root: Path, relative: str | os.PathLike[str]) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise MigrationError("Path escapes its owned root")
    root_path = _absolute_without_symlinks(root)
    candidate = _absolute_without_symlinks(root_path / relative_path)
    resolved_root = root_path.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise MigrationError("Path escapes its owned root") from exc
    return resolved_candidate


def _fsync_directory(path: Path) -> None:
    directory = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


@dataclass(frozen=True)
class InventoryEntry:
    relative_path: str
    byte_length: int
    sha256: str
    format: str
    symlink: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.relative_path,
            "bytes": self.byte_length,
            "sha256": self.sha256,
            "format": self.format,
            "symlink": self.symlink,
        }


@dataclass(frozen=True)
class MappingEntry:
    source_path: str
    target_id: str
    status: str
    findings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"sourcePath": self.source_path, "targetId": self.target_id, "status": self.status, "findings": list(self.findings)}


@dataclass
class MigrationReceipt:
    migration_id: str
    phase: MigrationPhase
    source_root: str
    candidate_root: str
    backup_root: str
    source_inventory_sha256: str | None = None
    candidate_inventory_sha256: str | None = None
    backup_manifest_sha256: str | None = None
    inventory: list[InventoryEntry] = field(default_factory=list)
    mappings: list[MappingEntry] = field(default_factory=list)
    checkpoint: int = 0
    findings: list[dict[str, str]] = field(default_factory=list)
    candidate_writes: int = 0
    prior_locator: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": "2.0.0",
            "migrationId": self.migration_id,
            "phase": self.phase.value,
            "sourceRoot": self.source_root,
            "candidateRoot": self.candidate_root,
            "backupRoot": self.backup_root,
            "sourceInventorySha256": self.source_inventory_sha256,
            "candidateInventorySha256": self.candidate_inventory_sha256,
            "backupManifestSha256": self.backup_manifest_sha256,
            "inventory": [entry.as_dict() for entry in self.inventory],
            "mappings": [entry.as_dict() for entry in self.mappings],
            "checkpoint": self.checkpoint,
            "findings": list(self.findings),
            "candidateWrites": self.candidate_writes,
            "priorLocator": self.prior_locator,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MigrationReceipt":
        if value.get("schemaVersion") != "2.0.0":
            raise MigrationError("Unsupported migration receipt schema")
        try:
            phase = MigrationPhase(value["phase"])
            migration_id = _validate_migration_id(value["migrationId"])
        except (KeyError, ValueError) as exc:
            raise MigrationError("Invalid migration receipt") from exc
        inventory = [InventoryEntry(item["path"], item["bytes"], item["sha256"], item["format"], item.get("symlink", False)) for item in value.get("inventory", [])]
        mappings = [MappingEntry(item["sourcePath"], item["targetId"], item["status"], tuple(item.get("findings", ()))) for item in value.get("mappings", [])]
        return cls(
            migration_id=migration_id,
            phase=phase,
            source_root=value["sourceRoot"],
            candidate_root=value["candidateRoot"],
            backup_root=value["backupRoot"],
            source_inventory_sha256=value.get("sourceInventorySha256"),
            candidate_inventory_sha256=value.get("candidateInventorySha256"),
            backup_manifest_sha256=value.get("backupManifestSha256"),
            inventory=inventory,
            mappings=mappings,
            checkpoint=value.get("checkpoint", 0),
            findings=list(value.get("findings", [])),
            candidate_writes=value.get("candidateWrites", 0),
            prior_locator=value.get("priorLocator"),
        )


class MigrationManager:
    def __init__(self, source_root: str | os.PathLike[str], candidate_root: str | os.PathLike[str], backup_root: str | os.PathLike[str]):
        source = _absolute_without_symlinks(source_root).resolve(strict=False)
        candidate = _absolute_without_symlinks(candidate_root).resolve(strict=False)
        backup = _absolute_without_symlinks(backup_root).resolve(strict=False)
        self.source_root = source
        self.candidate_root = candidate
        self.backup_root = backup
        if not self.source_root.is_dir():
            raise MigrationError("Migration source root must be an existing directory")
        if len({self.source_root, self.candidate_root, self.backup_root}) != 3:
            raise MigrationError("Migration roots must be separate")
        if (
            self.candidate_root.is_relative_to(self.source_root)
            or self.source_root.is_relative_to(self.candidate_root)
            or self.backup_root.is_relative_to(self.source_root)
            or self.source_root.is_relative_to(self.backup_root)
            or self.candidate_root.is_relative_to(self.backup_root)
            or self.backup_root.is_relative_to(self.candidate_root)
        ):
            raise MigrationError("Migration roots cannot overlap")

    def _check_receipt(self, receipt: MigrationReceipt) -> None:
        _validate_migration_id(receipt.migration_id)
        if tuple(Path(value).expanduser().resolve(strict=False) for value in (receipt.source_root, receipt.candidate_root, receipt.backup_root)) != (self.source_root, self.candidate_root, self.backup_root):
            raise MigrationError("Migration receipt roots do not match this manager")

    @property
    def receipt_path(self) -> Path:
        return _safe_child(self.candidate_root, "migration-receipt.json")

    @staticmethod
    def _file_digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _inventory_digest(entries: list[InventoryEntry]) -> str:
        payload = json.dumps([entry.as_dict() for entry in entries], sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _write_receipt(self, receipt: MigrationReceipt) -> None:
        self._check_receipt(receipt)
        self.candidate_root.mkdir(parents=True, exist_ok=True)
        _absolute_without_symlinks(self.candidate_root)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.candidate_root, prefix=".migration-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(receipt.as_dict(), handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, self.receipt_path)
            _fsync_directory(self.candidate_root)
        finally:
            temporary.unlink(missing_ok=True)

    def _read_receipt(self) -> MigrationReceipt | None:
        path = self.receipt_path
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return MigrationReceipt.from_dict(value)
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise MigrationError("Migration receipt is unreadable") from exc

    def _scan_inventory(self) -> list[InventoryEntry]:
        entries: list[InventoryEntry] = []
        excluded = {".git", ".ui-design-studio", ".prism-state", ".venv-prism", "__pycache__"}
        for path in sorted(self.source_root.rglob("*")):
            relative_path = path.relative_to(self.source_root)
            if any(part in excluded or part.startswith(".migration-") for part in relative_path.parts):
                continue
            relative = relative_path.as_posix()
            if path.is_symlink():
                if not _safe_child(self.source_root, relative_path.parent).is_relative_to(self.source_root):
                    raise MigrationError("Symlink path escapes source root")
                entries.append(InventoryEntry(relative, 0, "", "symlink", True))
                continue
            if not path.is_file():
                continue
            safe = _safe_child(self.source_root, relative_path)
            entries.append(InventoryEntry(relative, safe.stat().st_size, self._file_digest(safe), path.suffix.lower().lstrip(".") or "binary"))
        return entries

    def inventory(self, migration_id: str) -> MigrationReceipt:
        _validate_migration_id(migration_id)
        existing = self._read_receipt()
        entries = self._scan_inventory()
        digest = self._inventory_digest(entries)
        if existing is not None:
            self._check_receipt(existing)
            if existing.migration_id != migration_id or existing.source_inventory_sha256 != digest:
                raise MigrationConflict("Legacy source inventory changed under the existing migration")
            return existing
        receipt = MigrationReceipt(migration_id, MigrationPhase.INVENTORIED, str(self.source_root), str(self.candidate_root), str(self.backup_root), source_inventory_sha256=digest, inventory=entries)
        self._write_receipt(receipt)
        return receipt

    def _write_json(self, path: Path, value: dict[str, Any]) -> None:
        path = _safe_child(path.parent, path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        _absolute_without_symlinks(path.parent)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".migration-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, path)
            _fsync_directory(path.parent)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _copy_file_atomic(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        _absolute_without_symlinks(destination.parent)
        with source.open("rb") as source_handle, tempfile.NamedTemporaryFile("wb", dir=destination.parent, prefix=".migration-copy-", delete=False) as handle:
            temporary = Path(handle.name)
            while chunk := source_handle.read(1024 * 1024):
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, destination)
            _fsync_directory(destination.parent)
        finally:
            temporary.unlink(missing_ok=True)

    def backup(self, receipt: MigrationReceipt) -> MigrationReceipt:
        self._check_receipt(receipt)
        if receipt.phase is not MigrationPhase.INVENTORIED:
            raise MigrationError("Backup requires an inventoried migration")
        if receipt.source_inventory_sha256 != self._inventory_digest(self._scan_inventory()):
            raise MigrationConflict("Source changed before backup")
        target_root = _safe_child(self.backup_root, receipt.migration_id)
        target_root.mkdir(parents=True, exist_ok=True)
        _absolute_without_symlinks(target_root)
        manifest_entries = []
        findings = list(receipt.findings)
        for entry in receipt.inventory:
            source = _safe_child(self.source_root, entry.relative_path) if not entry.symlink else self.source_root / entry.relative_path
            target = _safe_child(target_root, entry.relative_path)
            if entry.symlink:
                if not source.is_symlink():
                    raise MigrationConflict(f"Legacy symlink changed during backup: {entry.relative_path}")
                findings.append({"path": entry.relative_path, "reason": "symlink_not_copied"})
                manifest_entries.append({"path": entry.relative_path, "symlink": True, "target": os.readlink(source)})
                continue
            self._copy_file_atomic(source, target)
            manifest_entries.append({"path": entry.relative_path, "bytes": target.stat().st_size, "sha256": self._file_digest(target), "symlink": False})
        manifest = {"schemaVersion": "2.0.0", "migrationId": receipt.migration_id, "entries": manifest_entries, "findings": findings}
        manifest_path = _safe_child(target_root, "backup-manifest.json")
        self._write_json(manifest_path, manifest)
        manifest_digest = self._file_digest(manifest_path)
        updated = MigrationReceipt.from_dict({**receipt.as_dict(), "phase": MigrationPhase.BACKED_UP.value, "backupManifestSha256": manifest_digest, "findings": findings})
        self._write_receipt(updated)
        return updated

    def verify_backup(self, receipt: MigrationReceipt) -> None:
        self._check_receipt(receipt)
        manifest_path = _safe_child(_safe_child(self.backup_root, receipt.migration_id), "backup-manifest.json")
        if not manifest_path.is_file() or self._file_digest(manifest_path) != receipt.backup_manifest_sha256:
            raise MigrationError("Backup manifest is missing or changed")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MigrationError("Backup manifest is unreadable") from exc
        if manifest.get("migrationId") != receipt.migration_id:
            raise MigrationError("Backup manifest belongs to another migration")
        for entry in manifest.get("entries", []):
            if entry.get("symlink"):
                continue
            path = _safe_child(self.backup_root / receipt.migration_id, entry["path"])
            if not path.is_file() or path.is_symlink() or path.stat().st_size != entry["bytes"] or self._file_digest(path) != entry["sha256"]:
                raise MigrationError(f"Backup bytes are corrupt: {entry['path']}")

    @staticmethod
    def _target_id(migration_id: str, relative_path: str) -> str:
        return hashlib.sha256(f"{migration_id}\n{relative_path}".encode("utf-8")).hexdigest()[:32]

    def import_records(self, receipt: MigrationReceipt) -> MigrationReceipt:
        self._check_receipt(receipt)
        if receipt.phase not in (MigrationPhase.BACKED_UP, MigrationPhase.IMPORTING):
            raise MigrationError("Import requires a backed-up migration")
        self.verify_backup(receipt)
        mappings = list(receipt.mappings)
        findings = list(receipt.findings)
        legacy_root = _safe_child(self.candidate_root, "legacy")
        legacy_root.mkdir(parents=True, exist_ok=True)
        start = receipt.checkpoint
        for index, entry in enumerate(receipt.inventory[start:], start=start):
            target_id = self._target_id(receipt.migration_id, entry.relative_path)
            source = self.source_root / entry.relative_path
            destination = _safe_child(legacy_root, entry.relative_path)
            if entry.symlink:
                finding = {"path": entry.relative_path, "reason": "legacy_symlink_requires_repair"}
                findings.append(finding)
                mappings.append(MappingEntry(entry.relative_path, target_id, "quarantined", (finding["reason"],)))
            else:
                source = _safe_child(self.source_root, entry.relative_path)
                data = source.read_bytes()
                if hashlib.sha256(data).hexdigest() != entry.sha256:
                    raise MigrationConflict(f"Legacy source changed during import: {entry.relative_path}")
                self._copy_file_atomic(source, destination)
                item_findings: list[str] = []
                if entry.format == "json":
                    try:
                        json.loads(data)
                    except (UnicodeError, json.JSONDecodeError):
                        item_findings.append("malformed_json_preserved_as_unknown")
                        findings.append({"path": entry.relative_path, "reason": item_findings[0]})
                mappings.append(MappingEntry(entry.relative_path, target_id, "quarantined" if item_findings else "imported", tuple(item_findings)))
            copied_entries = [
                InventoryEntry(item.relative_path, (legacy_root / item.relative_path).stat().st_size if not item.symlink else 0, self._file_digest(legacy_root / item.relative_path) if not item.symlink else "", item.format, item.symlink)
                for item in receipt.inventory[:index + 1]
            ]
            updated = MigrationReceipt.from_dict({**receipt.as_dict(), "phase": MigrationPhase.IMPORTING.value, "checkpoint": index + 1, "mappings": [item.as_dict() for item in mappings], "findings": findings, "candidateInventorySha256": self._inventory_digest(copied_entries)})
            self._write_receipt(updated)
            receipt = updated
        return receipt

    def validate(self, receipt: MigrationReceipt) -> MigrationReceipt:
        self._check_receipt(receipt)
        if receipt.phase not in (MigrationPhase.IMPORTING, MigrationPhase.VALIDATED):
            raise MigrationError("Validation requires an imported migration")
        self.verify_backup(receipt)
        current = self.inventory(receipt.migration_id)
        if current.source_inventory_sha256 != receipt.source_inventory_sha256:
            raise MigrationConflict("Legacy source changed before validation")
        legacy_root = _safe_child(self.candidate_root, "legacy")
        findings = list(receipt.findings)
        for entry in receipt.inventory:
            if entry.symlink:
                continue
            candidate = _safe_child(legacy_root, entry.relative_path)
            if not candidate.is_file() or candidate.is_symlink() or self._file_digest(candidate) != entry.sha256:
                findings.append({"path": entry.relative_path, "reason": "candidate_bytes_missing_or_corrupt"})
        if len(receipt.mappings) != len(receipt.inventory):
            findings.append({"path": "mappings", "reason": "mapping_count_incomplete"})
        if any(item.get("reason") == "candidate_bytes_missing_or_corrupt" for item in findings):
            raise MigrationError("Candidate validation found missing or corrupt copied bytes")
        updated = MigrationReceipt.from_dict({**receipt.as_dict(), "phase": MigrationPhase.VALIDATED.value, "findings": findings})
        self._write_receipt(updated)
        return updated

    @property
    def locator_path(self) -> Path:
        return _safe_child(self.source_root, Path(".prism") / "state-locator.json")

    @property
    def activation_journal_path(self) -> Path:
        return _safe_child(self.candidate_root, "activation-journal.json")

    def activate(self, receipt: MigrationReceipt) -> MigrationReceipt:
        self._check_receipt(receipt)
        if receipt.phase is not MigrationPhase.VALIDATED:
            raise MigrationError("Activation requires a validated migration")
        self.verify_backup(receipt)
        prior = None
        if self.locator_path.is_file():
            try:
                prior = json.loads(self.locator_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise MigrationError("Existing state locator is unreadable") from exc
        journal = {
            "schemaVersion": "2.0.0",
            "migrationId": receipt.migration_id,
            "phase": "prepared",
            "priorLocator": prior,
            "candidateRoot": str(self.candidate_root),
            "sourceInventorySha256": receipt.source_inventory_sha256,
            "candidateInventorySha256": receipt.candidate_inventory_sha256,
        }
        self._write_json(self.activation_journal_path, journal)
        self._write_json(self.locator_path, {
            "schemaVersion": "2.0.0",
            "migrationId": receipt.migration_id,
            "candidateRoot": str(self.candidate_root),
            "sourceInventorySha256": receipt.source_inventory_sha256,
            "candidateInventorySha256": receipt.candidate_inventory_sha256,
            "candidateWrites": 0,
        })
        self._write_json(self.activation_journal_path, {**journal, "phase": "active"})
        updated = MigrationReceipt.from_dict({**receipt.as_dict(), "phase": MigrationPhase.ACTIVE.value, "priorLocator": prior})
        self._write_receipt(updated)
        return updated

    def mark_candidate_write(self, receipt: MigrationReceipt) -> MigrationReceipt:
        self._check_receipt(receipt)
        if receipt.phase is not MigrationPhase.ACTIVE:
            raise MigrationError("Candidate writes require an active migration")
        locator = json.loads(self.locator_path.read_text(encoding="utf-8"))
        if locator.get("migrationId") != receipt.migration_id:
            raise MigrationConflict("Active locator belongs to another migration")
        writes = int(locator.get("candidateWrites", 0)) + 1
        self._write_json(self.locator_path, {**locator, "candidateWrites": writes})
        updated = MigrationReceipt.from_dict({**receipt.as_dict(), "candidateWrites": writes})
        self._write_receipt(updated)
        return updated

    def rollback(self, receipt: MigrationReceipt) -> MigrationReceipt:
        self._check_receipt(receipt)
        if receipt.phase is not MigrationPhase.ACTIVE:
            raise MigrationError("Rollback requires an active migration")
        self.verify_backup(receipt)
        locator = json.loads(self.locator_path.read_text(encoding="utf-8"))
        if locator.get("migrationId") != receipt.migration_id:
            raise MigrationConflict("Active locator belongs to another migration")
        if receipt.candidate_writes or locator.get("candidateWrites", 0):
            raise MigrationConflict("Candidate has divergent later writes; export or fork it before rollback")
        if receipt.prior_locator is None:
            self.locator_path.unlink(missing_ok=True)
            _fsync_directory(self.locator_path.parent)
        else:
            self._write_json(self.locator_path, receipt.prior_locator)
        self._write_json(self.activation_journal_path, {"schemaVersion": "2.0.0", "migrationId": receipt.migration_id, "phase": MigrationPhase.RESTORED.value, "priorLocator": receipt.prior_locator})
        updated = MigrationReceipt.from_dict({**receipt.as_dict(), "phase": MigrationPhase.RESTORED.value})
        self._write_receipt(updated)
        return updated
