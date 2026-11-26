"""Copy-first legacy migration and recovery primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
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
        except (KeyError, ValueError) as exc:
            raise MigrationError("Invalid migration receipt phase") from exc
        inventory = [InventoryEntry(item["path"], item["bytes"], item["sha256"], item["format"], item.get("symlink", False)) for item in value.get("inventory", [])]
        mappings = [MappingEntry(item["sourcePath"], item["targetId"], item["status"], tuple(item.get("findings", ()))) for item in value.get("mappings", [])]
        return cls(
            migration_id=value["migrationId"],
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
        self.source_root = Path(source_root).expanduser().resolve()
        self.candidate_root = Path(candidate_root).expanduser().resolve()
        self.backup_root = Path(backup_root).expanduser().resolve()
        if not self.source_root.is_dir():
            raise MigrationError("Migration source root must be an existing directory")
        if self.candidate_root == self.source_root or self.backup_root == self.source_root:
            raise MigrationError("Migration candidate and backup roots must be separate from the source")
        if self.candidate_root.is_relative_to(self.source_root) or self.backup_root.is_relative_to(self.source_root):
            raise MigrationError("Migration candidate and backup roots cannot be inside the source tree")

    @property
    def receipt_path(self) -> Path:
        return self.candidate_root / "migration-receipt.json"

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
        self.candidate_root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.candidate_root, prefix=".migration-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(receipt.as_dict(), handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, self.receipt_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _read_receipt(self) -> MigrationReceipt | None:
        if not self.receipt_path.is_file():
            return None
        try:
            value = json.loads(self.receipt_path.read_text(encoding="utf-8"))
            return MigrationReceipt.from_dict(value)
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
            raise MigrationError("Migration receipt is unreadable") from exc

    def inventory(self, migration_id: str) -> MigrationReceipt:
        if not isinstance(migration_id, str) or not migration_id.strip():
            raise MigrationError("Migration ID is required")
        existing = self._read_receipt()
        entries: list[InventoryEntry] = []
        excluded = {".git", ".ui-design-studio", ".prism-state", ".venv-prism", "__pycache__"}
        for path in sorted(self.source_root.rglob("*")):
            relative_path = path.relative_to(self.source_root)
            if any(part in excluded or part.startswith(".migration-") for part in relative_path.parts):
                continue
            relative = relative_path.as_posix()
            if path.is_symlink():
                entries.append(InventoryEntry(relative, 0, "", "symlink", True))
                continue
            if not path.is_file():
                continue
            entries.append(InventoryEntry(relative, path.stat().st_size, self._file_digest(path), path.suffix.lower().lstrip(".") or "binary"))
        digest = self._inventory_digest(entries)
        if existing is not None:
            if existing.migration_id != migration_id or existing.source_inventory_sha256 != digest:
                raise MigrationConflict("Legacy source inventory changed under the existing migration")
            return existing
        receipt = MigrationReceipt(migration_id, MigrationPhase.INVENTORIED, str(self.source_root), str(self.candidate_root), str(self.backup_root), source_inventory_sha256=digest, inventory=entries)
        self._write_receipt(receipt)
        return receipt
    def _write_json(self, path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".migration-", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def backup(self, receipt: MigrationReceipt) -> MigrationReceipt:
        if receipt.phase is not MigrationPhase.INVENTORIED:
            raise MigrationError("Backup requires an inventoried migration")
        if receipt.source_inventory_sha256 != self._inventory_digest([
            InventoryEntry(item.relative_path, (self.source_root / item.relative_path).stat().st_size, self._file_digest(self.source_root / item.relative_path), item.format, item.symlink)
            for item in receipt.inventory if not item.symlink
        ]):
            raise MigrationConflict("Source changed before backup")
        target_root = self.backup_root / receipt.migration_id
        target_root.mkdir(parents=True, exist_ok=True)
        manifest_entries = []
        findings = list(receipt.findings)
        for entry in receipt.inventory:
            source = self.source_root / entry.relative_path
            target = target_root / entry.relative_path
            if entry.symlink:
                findings.append({"path": entry.relative_path, "reason": "symlink_not_copied"})
                manifest_entries.append({"path": entry.relative_path, "symlink": True, "target": os.readlink(source)})
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as source_handle, tempfile.NamedTemporaryFile("wb", dir=target.parent, prefix=".backup-", delete=False) as handle:
                temporary = Path(handle.name)
                while chunk := source_handle.read(1024 * 1024):
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            manifest_entries.append({"path": entry.relative_path, "bytes": target.stat().st_size, "sha256": self._file_digest(target), "symlink": False})
        manifest = {"schemaVersion": "2.0.0", "migrationId": receipt.migration_id, "entries": manifest_entries, "findings": findings}
        manifest_path = target_root / "backup-manifest.json"
        self._write_json(manifest_path, manifest)
        manifest_digest = self._file_digest(manifest_path)
        updated = MigrationReceipt.from_dict({**receipt.as_dict(), "phase": MigrationPhase.BACKED_UP.value, "backupManifestSha256": manifest_digest, "findings": findings})
        self._write_receipt(updated)
        return updated

    def verify_backup(self, receipt: MigrationReceipt) -> None:
        manifest_path = self.backup_root / receipt.migration_id / "backup-manifest.json"
        if not manifest_path.is_file() or self._file_digest(manifest_path) != receipt.backup_manifest_sha256:
            raise MigrationError("Backup manifest is missing or changed")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("entries", []):
            if entry.get("symlink"):
                continue
            path = self.backup_root / receipt.migration_id / entry["path"]
            if not path.is_file() or path.is_symlink() or path.stat().st_size != entry["bytes"] or self._file_digest(path) != entry["sha256"]:
                raise MigrationError(f"Backup bytes are corrupt: {entry['path']}")
    @staticmethod
    def _target_id(migration_id: str, relative_path: str) -> str:
        return hashlib.sha256(f"{migration_id}\n{relative_path}".encode("utf-8")).hexdigest()[:32]

    def import_records(self, receipt: MigrationReceipt) -> MigrationReceipt:
        if receipt.phase not in (MigrationPhase.BACKED_UP, MigrationPhase.IMPORTING):
            raise MigrationError("Import requires a backed-up migration")
        self.verify_backup(receipt)
        mappings = list(receipt.mappings)
        findings = list(receipt.findings)
        legacy_root = self.candidate_root / "legacy"
        legacy_root.mkdir(parents=True, exist_ok=True)
        start = receipt.checkpoint
        for index, entry in enumerate(receipt.inventory[start:], start=start):
            target_id = self._target_id(receipt.migration_id, entry.relative_path)
            source = self.source_root / entry.relative_path
            destination = legacy_root / entry.relative_path
            if entry.symlink:
                finding = {"path": entry.relative_path, "reason": "legacy_symlink_requires_repair"}
                findings.append(finding)
                mappings.append(MappingEntry(entry.relative_path, target_id, "quarantined", (finding["reason"],)))
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                data = source.read_bytes()
                if hashlib.sha256(data).hexdigest() != entry.sha256:
                    raise MigrationConflict(f"Legacy source changed during import: {entry.relative_path}")
                destination.write_bytes(data)
                item_findings: list[str] = []
                if entry.format == "json":
                    try:
                        json.loads(data)
                    except (UnicodeError, json.JSONDecodeError):
                        item_findings.append("malformed_json_preserved_as_unknown")
                        findings.append({"path": entry.relative_path, "reason": item_findings[0]})
                mappings.append(MappingEntry(entry.relative_path, target_id, "quarantined" if item_findings else "imported", tuple(item_findings)))
            updated = MigrationReceipt.from_dict({**receipt.as_dict(), "phase": MigrationPhase.IMPORTING.value, "checkpoint": index + 1, "mappings": [item.as_dict() for item in mappings], "findings": findings, "candidateInventorySha256": self._inventory_digest([InventoryEntry(item.relative_path, (legacy_root / item.relative_path).stat().st_size if not item.symlink else 0, self._file_digest(legacy_root / item.relative_path) if not item.symlink else "", item.format, item.symlink) for item in receipt.inventory[:index + 1]])})
            self._write_receipt(updated)
            receipt = updated
        return receipt
    def validate(self, receipt: MigrationReceipt) -> MigrationReceipt:
        if receipt.phase not in (MigrationPhase.IMPORTING, MigrationPhase.VALIDATED):
            raise MigrationError("Validation requires an imported migration")
        self.verify_backup(receipt)
        current = self.inventory(receipt.migration_id)
        if current.source_inventory_sha256 != receipt.source_inventory_sha256:
            raise MigrationConflict("Legacy source changed before validation")
        legacy_root = self.candidate_root / "legacy"
        findings = list(receipt.findings)
        for entry in receipt.inventory:
            if entry.symlink:
                continue
            candidate = legacy_root / entry.relative_path
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
        return self.source_root / ".prism" / "state-locator.json"

    @property
    def activation_journal_path(self) -> Path:
        return self.candidate_root / "activation-journal.json"

    def activate(self, receipt: MigrationReceipt) -> MigrationReceipt:
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
        if receipt.phase is not MigrationPhase.ACTIVE:
            raise MigrationError("Rollback requires an active migration")
        locator = json.loads(self.locator_path.read_text(encoding="utf-8"))
        if locator.get("migrationId") != receipt.migration_id:
            raise MigrationConflict("Active locator belongs to another migration")
        if receipt.candidate_writes or locator.get("candidateWrites", 0):
            raise MigrationConflict("Candidate has divergent later writes; export or fork it before rollback")
        if receipt.prior_locator is None:
            self.locator_path.unlink(missing_ok=True)
        else:
            self._write_json(self.locator_path, receipt.prior_locator)
        self._write_json(self.activation_journal_path, {"schemaVersion": "2.0.0", "migrationId": receipt.migration_id, "phase": MigrationPhase.RESTORED.value, "priorLocator": receipt.prior_locator})
        updated = MigrationReceipt.from_dict({**receipt.as_dict(), "phase": MigrationPhase.RESTORED.value})
        self._write_receipt(updated)
        return updated
