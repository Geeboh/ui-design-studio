"""Validated user-global dashboard network settings."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import os
from pathlib import Path
import secrets


SCHEMA_VERSION = 1
CONFIG_DIRECTORY = "ui-design-studio"
CONFIG_FILENAME = "config.json"


class SettingsError(ValueError):
    """The global settings file is unreadable or has an invalid shape."""


@dataclass(frozen=True)
class GlobalSettings:
    """The complete validated global dashboard network configuration."""

    lan_enabled: bool = True
    lan_address: str | None = None

    def __post_init__(self) -> None:
        if type(self.lan_enabled) is not bool:
            raise SettingsError("lanEnabled must be a boolean")
        if self.lan_address is not None:
            object.__setattr__(self, "lan_address", _ipv4(self.lan_address))

    def as_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "lanEnabled": self.lan_enabled,
            "lanAddress": self.lan_address,
        }


def _ipv4(value: str) -> str:
    if not isinstance(value, str):
        raise SettingsError("lanAddress must be an IPv4 address or null")
    try:
        return str(ipaddress.IPv4Address(value))
    except ipaddress.AddressValueError as exc:
        raise SettingsError("lanAddress must be an IPv4 address or null") from exc


def config_path(*, home: Path | str | None = None, xdg_config_home: Path | str | None = None) -> Path:
    """Return the one user-global settings path used by every project."""
    if xdg_config_home is None:
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        root = Path(xdg_config_home).expanduser()
    else:
        root = Path(home).expanduser() / ".config" if home is not None else Path.home() / ".config"
    return root / CONFIG_DIRECTORY / CONFIG_FILENAME


def _reject_symlinked_path(path: Path) -> None:
    for component in (*path.parents, path):
        if component.is_symlink():
            raise SettingsError(f"Refusing symlinked global settings path: {component}")


def _decode(raw: object) -> GlobalSettings:
    if not isinstance(raw, dict):
        raise SettingsError("Global settings must be a JSON object")
    required = {"schemaVersion", "lanEnabled"}
    allowed = required | {"lanAddress"}
    if set(raw) - allowed or not required <= set(raw):
        raise SettingsError("Global settings must contain schemaVersion and lanEnabled")
    if raw["schemaVersion"] != SCHEMA_VERSION:
        raise SettingsError("Unsupported global settings schemaVersion")
    return GlobalSettings(lan_enabled=raw["lanEnabled"], lan_address=raw.get("lanAddress"))


def load_settings(path: Path | str | None = None, *, home: Path | str | None = None) -> GlobalSettings:
    """Load settings, defaulting an absent file to enabled automatic discovery."""
    target = Path(path) if path is not None else config_path(home=home)
    _reject_symlinked_path(target)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return GlobalSettings()
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SettingsError(f"Unable to read global settings: {target}") from exc
    return _decode(raw)


def save_settings(settings: GlobalSettings, path: Path | str | None = None, *, home: Path | str | None = None) -> Path:
    """Atomically persist settings and return the target path."""
    if not isinstance(settings, GlobalSettings):
        raise TypeError("settings must be a GlobalSettings instance")
    target = Path(path) if path is not None else config_path(home=home)
    parent = target.parent
    _reject_symlinked_path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    _reject_symlinked_path(parent)
    if target.is_symlink():
        raise SettingsError(f"Refusing symlinked global settings file: {target}")
    temporary: Path | None = None
    try:
        temporary = parent / f".{target.name}.{secrets.token_hex(8)}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(temporary, flags, 0o600)
        try:
            payload = (json.dumps(settings.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            remaining = memoryview(payload)
            while remaining:
                remaining = remaining[os.write(descriptor, remaining):]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, target)
        temporary = None
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
    return target


def update_settings(*, lan_enabled: bool, lan_address: str | None, path: Path | str | None = None,
                    home: Path | str | None = None) -> GlobalSettings:
    """Validate, persist, and return one complete settings object."""
    settings = GlobalSettings(lan_enabled=lan_enabled, lan_address=lan_address)
    save_settings(settings, path, home=home)
    return settings
