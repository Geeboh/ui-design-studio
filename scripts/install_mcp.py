#!/usr/bin/env python3
"""Install the MCP package globally for this user, without project installation.

Run `bash install.sh --mcp-global`. Project options require a separate invocation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PACKAGE = Path(__file__).resolve().parents[1]
MARKER = ".ui-design-mcp-install.json"
COMMANDS = ("ui-design", "ui-design-mcp")


class InstallError(Exception):
    pass


def plain_parents(path: Path) -> None:
    for current in (*reversed(path.parents), path):
        if current.is_symlink():
            raise InstallError(f"Refusing a symlinked managed path: {current}")
        if current.exists() and not current.is_dir():
            raise InstallError(f"Expected a directory: {current}")


def ownership(prefix: Path, user_bin: Path) -> dict:
    return {"schemaVersion": 1, "installer": "ui-design-studio-mcp", "prefix": str(prefix), "userBin": str(user_bin)}


def preflight(prefix: Path, user_bin: Path) -> bool:
    plain_parents(prefix)
    plain_parents(user_bin)
    owned = prefix.exists()
    if owned:
        marker = prefix / MARKER
        if marker.is_symlink() or not marker.is_file():
            raise InstallError(f"Refusing an unmanaged MCP installation prefix: {prefix}")
        try:
            recorded = json.loads(marker.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise InstallError(f"Invalid MCP ownership marker: {marker}") from exc
        if recorded != ownership(prefix, user_bin):
            raise InstallError(f"MCP ownership marker does not match this installation: {marker}")
        # pip must not follow a modified environment into files outside its prefix.
        for directory, directories, files in os.walk(prefix, followlinks=False):
            for name in directories + files:
                path = Path(directory) / name
                if path.is_symlink() and not (path == prefix / "lib64" and os.readlink(path) == "lib"):
                    raise InstallError(f"Refusing a symlinked environment path: {path}")
        for relative in ("pyvenv.cfg", "bin/python"):
            path = prefix / relative
            if not path.is_file() or path.is_symlink():
                raise InstallError(f"Incomplete managed MCP environment: {path}")
        if not os.access(prefix / "bin/python", os.X_OK):
            raise InstallError(f"MCP environment Python is not executable: {prefix / 'bin/python'}")
    for name in COMMANDS:
        link = user_bin / name
        target = prefix / "bin" / name
        if link.is_symlink():
            if not owned or os.readlink(link) != str(target):
                raise InstallError(f"Refusing to replace an unrelated executable: {link}")
        elif link.exists():
            raise InstallError(f"Refusing to replace an unrelated executable: {link}")
    return owned


def install(home: Path) -> tuple[Path, Path]:
    if not home.is_absolute() or not home.is_dir():
        raise InstallError("HOME must be an absolute path to an existing directory.")
    prefix = home / ".local/share/ui-design-studio/mcp"
    user_bin = home / ".local/bin"
    owned = preflight(prefix, user_bin)
    if not owned:
        prefix.parent.mkdir(parents=True, exist_ok=True)
        prefix.mkdir()
        try:
            (prefix / MARKER).write_text(json.dumps(ownership(prefix, user_bin), sort_keys=True) + "\n", encoding="utf-8")
            subprocess.run([sys.executable, "-m", "venv", "--copies", str(prefix)], check=True)
        except BaseException:
            shutil.rmtree(prefix)
            raise
    try:
        preflight(prefix, user_bin)
        subprocess.run([str(prefix / "bin/python"), "-m", "pip", "--isolated", "install", "--upgrade", str(PACKAGE)],
                       env={**os.environ, "PIP_CONFIG_FILE": os.devnull}, check=True)
        preflight(prefix, user_bin)
        for name in COMMANDS:
            executable = prefix / "bin" / name
            if not executable.is_file() or not os.access(executable, os.X_OK):
                raise InstallError(f"Package installation did not create an executable: {executable}")
        user_bin.mkdir(parents=True, exist_ok=True)
        for name in COMMANDS:
            link = user_bin / name
            if not link.is_symlink():
                link.symlink_to(prefix / "bin" / name)
    except BaseException:
        if not owned:
            for name in COMMANDS:
                link = user_bin / name
                if link.is_symlink() and os.readlink(link) == str(prefix / "bin" / name):
                    link.unlink()
            shutil.rmtree(prefix)
        raise
    return prefix, user_bin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-global", action="store_true", required=True,
                        help="Install only the user-global MCP package; run project installation separately")
    parser.parse_args(argv)
    if sys.prefix == sys.base_prefix:
        parser.error("Run bash install.sh --mcp-global, which bootstraps a virtual environment.")
    try:
        home_value = os.environ.get("HOME", "")
        if not home_value:
            raise InstallError("HOME must be set to an absolute path to an existing directory.")
        prefix, user_bin = install(Path(home_value))
    except (InstallError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("Installed the user-global MCP package. No project files or MCP client configurations changed.")
    for name in COMMANDS:
        print(f"  {prefix / 'bin' / name}")
        print(f"  {user_bin / name}")
    print(f"PATH: add {user_bin} to PATH if needed; the absolute executable paths work without it.")
    print("Select each project explicitly with --repo /absolute/project/path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
