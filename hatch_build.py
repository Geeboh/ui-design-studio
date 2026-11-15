"""Reject links instead of dereferencing private files into distributions."""
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        for relative in ("README.md", "LICENSE.txt", "pyproject.toml", "hatch_build.py",
                         "src/ui_design_studio", ".omp/skills", ".omp/agents"):
            root = Path(self.root) / relative
            for parent in (root, *root.parents):
                if parent == Path(self.root):
                    break
                if parent.is_symlink():
                    raise ValueError(f"Symlink is not distributable: {parent.relative_to(self.root)}")
            for path in (root, *root.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"Symlink is not distributable: {path.relative_to(self.root)}")
                if path.name == ".env.example" and path.is_file():
                    relative_path = path.relative_to(self.root)
                    if not any(self.build_config.path_is_excluded(parent.as_posix() + "/")
                               for parent in relative_path.parents):
                        build_data.setdefault("force_include", {})[str(path)] = relative_path.as_posix()
