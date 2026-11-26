"""Small shared helpers for the PRISM implementation handoff; no product runtime."""
from __future__ import annotations
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone

PACK_ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".prism-state", ".prism-tools-venv"}

def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()

def file_digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()

def receipt_evidence_errors(repo, receipt, *, check_current_plan=True):
    """Check captured observations again; a receipt alone is not current evidence."""
    repo = Path(repo).resolve()
    checks = []
    if receipt.get("planSnapshot"):
        checks.append((receipt["planSnapshot"], receipt.get("planSha256")))
    if receipt.get("sourceSnapshot"):
        checks.append((receipt["sourceSnapshot"], receipt.get("sourceSnapshotSha256")))
    if check_current_plan and receipt.get("planPath"):
        plan_path = Path(receipt["planPath"])
        if not plan_path.is_file() or file_digest(plan_path) != receipt.get("planSha256"):
            checks.append(("__changed_current_plan__", ""))
    review = receipt.get("review")
    if review:
        checks.append((review["path"], review["sha256"]))
        checks.extend((x["path"], x["sha256"]) for x in review.get("evidence", []))
    for command in receipt.get("commands", []):
        checks.append((command["log"], command["logSha256"]))
        checks.extend((x["path"], x["sha256"]) for x in command.get("artifacts", []))
    errors = []
    for relative, expected in checks:
        try:
            if Path(relative).parts[:1] == (".prism-state",):
                state_path(repo, Path(*Path(relative).parts[1:]))
            path = safe_child(repo, relative, must_exist=True)
            if not path.is_file() or file_digest(path) != expected:
                errors.append(f"Missing or changed evidence: {relative}")
        except (ValueError, OSError):
            errors.append(f"Missing or changed evidence: {relative}")
    return errors

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def read_json(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError(f"Non-finite JSON number is not permitted: {value}")
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"Non-finite JSON number is not permitted: {value}")
        return number
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_pairs, parse_constant=reject_constant, parse_float=finite_float)

def atomic_write(path, data, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".prism-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def write_json(path, value):
    atomic_write(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())

def emit(value):
    print(json.dumps(value, indent=2, ensure_ascii=False))

def git(repo, *args, timeout=30):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip() or "Git command failed")
    return result.stdout

def repo_root(path):
    candidate = Path(path).expanduser().resolve(strict=True)
    root = Path(git(candidate, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if root != candidate:
        raise ValueError(f"Use the repository root: {root}")
    return root

def safe_child(root, relative, *, must_exist=False):
    root = Path(root).resolve()
    rel = Path(relative)
    if not str(relative).strip() or rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Expected a relative path inside the repository: {relative}")
    path = root / rel
    resolved = path.resolve(strict=must_exist)
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path leaves the repository: {relative}")
    return resolved

def state_path(root, relative=""):
    """Resolve a private-state path without following any existing symlink.

    The directory is owned by this rebuild, not a configurable output redirect.
    Check again after child programs return before writing their receipts.
    """
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("Private state paths must stay inside .prism-state")
    parts = (".prism-state",) + rel.parts
    current = root
    for index, part in enumerate(parts):
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Private state must not contain a symlink: {current}")
        if current.exists() and (index < len(parts) - 1 or not rel.parts) and not current.is_dir():
            raise ValueError(f"Private state parent must be a directory: {current}")
    if not current.resolve(strict=False).is_relative_to(root):
        raise ValueError("Private state resolves outside the repository")
    return current

def pack_files(root):
    root = Path(root).resolve()
    files = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts) or path.name.endswith((".pyc", ".pyo")):
            continue
        if path.is_symlink():
            raise ValueError(f"Pack must not contain symlinks: {rel}")
        if path.is_file() and rel.as_posix() != "MANIFEST.sha256":
            files.append(path)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())

def verify_manifest(root):
    root = Path(root).resolve()
    manifest = root / "MANIFEST.sha256"
    if not manifest.is_file():
        raise ValueError("MANIFEST.sha256 is missing; this is not a finalized pack")
    expected = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        sha, rel = line.split("  ", 1)
        if rel in expected or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError(f"Invalid manifest entry: {rel}")
        expected[rel] = sha
    actual = {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in pack_files(root)}
    errors = []
    for rel in sorted(set(actual) | set(expected)):
        if rel not in expected:
            errors.append(f"Unexpected pack file: {rel}")
        elif rel not in actual:
            errors.append(f"Missing pack file: {rel}")
        elif actual[rel] != expected[rel]:
            errors.append(f"Hash mismatch: {rel}")
    if errors:
        raise ValueError("; ".join(errors))
    return {"files": len(actual), "manifestSha256": digest(manifest.read_bytes())}

def candidate_snapshot(repo):
    repo = repo_root(repo)
    tracked = set(git(repo, "ls-files", "-z").decode().split("\0")) - {""}
    untracked = set(git(repo, "ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")) - {""}
    def included(name):
        return not any(part in SKIP_PARTS for part in Path(name).parts)
    names = sorted(name for name in tracked | untracked if included(name))
    entries = []
    for name in names:
        p = repo / name
        if p.is_symlink():
            entries.append({"path": name, "kind": "symlink", "sha256": digest(os.readlink(p).encode())})
        elif p.is_file():
            entries.append({"path": name, "kind": "file", "sha256": digest(p.read_bytes()), "executable": bool(p.stat().st_mode & 0o111)})
        elif p.is_dir() and (p / ".git").exists():
            submodule = candidate_snapshot(p)
            entries.append({"path": name, "kind": "submodule", "sha256": submodule["sha256"], "commit": submodule["commit"], "clean": submodule["clean"]})
        else:
            entries.append({"path": name, "kind": "missing-or-nonregular"})
    changed = set(git(repo, "diff", "--name-only", "-z", "HEAD", "--").decode().split("\0")) - {""}
    dirty = sorted(name for name in changed | untracked if included(name))
    body = {"commit": git(repo, "rev-parse", "HEAD").decode().strip(), "entries": entries, "dirtyPaths": dirty, "clean": not dirty}
    return {**body, "sha256": digest(canonical(body))}

def b64(data):
    return base64.b64encode(data).decode("ascii")

def unb64(data):
    return base64.b64decode(data, validate=True)
