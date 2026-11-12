"""Load one authoritative engine from the checkout or installed wheel."""
from __future__ import annotations

from functools import lru_cache
import importlib.util
from pathlib import Path
import threading


PACKAGE = Path(__file__).resolve().parent
PAYLOAD = PACKAGE / "payload" if (PACKAGE / "payload").is_dir() else PACKAGE.parents[1] / ".omp"
_LOAD_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _load_studio():
    path = PAYLOAD / "skills/ui-design-studio/scripts/studio.py"
    spec = importlib.util.spec_from_file_location("ui_design_studio_engine", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load UI Design Studio engine: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._design_backend()
    return module


def studio():
    with _LOAD_LOCK:
        return _load_studio()


def backend():
    return studio()._design_backend()
