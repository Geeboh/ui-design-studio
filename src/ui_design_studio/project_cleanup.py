"""Remove project-local UI Design Studio payload while preserving MCP data."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import stat


AGENTS_START = b"<!-- ui-design-studio:start -->"
AGENTS_END = b"<!-- ui-design-studio:end -->"
IGNORE_START = b"# ui-design-studio:start"
IGNORE_END = b"# ui-design-studio:end"
PACKAGE = "ui-design-studio"
INSTALL_STATE = Path(".ui-design-studio/install-state.json")

KNOWN_SKILLS = {
    "ui-design-studio", "ui-assess", "ui-plan", "ui-design", "ui-produce",
    "ui-review", "ui-finalize", "ui-theme", "ui-yolo",
}


class CleanupError(Exception):
    pass


@dataclass(frozen=True)
class CleanupPlan:
    remove: tuple[str, ...]
    rewrite: tuple[tuple[str, bytes], ...]
    conflicts: tuple[str, ...]
    preserve: tuple[str, ...]

    @property
    def changed(self) -> int:
        return len(self.remove) + len(self.rewrite)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_relative(raw: object) -> str:
    if not isinstance(raw, str):
        raise CleanupError("Invalid managed path")
    path = Path(raw)
    if path.is_absolute() or not raw or ".." in path.parts:
        raise CleanupError(f"Unsafe managed path: {raw!r}")
    return path.as_posix()


def _load_state(root: Path) -> dict:
    path = root / INSTALL_STATE
    if not path.is_file():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise CleanupError(f"Invalid install state: {path}") from exc
    if state.get("package") != PACKAGE or not isinstance(state.get("managedFiles"), dict):
        raise CleanupError(f"Unrecognized install state: {path}")
    state["managedFiles"] = {_safe_relative(key): value for key, value in state["managedFiles"].items()}
    return state


def _strip_block(data: bytes, start: bytes, end: bytes) -> bytes:
    begin = data.find(start)
    if begin < 0:
        return data
    finish = data.find(end, begin + len(start))
    if finish < 0:
        raise CleanupError("Unclosed UI Design Studio block")
    finish += len(end)
    if finish < len(data) and data[finish:finish + 2] == b"\r\n":
        finish += 2
    elif finish < len(data) and data[finish:finish + 1] == b"\n":
        finish += 1
    return data[:begin] + data[finish:]


def _candidate_paths(root: Path, state: dict) -> set[str]:
    if state:
        return set(state.get("managedFiles", {}))
    return {
        ".omp/extensions/ui-design-progress.ts",
        ".omp/commands/ui-design.md",
        ".omp/commands/ui-yolo.md",
        "tools/ui-design",
    }


def plan_cleanup(root: Path, *, purge_backups: bool = False) -> CleanupPlan:
    if not root.is_absolute() or not root.is_dir():
        raise CleanupError("--repo must be an absolute existing project directory")
    state = _load_state(root)
    managed = state.get("managedFiles", {})
    remove: set[str] = set()
    conflicts: set[str] = set()
    for relative in _candidate_paths(root, state):
        if relative == "ui-design-studio.json":
            continue
        path = root / relative
        if not path.exists() and not path.is_symlink():
            continue
        if path.is_dir() and not path.is_symlink():
            continue
        record = managed.get(relative)
        if isinstance(record, dict):
            if path.is_symlink() or not path.is_file():
                conflicts.add(relative)
                continue
            expected = record.get("sha256")
            expected_mode = record.get("mode")
            if (
                not isinstance(expected, str)
                or _digest(path) != expected
                or not isinstance(expected_mode, int)
                or stat.S_IMODE(path.stat().st_mode) != expected_mode
            ):
                conflicts.add(relative)
                continue
        remove.add(relative)

    rewrite: dict[str, bytes] = {}
    for relative, start, end in (
        ("AGENTS.md", AGENTS_START, AGENTS_END),
        (".gitignore", IGNORE_START, IGNORE_END),
    ):
        path = root / relative
        if path.is_file():
            after = _strip_block(path.read_bytes(), start, end)
            if after != path.read_bytes():
                rewrite[relative] = after

    if (root / INSTALL_STATE).is_file():
        remove.add(INSTALL_STATE.as_posix())
    if (root / ".venv-ui-design").exists():
        remove.add(".venv-ui-design")
    if purge_backups and (root / ".ui-design-studio/backups").exists():
        remove.add(".ui-design-studio/backups")

    preserve = [".ui-design-studio/runtime", "docs/design/runs", "ui-design-studio.json"]
    if not purge_backups:
        preserve.append(".ui-design-studio/backups")
    return CleanupPlan(tuple(sorted(remove)), tuple(sorted(rewrite.items())), tuple(sorted(conflicts)), tuple(preserve))


def execute_cleanup(root: Path, plan: CleanupPlan) -> None:
    if plan.conflicts:
        raise CleanupError("Edited installer-managed files require manual review: " + ", ".join(plan.conflicts))
    for relative, data in plan.rewrite:
        path = root / relative
        path.write_bytes(data)
    for relative in sorted(plan.remove, key=lambda value: len(Path(value).parts), reverse=True):
        path = root / relative
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()


def cleanup_project(root: Path, *, apply: bool, purge_backups: bool) -> dict:
    plan = plan_cleanup(root, purge_backups=purge_backups)
    applied = False
    if apply and not plan.conflicts:
        execute_cleanup(root, plan)
        applied = True
    return {
        "status": "PASS" if not plan.conflicts else "CONFLICT",
        "applied": applied,
        "changed": plan.changed,
        "removed": list(plan.remove),
        "rewritten": [relative for relative, _ in plan.rewrite],
        "conflicts": list(plan.conflicts),
        "preserved": plan.preserve,
    }
