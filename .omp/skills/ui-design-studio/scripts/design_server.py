#!/usr/bin/env python3
"""Live design records, immutable previews, authenticated approvals and owned cleanup.

Gate semantics are deliberately conservative. Assessment needs current resolved
context/routing and a complete valid inventory. Plan needs a current approved
Plan decision. Design also needs every required mockup and current Design
approval. Produce additionally needs every implementation and fresh passed QA,
all required fresh evidence and independent review. Finalize additionally needs
studio.check_run to return PASS now. Missing requirements remain pending;
malformed, stale, rejected or explicitly failed inputs fail their gate. Fresh QA
means valid reviewer metadata and matching current report/input hashes. These
counts prove file/hash completeness, not that a reported review is truthful.

HTML, SVG, CSS and their local visual/font dependencies are retained together.
Previews have a separate capability, an opaque sandbox origin and no scripts.
They are not a runnable replica of a scripted application.
Explicit artwork publication retains bytes before acknowledging an ID/version.
Manifests retain capture time; a separate index orders current publications,
including content reverts. Cleanup keeps inert OS-lock coordination files.
Status command success means the records were read, not that gates passed.
Public aliases use one address generation for request validation and metadata.
LAN updates replace advertised URLs, permitted Hosts and permitted Origins.
"""
from __future__ import annotations

from contextlib import contextmanager
import datetime as dt
import errno
import hashlib
from html import escape
from html.parser import HTMLParser
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import signal
import socket
import tempfile
import threading
import time
from typing import NamedTuple
from urllib.parse import quote, unquote, urlsplit, urlunsplit
import xml.etree.ElementTree as ET


VISUAL = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".html", ".htm", ".pdf"}
DEPENDENCIES = VISUAL | {".css", ".woff", ".woff2", ".ttf", ".otf", ".eot"}
STATUSES = {"active", "done", "blocked", "failed", "pending"}
DOWNSTREAM_STAGES = {"plan": ("design", "finalize"), "design": ("finalize",)}
EXCLUDED = {"artwork-library", "artwork-metadata", "approval-requests", "workers", "__pycache__", "node_modules", ".git", ".cache", "cache", "runtime"}
CSS_URL = re.compile(r"url\(\s*(?P<quote>['\"]?)(?P<url>.*?)\1\s*\)", re.I | re.S)
CSS_IMPORT = re.compile(r"@import\s+(['\"])(.*?)\1", re.I)
SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
MAX_BODY = 128 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def need(studio, condition, message):
    studio.require(condition, message)


def read_record(studio, root, relative, default=None):
    path = studio.safe_path(root, relative, must_exist=False)
    try:
        return studio.read_json(path)
    except studio.StudioError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            return default
        raise


class FileLock:
    def __init__(self, path, studio, blocking=False):
        self.path, self.studio, self.blocking = Path(path), studio, blocking
        self.handle = None
        self.contended = False

    def __enter__(self):
        need(self.studio, not self.path.is_symlink(), f"Lock cannot be a symlink: {self.path}")
        self.handle = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.handle.seek(0)
                if self.path.stat().st_size == 0:
                    self.handle.write(b"0")
                    self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_LOCK if self.blocking else msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle, fcntl.LOCK_EX | (0 if self.blocking else fcntl.LOCK_NB))
        except OSError as exc:
            self.handle.close()
            self.handle = None
            self.contended = exc.errno in (errno.EACCES, errno.EAGAIN, errno.EWOULDBLOCK)
            message = "Design records are locked by another owner" if self.contended else "Cannot lock design records"
            raise self.studio.StudioError(f"{message}: {self.path}") from exc
        return self

    def __exit__(self, *unused):
        if self.handle:
            if os.name == "nt":
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle, fcntl.LOCK_UN)
            self.handle.close()
            self.handle = None


@contextmanager
def records_lock(studio, root):
    with FileLock(Path(root) / ".design-records.lock", studio, blocking=True):
        yield


def private_json(studio, path, value):
    studio.atomic_json(path, value)
    os.chmod(path, 0o600)


def local_reference(studio, root, source, value):
    value = value.strip()
    if not value or value.startswith("#"):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
        return None
    path = PurePosixPath(source).parent / unquote(parsed.path)
    parts = []
    for part in path.parts:
        if part == "..":
            if not parts:
                return None
            parts.pop()
        elif part != ".":
            parts.append(part)
    if not parts:
        return None
    relative = "/".join(parts)
    if any(part in EXCLUDED or part.startswith(".") for part in PurePosixPath(relative).parts):
        return None
    if Path(relative).suffix.lower() not in DEPENDENCIES:
        return None
    studio.safe_path(root, relative)
    return relative


class References(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.references = []
        self.styles = []
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("src", "poster", "background", "href", "xlink:href"):
            if attrs.get(key) and tag not in ("script", "a", "base", "iframe", "object", "embed"):
                self.references.append(attrs[key])
        if attrs.get("srcset"):
            self.references.extend(item.strip().split()[0] for item in attrs["srcset"].split(",") if item.strip())
        self.styles.extend(value for key, value in attrs.items() if value and (key == "style" or "url(" in value.lower()))
        self.in_style = tag == "style"

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.styles.append(data)


def dependency_bundle(studio, root, inputs, warnings=None):
    """Return original bytes keyed by every explicit input and local dependency."""
    need(studio, isinstance(inputs, list) and inputs and all(isinstance(p, str) for p in inputs), "Inputs must be a nonempty path list")
    pending, files = list(inputs), {}
    while pending:
        relative = pending.pop()
        path = studio.safe_path(root, relative)
        relative = path.relative_to(root).as_posix()
        if relative in files:
            continue
        content = path.read_bytes()
        files[relative] = content
        suffix = path.suffix.lower()
        references = []
        styles = []
        if suffix in (".html", ".htm", ".svg"):
            parser = References()
            parser.feed(content.decode("utf-8"))
            references.extend(parser.references)
            styles.extend(parser.styles)
        elif suffix == ".css":
            styles.append(content.decode("utf-8"))
        for style in styles:
            references.extend(match.group("url") for match in CSS_URL.finditer(style))
            references.extend(match.group(2) for match in CSS_IMPORT.finditer(style))
        for reference in references:
            try:
                target = local_reference(studio, root, relative, reference)
            except (studio.StudioError, OSError, ValueError) as exc:
                if warnings is None:
                    raise
                warnings.append(f"Preview dependency {relative}: {exc}")
                continue
            if target and target not in files:
                pending.append(target)
    return files


def expanded_inputs(studio, root, files):
    return sorted(dependency_bundle(studio, root, files))


def publish_progress(studio, root, next_action=None, blockers=None):
    root = checked_root(studio, root)
    with records_lock(studio, root):
        record = read_record(studio, root, "progress.json", {"schemaVersion": "1.0", "tasks": [], "nextAction": "", "blockers": []})
        need(studio, isinstance(record, dict), "progress.json must be an object")
        if next_action is not None:
            record["nextAction"] = next_action
        if blockers is not None:
            record["blockers"] = [text for text in blockers if text.strip()]
        record["updatedAt"] = timestamp()
        studio.atomic_json(studio.safe_path(root, "progress.json", must_exist=False), record)
    return {"status": "PASS", "file": str(root / "progress.json")}


def publish_worker(studio, root, worker_id, task, status, message, model=None):
    root = checked_root(studio, root)
    need(studio, isinstance(worker_id, str) and SLUG.fullmatch(worker_id) and len(worker_id) <= 64, "Worker ID must be a portable lowercase slug")
    need(studio, status in STATUSES and task.strip(), "Worker needs a task and valid status")
    record = {"id": worker_id, "task": task, "status": status, "message": message, "updatedAt": timestamp()}
    if model:
        record["model"] = model
    with records_lock(studio, root):
        studio.atomic_json(studio.safe_path(root, f"workers/{worker_id}.json", must_exist=False), record)
    return {"status": "PASS", "worker": record}


def project_theme(studio, root, repo=None):
    root = Path(root).resolve()
    run = studio.read_json(studio.safe_path(root, "run.json"))
    studio.validate_slug(run.get("themeId"))
    candidates = [Path(repo).resolve()] if repo else root.parents
    for candidate in candidates:
        try:
            unused, themes, runs = studio.config_paths(candidate)
            if root != runs and root.is_relative_to(runs):
                theme = studio.safe_path(themes, run["themeId"], must_exist=False, allow_dir=True)
                return candidate, theme, run["themeId"]
        except (studio.StudioError, OSError, ValueError):
            if repo:
                raise
    need(studio, repo is None, "Run must belong to the selected project's configured runs directory")
    return None


def import_theme_art(studio, root, repo=None):
    project = project_theme(studio, root, repo)
    if project is None:
        return None
    repository, theme, theme_id = project
    files = {}
    if theme.exists():
        for directory, dirs, names in os.walk(theme, followlinks=False):
            base = Path(directory)
            dirs[:] = sorted(name for name in dirs if name not in EXCLUDED and not name.startswith(".") and not (base / name).is_symlink())
            for name in sorted(names):
                source = base / name
                if source.is_symlink() or name.startswith(".") or source.suffix.lower() not in DEPENDENCIES:
                    continue
                relative = source.relative_to(theme).as_posix()
                source = studio.safe_path(theme, relative)
                content = source.read_bytes()
                imported = f"theme-artwork/{theme_id}/{relative}"
                output = studio.safe_path(root, imported, must_exist=False)
                output.parent.mkdir(parents=True, exist_ok=True)
                if not output.exists() or output.read_bytes() != content:
                    studio.atomic_bytes(output, content, 0o600)
                files[imported] = digest(content)
    record = {"schemaVersion": "1.0", "projectRoot": str(repository),
              "themePath": theme.relative_to(repository).as_posix(), "files": files}
    path = studio.safe_path(root, ".design-theme-sources.json", must_exist=False)
    if not path.exists() or studio.read_json(path) != record:
        studio.atomic_json(path, record)
    return record


def bind_theme_sources(studio, root, inputs, source_record):
    imported = [path for path in inputs if path.startswith("theme-artwork/")]
    if imported:
        need(studio, isinstance(source_record, dict) and all(path in source_record["files"] and studio.sha_file(studio.safe_path(root, path)) == source_record["files"][path] for path in imported),
             "Imported theme input is no longer a current original project artifact")
        inputs = sorted(set([*inputs, ".design-theme-sources.json"]))
    return inputs


def publish_artwork(studio, root, relative, context, title=None, repo=None):
    root = checked_root(studio, root)
    with records_lock(studio, root):
        import_theme_art(studio, root, repo)
        if repo:
            repository, theme, theme_id = project_theme(studio, root, repo)
            original = studio.safe_path(repository, relative)
            need(studio, original.is_relative_to(theme), "Explicit project publication is limited to the active theme directory")
            relative = f"theme-artwork/{theme_id}/" + original.relative_to(theme).as_posix()
        path = studio.safe_path(root, relative)
        relative = path.relative_to(root).as_posix()
        need(studio, path.suffix.lower() in VISUAL and context.strip(), "Artwork needs a supported visual file and nonempty context")
        need(studio, not any(part in EXCLUDED or part.startswith(".") for part in PurePosixPath(relative).parts), "Artwork must be an original run artifact")
        key = digest(relative.encode())
        metadata = {"path": relative, "title": title or path.name, "context": context, "updatedAt": timestamp()}
        studio.atomic_json(studio.safe_path(root, f"artwork-metadata/{key}.json", must_exist=False), metadata)
        retained, unused_warnings = ArtworkLibrary(studio, root, repo).retain(relative)
    return {"status": "PASS", "artwork": retained}


def checked_root(studio, root):
    root = Path(root).resolve()
    run = studio.read_json(studio.safe_path(root, "run.json"))
    need(studio, isinstance(run, dict), "run.json must be an object")
    return root


def latest_decisions(studio, root):
    record = studio.read_json(studio.safe_path(root, "decisions.json"))
    need(studio, isinstance(record, dict) and record.get("schemaVersion") == "1.0" and isinstance(record.get("decisions"), list), "Invalid decisions record")
    latest = {}
    for item in record["decisions"]:
        need(studio, isinstance(item, dict) and item.get("stage") in ("plan", "design", "finalize"), "Invalid decision entry")
        latest[item["stage"]] = item
    return record, latest


def current_decision(studio, root, run, decision):
    if not decision or decision.get("outcome") != "approved":
        return False
    actor = decision.get("actor")
    if actor not in ("user", "agent-yolo") or (run.get("mode") == "guided" and actor != "user"):
        return False
    if not isinstance(decision.get("rationale"), str) or not decision["rationale"].strip():
        return False
    return decision.get("inputsDigest") == studio.file_digest(root, decision.get("inputs"))


def publish_request(studio, root, request_id, stage, title, context, files, choices=None):
    root = checked_root(studio, root)
    need(studio, isinstance(request_id, str) and SLUG.fullmatch(request_id) and len(request_id) <= 64, "Approval ID must be a portable lowercase slug")
    need(studio, stage in ("plan", "design") and title.strip() and context.strip(), "Approval needs a stage, title and review context")
    with records_lock(studio, root):
        source_record = import_theme_art(studio, root)
        run = studio.read_json(root / "run.json")
        decisions, latest = latest_decisions(studio, root)
        inputs = list(files)
        context_path = run.get("projectContext", {}).get("path") if isinstance(run.get("projectContext"), dict) else None
        if context_path:
            inputs.append(context_path)
        if stage == "design":
            plan = latest.get("plan")
            need(studio, current_decision(studio, root, run, plan), "Design requests require a current approved Plan decision")
            inputs.extend(plan["inputs"])
        inputs = expanded_inputs(studio, root, inputs)
        inputs = bind_theme_sources(studio, root, inputs, source_record)
        library = ArtworkLibrary(studio, root)
        available, unused_warnings = library.discover()
        current_art = library.publication_index()["current"]
        owned_art = {}
        for art in available:
            if current_art.get(art["path"]) == art["version"] and art["path"] in inputs and all(path in inputs and studio.sha_file(studio.safe_path(root, path)) == value for path, value in art["files"].items()):
                owned_art[art["id"]] = art
        if choices is None:
            choices = [{"id": "approve", "label": "Approve current artifacts", "artworkIds": list(owned_art)},
                       {"id": "request-changes", "label": "Request changes", "artworkIds": []}]
        need(studio, isinstance(choices, list) and len(choices) >= 2, "Choices must contain at least two review options")
        seen = set()
        for option in choices:
            need(studio, isinstance(option, dict) and isinstance(option.get("id"), str) and SLUG.fullmatch(option["id"]) and option["id"] not in seen, "Options require unique slug IDs")
            need(studio, isinstance(option.get("label"), str) and option["label"].strip(), "Options require labels")
            need(studio, isinstance(option.get("artworkIds", []), list) and all(isinstance(x, str) for x in option.get("artworkIds", [])), "Option artworkIds must be a string list")
            need(studio, all(art_id in owned_art for art_id in option.get("artworkIds", [])), "Option artworkIds must refer to current request-owned artifact versions")
            option.setdefault("artworkIds", [])
            seen.add(option["id"])
        request = {"schemaVersion": "1.0", "id": request_id, "stage": stage, "title": title, "context": context,
                   "inputs": inputs, "inputsDigest": studio.file_digest(root, inputs), "options": choices,
                   "decisionsDigest": digest(canonical(decisions)), "runDigest": digest(canonical(run)),
                   "createdAt": timestamp(), "status": "pending"}
        path = studio.safe_path(root, f"approval-requests/{request_id}.json", must_exist=False)
        if path.exists():
            existing = studio.read_json(path)
            ignored = {"createdAt", "status"}
            need(studio, {key: value for key, value in existing.items() if key not in ignored} == {key: value for key, value in request.items() if key not in ignored},
                 "Approval request IDs are immutable; publish a new ID after any review input, context, option or decision change")
            return {"status": "PASS", "request": existing}
        studio.atomic_json(studio.safe_path(root, f"approval-requests/{request_id}.json", must_exist=False), request)
    return {"status": "PASS", "request": request}


class ApprovalConflict(Exception):
    pass


def approve(studio, root, payload):
    need(studio, isinstance(payload, dict), "Approval body must be an object")
    request_id = payload.get("id")
    need(studio, isinstance(request_id, str) and SLUG.fullmatch(request_id), "Invalid approval ID")
    with records_lock(studio, root):
        source_record = import_theme_art(studio, root)
        run = studio.read_json(root / "run.json")
        need(studio, run.get("mode") == "guided", "Yolo mode does not accept human approval forms")
        request = studio.read_json(studio.safe_path(root, f"approval-requests/{request_id}.json"))
        decisions, latest = latest_decisions(studio, root)
        try:
            current_inputs = expanded_inputs(studio, root, request["inputs"])
            current_inputs = bind_theme_sources(studio, root, current_inputs, source_record)
            fresh = (current_inputs == request["inputs"] and studio.file_digest(root, current_inputs) == request["inputsDigest"]
                     and digest(canonical(decisions)) == request["decisionsDigest"] and digest(canonical(run)) == request["runDigest"])
        except (studio.StudioError, OSError, UnicodeError, ValueError, KeyError):
            fresh = False
        if not fresh or payload.get("inputsDigest") != request.get("inputsDigest"):
            raise ApprovalConflict("Review inputs or decisions changed; refresh the approval request and review again")
        option = next((item for item in request["options"] if item["id"] == payload.get("optionId")), None)
        need(studio, option is not None, "Unknown approval option")
        need(studio, payload.get("outcome") in ("approved", "rejected"), "Approval outcome must be approved or rejected")
        need(studio, isinstance(payload.get("rationale"), str) and payload["rationale"].strip(), "A review rationale is required")
        need(studio, payload.get("optionId") != "request-changes" or payload.get("outcome") == "rejected", "Request changes cannot grant approval")
        if request["stage"] == "design":
            plan = latest.get("plan")
            if not current_decision(studio, root, run, plan) or not set(plan["inputs"]).issubset(request["inputs"]):
                raise ApprovalConflict("The approved Plan changed; publish and review the Design request again")
        decision = {"stage": request["stage"], "actor": "user", "outcome": payload["outcome"],
                    "rationale": payload["rationale"].strip(), "inputs": request["inputs"], "inputsDigest": request["inputsDigest"],
                    "optionId": option["id"], "requestId": request_id, "recordedAt": timestamp()}
        decisions["decisions"].append(decision)
        for stage in DOWNSTREAM_STAGES[request["stage"]]:
            if latest.get(stage, {}).get("outcome") == "approved":
                decisions["decisions"].append({"stage": stage, "actor": "user", "outcome": "superseded",
                    "rationale": f"Superseded by the new {request['stage'].title()} review; downstream approval must be renewed.",
                    "recordedAt": timestamp(), "supersededByRequestId": request_id})
        studio.atomic_json(studio.safe_path(root, "decisions.json"), decisions)
    return {"status": "PASS", "decision": decision}


class ArtworkLibrary:
    def __init__(self, studio, root, repo=None):
        self.studio, self.root, self.repo = studio, Path(root), repo
        self.directory = studio.safe_path(root, "artwork-library", must_exist=False, allow_dir=True)

    def publication_index(self):
        index = read_record(self.studio, self.directory, "index.json", {"schemaVersion": "1.0", "current": {}, "versions": []})
        need(self.studio, isinstance(index, dict) and index.get("schemaVersion") == "1.0"
             and isinstance(index.get("current"), dict) and isinstance(index.get("versions"), list)
             and all(isinstance(key, str) and isinstance(value, str) and HASH.fullmatch(value) for key, value in index["current"].items())
             and all(isinstance(value, str) and HASH.fullmatch(value) for value in index["versions"])
             and len(index["versions"]) == len(set(index["versions"])), "Invalid artwork publication index")
        return index

    def remember(self, relative, version):
        index = self.publication_index()
        if index["current"].get(relative) == version and version in index["versions"]:
            return
        index["current"][relative] = version
        index["versions"] = [value for value in index["versions"] if value != version] + [version]
        self.studio.atomic_json(self.studio.safe_path(self.directory, "index.json", must_exist=False), index)

    def retain(self, relative, strict=True):
        studio, root = self.studio, self.root
        warnings = []
        source = studio.safe_path(root, relative)
        need(studio, source.suffix.lower() in VISUAL, "Only visual artifacts may be retained")
        bundle = dependency_bundle(studio, root, [relative], None if strict else warnings)
        metadata = read_record(studio, root, f"artwork-metadata/{digest(relative.encode())}.json", {})
        need(studio, isinstance(metadata, dict), "Artwork metadata must be an object")
        title = metadata.get("title") or source.name
        context = metadata.get("context") or f"Design artifact generated at {relative}."
        hashes = {key: digest(value) for key, value in sorted(bundle.items())}
        version = digest(canonical({"path": relative, "files": hashes, "title": title, "context": context}))
        target = studio.safe_path(root, f"artwork-library/{version}", must_exist=False, allow_dir=True)
        if target.exists():
            record = studio.read_json(studio.safe_path(target, "manifest.json"))
            need(studio, record.get("files") == hashes and record.get("path") == relative and record.get("version") == version, "Existing immutable artwork manifest changed")
            if strict:
                for path in hashes:
                    self.file(version, path)
            self.remember(relative, version)
            return record, warnings
        record = {"id": digest(relative.encode())[:16] + "-" + version[:16], "path": relative, "title": title,
                  "context": context, "kind": "html" if source.suffix.lower() in (".html", ".htm") else "pdf" if source.suffix.lower() == ".pdf" else "image",
                  "createdAt": timestamp(), "version": version, "files": hashes}
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".capture-", dir=self.directory))
        try:
            for path, content in bundle.items():
                output = studio.safe_path(temporary, f"files/{path}", must_exist=False)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(content)
            studio.atomic_json(temporary / "manifest.json", record)
            temporary.rename(target)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
        self.remember(relative, version)
        return record, warnings

    def discover(self):
        studio, root = self.studio, self.root
        warnings = []
        import_theme_art(studio, root, self.repo)
        for directory, dirs, names in os.walk(root, followlinks=False):
            base = Path(directory)
            dirs[:] = sorted(name for name in dirs if name not in EXCLUDED and not name.startswith(".") and not (base / name).is_symlink())
            for name in sorted(names):
                source = base / name
                if source.is_symlink() or source.suffix.lower() not in VISUAL or name.startswith("."):
                    continue
                relative = source.relative_to(root).as_posix()
                try:
                    unused_record, dependency_warnings = self.retain(relative, strict=False)
                    warnings.extend(dependency_warnings)
                except (studio.StudioError, OSError, UnicodeError, ValueError, TypeError) as exc:
                    warnings.append(f"Artwork {relative}: {exc}")
        return self.records(), warnings

    def records(self):
        if not self.directory.exists():
            return []
        records = []
        for path in sorted(self.directory.iterdir()):
            if path.is_symlink() or not path.is_dir() or not HASH.fullmatch(path.name):
                continue
            try:
                record = self.studio.read_json(self.studio.safe_path(path, "manifest.json"))
                if record.get("version") == path.name and isinstance(record.get("files"), dict):
                    records.append(record)
            except (self.studio.StudioError, OSError, ValueError, TypeError):
                continue
        order = {version: position for position, version in enumerate(self.publication_index()["versions"])}
        return sorted(records, key=lambda item: (item["version"] in order, order.get(item["version"], -1), item["createdAt"], item["path"], item["version"]))

    def file(self, version, relative):
        need(self.studio, isinstance(version, str) and HASH.fullmatch(version), "Invalid artwork version")
        directory = self.studio.safe_path(self.directory, version, allow_dir=True)
        record = self.studio.read_json(self.studio.safe_path(directory, "manifest.json"))
        need(self.studio, relative in record.get("files", {}) and Path(relative).suffix.lower() in DEPENDENCIES, "File is not a published visual dependency")
        path = self.studio.safe_path(directory, "files/" + relative)
        content = path.read_bytes()
        need(self.studio, digest(content) == record["files"][relative], "Immutable artwork bytes changed")
        return record, content


def rewrite_url(studio, root, source, value, files, prefix):
    if re.fullmatch(r"data:(?:image/(?:png|jpeg|gif|webp|avif)|font/(?:woff2?|ttf|otf));base64,[A-Za-z0-9+/=\s]+", value.strip(), re.I):
        return value.strip()
    if value.strip().startswith("#"):
        return value
    try:
        target = local_reference(studio, root, source, value)
    except (studio.StudioError, OSError, ValueError):
        target = None
    if target not in files:
        return ""
    fragment = urlsplit(value).fragment
    return prefix + quote(target, safe="/") + ("#" + quote(fragment) if fragment else "")


def safe_css(studio, root, source, content, files, prefix):
    def url(match):
        target = rewrite_url(studio, root, source, match.group("url"), files, prefix)
        return 'url("' + target.replace('"', "%22") + '")'
    content = CSS_URL.sub(url, content)
    content = CSS_IMPORT.sub(lambda m: '@import "' + rewrite_url(studio, root, source, m.group(2), files, prefix) + '"', content)
    return content


class SafeHTML(HTMLParser):
    BLOCKED = {"script", "iframe", "frame", "frameset", "object", "embed", "base", "portal", "noscript", "set", "animate", "animatetransform", "animatemotion"}
    URL_ATTRS = {"src", "href", "poster", "background", "xlink:href"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, studio, root, source, files, prefix):
        super().__init__(convert_charrefs=False)
        self.studio, self.root, self.source, self.files, self.prefix = studio, root, source, files, prefix
        self.output, self.blocked = [], []
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        if self.blocked:
            if tag in self.BLOCKED and tag not in self.VOID:
                self.blocked.append(tag)
            return
        if tag in self.BLOCKED:
            if tag not in self.VOID:
                self.blocked.append(tag)
            return
        if tag == "meta" and any(key.lower() == "http-equiv" for key, value in attrs):
            return
        clean = []
        for key, value in attrs:
            key = key.lower()
            if key.startswith("on") or key in ("srcdoc", "action", "formaction", "ping", "target", "download", "nonce", "integrity", "xml:base"):
                continue
            if key in ("href", "xlink:href") and tag not in ("link", "use", "image"):
                continue
            if value is not None and key in self.URL_ATTRS:
                value = rewrite_url(self.studio, self.root, self.source, value, self.files, self.prefix)
            elif value is not None and key == "srcset":
                candidates = []
                for item in value.split(","):
                    parts = item.strip().split()
                    if parts:
                        url = rewrite_url(self.studio, self.root, self.source, parts[0], self.files, self.prefix)
                        if url:
                            candidates.append(" ".join([url, *parts[1:]]))
                value = ", ".join(candidates)
            elif value is not None and key == "style":
                value = safe_css(self.studio, self.root, self.source, value, self.files, self.prefix)
            clean.append(key if value is None else key + '="' + escape(value, quote=True) + '"')
        self.output.append("<" + tag + (" " + " ".join(clean) if clean else "") + ">")
        self.in_style = tag == "style"

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.blocked:
            if tag == self.blocked[-1]:
                self.blocked.pop()
            return
        if tag not in self.BLOCKED and tag not in self.VOID:
            self.output.append("</" + tag + ">")
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if not self.blocked:
            self.output.append(safe_css(self.studio, self.root, self.source, data, self.files, self.prefix) if self.in_style else data)

    def handle_entityref(self, name):
        if not self.blocked:
            self.output.append("&" + name + ";")

    def handle_charref(self, name):
        if not self.blocked:
            self.output.append("&#" + name + ";")

    def handle_decl(self, decl):
        self.output.append("<!doctype html>")


def safe_svg(studio, root, source, content, files, prefix):
    document = ET.fromstring(content)
    forbidden = {"script", "foreignobject", "iframe", "object", "embed", "animate", "animatetransform", "animatemotion", "set"}
    for parent in document.iter():
        for child in list(parent):
            if child.tag.rsplit("}", 1)[-1].lower() in forbidden:
                parent.remove(child)
        for key, value in list(parent.attrib.items()):
            local = key.rsplit("}", 1)[-1].lower()
            if local.startswith("on") or local == "base" or (local == "href" and parent.tag.rsplit("}", 1)[-1].lower() == "a"):
                del parent.attrib[key]
            elif local in ("href", "src"):
                parent.attrib[key] = rewrite_url(studio, root, source, value, files, prefix)
            elif local == "style" or "url(" in value.lower():
                parent.attrib[key] = safe_css(studio, root, source, value, files, prefix)
        if parent.tag.rsplit("}", 1)[-1].lower() == "style" and parent.text:
            parent.text = safe_css(studio, root, source, parent.text, files, prefix)
    return ET.tostring(document, encoding="utf-8", xml_declaration=True)


def fresh_evidence(studio, root, entry):
    if not isinstance(entry, dict) or entry.get("status") != "passed" or not all(isinstance(entry.get(key), str) and entry[key].strip() for key in ("id", "kind", "reviewer", "recordedAt")):
        return False
    try:
        if studio.sha_file(studio.safe_path(root, entry.get("path"))) != entry.get("sha256"):
            return False
        if "inputs" in entry:
            return studio.file_digest(root, entry["inputs"]) == entry.get("inputsDigest")
        return True
    except (studio.StudioError, OSError, ValueError, TypeError):
        return False


def coverage_counts(studio, root, coverage, evidence):
    required = mockups = verified = 0
    valid = isinstance(coverage, dict) and coverage.get("schemaVersion") == "1.0" and isinstance(coverage.get("surfaces"), list)
    surfaces = coverage.get("surfaces", []) if valid else []
    valid = valid and bool(surfaces)
    seen = set()
    evidence_ids = {}
    for entry in evidence:
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            if entry["id"] in evidence_ids:
                evidence_ids[entry["id"]] = None
            else:
                evidence_ids[entry["id"]] = entry
    for surface in surfaces:
        if not isinstance(surface, dict):
            valid = False
            continue
        states, viewports = surface.get("states"), surface.get("viewports")
        sid = surface.get("id")
        shape = (isinstance(sid, str) and sid and sid not in seen and surface.get("kind") in ("page", "dialog")
                 and isinstance(surface.get("route"), str) and bool(surface["route"].strip())
                 and all(isinstance(items, list) and items and all(isinstance(x, str) and x for x in items)
                         and len(items) == len(set(items)) for items in (states, viewports)))
        if not shape:
            valid = False
            continue
        seen.add(sid)
        required += len(states) * len(viewports)
        cases = surface.get("cases", [])
        if not isinstance(cases, list):
            valid = False
            continue
        expected = {(state, viewport) for state in states for viewport in viewports}
        grouped = {}
        for case in cases:
            if not isinstance(case, dict) or not isinstance(case.get("state"), str) or not isinstance(case.get("viewport"), str):
                valid = False
                continue
            key = (case["state"], case["viewport"])
            grouped.setdefault(key, []).append(case)
            if key not in expected:
                valid = False
        for key in expected:
            values = grouped.get(key, [])
            if len(values) != 1:
                if len(values) > 1:
                    valid = False
                continue
            case = values[0]
            try:
                studio.safe_path(root, case.get("mockup"))
                mockups += 1
                studio.safe_path(root, case.get("implementation"))
                qa = case.get("qaEvidence")
                if isinstance(qa, list) and qa and all(isinstance(eid, str) and fresh_evidence(studio, root, evidence_ids.get(eid)) for eid in qa):
                    verified += 1
            except (studio.StudioError, OSError, ValueError, TypeError):
                continue
    return {"required": required, "mockups": mockups, "verified": verified, "inventoryComplete": valid and coverage.get("inventoryComplete") is True}, valid


def task_records(record):
    if not isinstance(record, dict):
        return []
    tasks = record.get("tasks", [])
    if not isinstance(tasks, list):
        return []
    result = []
    for item in tasks:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("title"), str) or not isinstance(item.get("status"), str):
            continue
        task = {key: item[key] for key in ("id", "title", "status")}
        progress = item.get("progress")
        if isinstance(progress, (int, float)) and not isinstance(progress, bool) and 0 <= progress <= 100:
            task["progress"] = progress
        if isinstance(item.get("nextAction"), str):
            task["nextAction"] = item["nextAction"]
        result.append(task)
    return result


class ServerAddresses(NamedTuple):
    """Keep metadata and request validation on one immutable address generation."""

    url: str
    local_url: str | None
    lan_urls: tuple[str, ...]
    bases: tuple[str, ...] = ()
    origins: frozenset[str] = frozenset()


class DesignState:
    def __init__(self, studio, root, url="", preview_capability="", repo=None, *, addresses=None):
        self.studio, self.root = studio, checked_root(studio, root)
        self.addresses = addresses if addresses is not None else ServerAddresses(url, None, ())
        self.preview_capability = preview_capability
        self.started_at = timestamp()
        self.library = ArtworkLibrary(studio, self.root, repo)
        self.lock = threading.RLock()
        self.history = []
        self.last_revision = None

    @property
    def url(self):
        return self.addresses.url

    def server_details(self):
        addresses = self.addresses
        return {"url": addresses.url, "localUrl": addresses.local_url, "lanUrls": list(addresses.lan_urls),
                "startedAt": self.started_at}

    def snapshot(self):
        with self.lock, records_lock(self.studio, self.root):
            try:
                return self._snapshot()
            except (self.studio.StudioError, OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError) as exc:
                observed = timestamp()
                message = "Cannot validate current run records: " + str(exc)
                revision = digest(message.encode())
                if revision != self.last_revision:
                    self.history.append({"at": observed, "verified": 0, "required": 0, "passedGates": 0})
                    self.last_revision = revision
                return {"schemaVersion": "1.0", "revision": revision, "observedAt": observed,
                        "run": {"id": self.root.name, "themeId": "", "mode": "", "phase": "", "status": "unverified"},
                        "server": self.server_details(),
                        "gates": [{"id": stage, "label": stage.title(), "status": "failed", "detail": message}
                                  for stage in ("assessment", "plan", "design", "produce", "finalize")],
                        "coverage": {"required": 0, "mockups": 0, "verified": 0, "inventoryComplete": False},
                        "nextAction": "Repair the run records before continuing.", "blockers": [message], "warnings": [message],
                        "workers": [], "tasks": [], "statistics": {"artworks": 0, "workers": 0, "tasks": 0, "evidence": 0, "passedEvidence": 0, "elapsedSeconds": 0},
                        "history": list(self.history), "artworks": [], "approvals": [], "decisions": []}

    def _snapshot(self):
        studio, root = self.studio, self.root
        warnings = ["Worker statuses are reported records, not proof of process liveness."]
        run = studio.read_json(studio.safe_path(root, "run.json"))
        coverage = studio.read_json(studio.safe_path(root, "coverage.json"))
        decisions, latest = latest_decisions(studio, root)
        evidence = run.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = []
            warnings.append("run.evidence is not a list")
        counts, inventory_valid = coverage_counts(studio, root, coverage, evidence)
        artworks, art_warnings = self.library.discover()
        warnings.extend(art_warnings)
        published_art = []
        for art in artworks:
            item = {key: art[key] for key in ("id", "path", "title", "context", "kind", "createdAt", "version")}
            item["url"] = f"preview/{self.preview_capability}/{art['version']}/" + quote(art["path"], safe="/") if self.preview_capability else ""
            published_art.append(item)
        progress = read_record(studio, root, "progress.json", {})
        need(studio, isinstance(progress, dict), "progress.json must be an object")
        workers = []
        directory = studio.safe_path(root, "workers", must_exist=False, allow_dir=True)
        if directory.exists():
            for path in sorted(directory.glob("*.json")):
                try:
                    record = studio.read_json(studio.safe_path(directory, path.name))
                    if isinstance(record, dict) and record.get("id") == path.stem and record.get("status") in STATUSES and all(isinstance(record.get(key), str) for key in ("task", "message", "updatedAt")):
                        workers.append({key: record[key] for key in ("id", "task", "status", "message", "updatedAt", "model") if key in record})
                except (studio.StudioError, OSError, ValueError, TypeError) as exc:
                    warnings.append(f"Worker {path.stem}: {exc}")
        tasks = task_records(progress)
        director = read_record(studio, root, "progress-pi-tasks-director.json", {})
        known = {item["id"] for item in tasks}
        if director:
            session_id = director.get("sessionId") if isinstance(director, dict) else None
            if not isinstance(session_id, str) or not session_id.strip() or director.get("schemaVersion") != "1.0" or director.get("runId") != run.get("id"):
                warnings.append("Native task director pointer does not match this run.")
            else:
                pi_tasks = read_record(studio, root, f"progress-pi-tasks/{digest(session_id.encode('utf-8'))}.json", {})
                if not isinstance(pi_tasks, dict) or pi_tasks.get("version") != 1 or pi_tasks.get("runId") != run.get("id") or pi_tasks.get("sessionId") != session_id:
                    warnings.append("Native task snapshot does not match the selected director session.")
                else:
                    native = pi_tasks.get("state", {})
                    native_tasks = native.get("tasks", {}) if isinstance(native, dict) else {}
                    if isinstance(native_tasks, dict):
                        native_tasks = [dict(item, id=key) for key, item in native_tasks.items() if isinstance(key, str) and isinstance(item, dict)]
                    tasks.extend(item for item in task_records({"tasks": native_tasks}) if item["id"] not in known)
        gates = []
        def gate(key, label, condition, detail, failed=False):
            gates.append({"id": key, "label": label, "status": "passed" if condition else "failed" if failed else "pending", "detail": detail})
        context_pending = []
        assessment_error = ""
        try:
            studio.check_project_context(root, run, context_pending)
            studio.check_model_routing(root, run, context_pending)
        except (studio.StudioError, OSError, ValueError, TypeError, KeyError) as exc:
            assessment_error = str(exc)
        assessed = not context_pending and not assessment_error and counts["inventoryComplete"] and inventory_valid
        gate("assessment", "Assessment", assessed, assessment_error or "; ".join(context_pending) or "Resolved current context/routing and complete valid inventory required.", bool(assessment_error) or (bool(coverage.get("surfaces")) and not inventory_valid))
        approval_current = {}
        approval_errors = {}
        for stage in ("plan", "design"):
            try:
                approval_current[stage] = current_decision(studio, root, run, latest.get(stage))
                if latest.get(stage, {}).get("outcome") == "approved" and not approval_current[stage]:
                    approval_errors[stage] = "Approval is stale or lacks valid actor/rationale."
            except (studio.StudioError, OSError, ValueError, TypeError) as exc:
                approval_current[stage] = False
                approval_errors[stage] = str(exc)
        plan_ok = assessed and approval_current["plan"]
        gate("plan", "Plan", plan_ok, approval_errors.get("plan", "Current digest-bound Plan approval and Assessment required."), "plan" in approval_errors or latest.get("plan", {}).get("outcome") == "rejected")
        design_upstream = set(latest.get("plan", {}).get("inputs", [])).issubset(set(latest.get("design", {}).get("inputs", [])))
        design_ok = plan_ok and approval_current["design"] and design_upstream and counts["required"] > 0 and counts["mockups"] == counts["required"]
        gate("design", "Design", design_ok, approval_errors.get("design", "Current upstream-bound Design approval and all mockups required."), "design" in approval_errors or latest.get("design", {}).get("outcome") == "rejected" or (approval_current["design"] and not design_upstream))
        fresh = [entry for entry in evidence if fresh_evidence(studio, root, entry)]
        kinds = {entry.get("kind") for entry in fresh}
        try:
            offline_required, unused = studio.check_project_context(root, run, [])
        except (studio.StudioError, OSError, ValueError, TypeError, KeyError):
            offline_required = True
        if not offline_required and any(isinstance(entry, dict) and entry.get("kind") == "offline" and entry.get("status") == "not-applicable" and all(isinstance(entry.get(key), str) and entry[key].strip() for key in ("reason", "reviewer", "recordedAt")) for entry in evidence):
            kinds.add("offline")
        reviewers = {entry.get("reviewer") for entry in fresh if entry.get("kind") == "review"}
        implementer = run.get("implementer")
        produced = (design_ok and counts["verified"] == counts["required"] and studio.REQUIRED_EVIDENCE.issubset(kinds)
                    and isinstance(implementer, str) and bool(implementer.strip()) and bool(reviewers) and implementer not in reviewers
                    and isinstance(run.get("themeDigest"), str) and HASH.fullmatch(run["themeDigest"]) is not None)
        evidence_failed = any(isinstance(entry, dict) and entry.get("status") == "failed" for entry in evidence)
        evidence_stale = any(isinstance(entry, dict) and entry.get("status") == "passed" and not fresh_evidence(studio, root, entry) for entry in evidence)
        gate("produce", "Produce", produced, "All implementations, fresh passed QA, required evidence, theme digest and independent review required.", evidence_failed or evidence_stale)
        check_error = ""
        try:
            checked = studio.check_run(root)
        except (studio.StudioError, OSError, ValueError, TypeError, KeyError) as exc:
            check_error = str(exc)
            checked = {"status": "FAIL", "pending": [], "errors": [check_error]}
        final_detail = check_error or "; ".join(checked.get("errors", []) + checked.get("pending", []))
        if checked["status"] == "PASS" and not produced:
            final_detail = "Snapshot prerequisites remain unverified despite check_run PASS."
        gate("finalize", "Finalize", checked["status"] == "PASS" and bool(produced), final_detail or "Current check_run PASS and all prior gates passed.", checked["status"] == "FAIL")
        approvals = []
        requests = studio.safe_path(root, "approval-requests", must_exist=False, allow_dir=True)
        if requests.exists():
            for path in sorted(requests.glob("*.json")):
                try:
                    request = studio.read_json(studio.safe_path(requests, path.name))
                    status = "pending"
                    decision = latest.get(request["stage"], {})
                    try:
                        inputs = expanded_inputs(studio, root, request["inputs"])
                        changed = inputs != request["inputs"] or studio.file_digest(root, inputs) != request["inputsDigest"] or digest(canonical(run)) != request["runDigest"]
                    except (studio.StudioError, OSError, UnicodeError, ValueError, TypeError):
                        changed = True
                    if changed:
                        status = "stale"
                    elif decision.get("requestId") == request["id"] and decision.get("inputsDigest") == request["inputsDigest"]:
                        status = decision["outcome"]
                    elif digest(canonical(decisions)) != request["decisionsDigest"]:
                        status = "stale"
                    item = {key: request[key] for key in ("id", "stage", "title", "context", "inputs", "inputsDigest", "options")}
                    item["status"] = status
                    approvals.append(item)
                except (studio.StudioError, OSError, ValueError, TypeError, KeyError) as exc:
                    warnings.append(f"Approval {path.stem}: {exc}")
        blockers = [text for text in progress.get("blockers", []) if isinstance(text, str) and text.strip()] if isinstance(progress.get("blockers", []), list) else []
        blockers += [gate["label"] + ": " + gate["detail"] for gate in gates if gate["status"] == "failed"]
        next_action = progress.get("nextAction", "")
        if not isinstance(next_action, str) or not next_action.strip():
            pending = next((gate for gate in gates if gate["status"] != "passed"), None)
            next_action = pending["detail"] if pending else "All recorded acceptance gates passed."
        elapsed = 0
        try:
            created = dt.datetime.fromisoformat(run.get("createdAt", self.started_at))
            if created.tzinfo:
                elapsed = max(0, int((dt.datetime.now(dt.timezone.utc) - created).total_seconds()))
        except (ValueError, TypeError):
            pass
        snap = {"schemaVersion": "1.0", "run": {key: run.get(key, "") for key in ("id", "themeId", "mode", "phase", "status")},
                "server": self.server_details(), "gates": gates, "coverage": counts,
                "nextAction": next_action, "blockers": blockers, "warnings": warnings, "workers": workers, "tasks": tasks,
                "statistics": {"artworks": len(published_art), "workers": len(workers), "tasks": len(tasks), "evidence": len(evidence), "passedEvidence": len(fresh), "elapsedSeconds": elapsed},
                "artworks": published_art, "approvals": approvals,
                "decisions": [{key: decision[key] for key in ("stage", "actor", "outcome", "rationale", "recordedAt", "optionId", "inputsDigest") if key in decision}
                              for decision in decisions["decisions"]]}
        stable = {key: value for key, value in snap.items() if key != "statistics"}
        stable["statistics"] = {key: value for key, value in snap["statistics"].items() if key != "elapsedSeconds"}
        revision = digest(canonical(stable))
        if revision != self.last_revision:
            self.history.append({"at": timestamp(), "verified": counts["verified"], "required": counts["required"], "passedGates": sum(g["status"] == "passed" for g in gates)})
            self.last_revision = revision
        snap.update(revision=revision, observedAt=timestamp(), history=list(self.history))
        return snap


def status_lines(snapshot):
    counts = snapshot["coverage"]
    gates = snapshot["gates"]
    width = 12
    done = width * counts["verified"] // counts["required"] if counts["required"] else 0
    coverage_percent = f"{100 * counts['verified'] // counts['required']}%" if counts["required"] and counts["inventoryComplete"] else "unknown"
    passed_gates = sum(gate["status"] == "passed" for gate in gates)
    gate_percent = f"{100 * passed_gates // len(gates)}%" if gates else "unknown"
    lines = [f"UI Design | {snapshot['run']['id']} | {snapshot['run']['mode']} | {snapshot['run']['phase']}",
             f"Coverage [{'#' * done}{'.' * (width - done)}] {counts['verified']}/{counts['required']} verified ({coverage_percent}) | {counts['mockups']} mockups | {passed_gates}/{len(gates)} gates ({gate_percent})",
             f"Workers {len(snapshot['workers'])} | Tasks {len(snapshot['tasks'])} | Artwork versions {snapshot['statistics']['artworks']}"]
    lines.extend(f"{worker['id']} [{worker['status']}] {worker['task']}" for worker in snapshot["workers"])
    lines.extend(f"Task [{task['status']}] {task['title']}" for task in snapshot["tasks"])
    lines.append("Next: " + snapshot["nextAction"])
    lines.extend("Blocked: " + blocker for blocker in snapshot["blockers"])
    if not snapshot["blockers"]:
        lines.append("Blocked: none")
    if snapshot["server"]["url"]:
        lines.append(snapshot["server"]["url"])
    else:
        lines.append("Design server is not running. Start design-serve for the browser dashboard.")
    return [re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", line) for line in lines]


def yolo_ready(studio, root):
    try:
        with records_lock(studio, root):
            run = studio.read_json(studio.safe_path(root, "run.json"))
            if run.get("mode") != "yolo" or run.get("status") != "passed" or run.get("phase") != "finalize":
                return False
            import_theme_art(studio, root)
            unused, latest = latest_decisions(studio, root)
            if latest.get("finalize", {}).get("outcome") != "approved":
                return False
            evidence = run.get("evidence", [])
            if any(entry.get("status") == "passed" and not fresh_evidence(studio, root, entry) for entry in evidence):
                return False
            return studio.check_run(root)["status"] == "PASS"
    except (studio.StudioError, OSError, ValueError, TypeError, KeyError, AttributeError):
        return False


def public_base(host, port, supplied):
    if supplied:
        if re.search(r"[\x00-\x20\x7f-\x9f]", supplied):
            raise ValueError("--public-url must not contain whitespace or terminal controls")
        parsed = urlsplit(supplied)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("--public-url must be an http(s) origin or reverse-proxy base path without credentials, query or fragment")
        if parsed.port in (None, 0) and parsed.scheme == "http":
            hostname = "[" + parsed.hostname + "]" if ":" in parsed.hostname else parsed.hostname
            parsed = parsed._replace(netloc=f"{hostname}:{port}")
        return urlunsplit(parsed).rstrip("/") + "/"
    hostname = "::1" if host == "::" else "127.0.0.1" if host == "0.0.0.0" else host
    if ":" in hostname:
        hostname = "[" + hostname + "]"
    return f"http://{hostname}:{port}/"


def http_origin(value, *, allow_path=False):
    if not isinstance(value, str) or re.search(r"[\x00-\x20\x7f-\x9f\\?#]", value):
        raise ValueError("Invalid HTTP origin")
    parsed = urlsplit(value)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or (parsed.path and not allow_path) or parsed.netloc.endswith(":")):
        raise ValueError("Invalid HTTP origin")
    port = parsed.port
    if port == 0:
        raise ValueError("Invalid HTTP origin")
    hostname = "[" + parsed.hostname + "]" if ":" in parsed.hostname else parsed.hostname
    if port is not None and port != {"http": 80, "https": 443}[parsed.scheme]:
        hostname += ":" + str(port)
    return f"{parsed.scheme}://{hostname}"


def validated_lan_addresses(studio, addresses):
    need(studio, isinstance(addresses, (tuple, list)), "LAN addresses must be IPv4 addresses")
    result = []
    for value in addresses:
        try:
            address = ipaddress.IPv4Address(value) if isinstance(value, str) else None
        except ipaddress.AddressValueError:
            address = None
        need(studio, address is not None and str(address) == value
             and not (address.is_loopback or address.is_unspecified or address.is_multicast or address.is_link_local),
             "LAN addresses must be non-loopback, non-link-local unicast IPv4 addresses")
        if value not in result:
            result.append(value)
    return tuple(result)


class DesignHTTPServer(ThreadingHTTPServer):
    daemon_threads = False
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        self.connections = set()
        self.connections_lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        with self.connections_lock:
            self.connections.add(request)
        try:
            super().process_request(request, client_address)
        except BaseException:
            with self.connections_lock:
                self.connections.discard(request)
            raise

    def shutdown_request(self, request):
        try:
            super().shutdown_request(request)
        finally:
            with self.connections_lock:
                self.connections.discard(request)

    def cancel_pending_reads(self):
        with self.connections_lock:
            connections = tuple(self.connections)
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RD)
            except OSError:
                pass


class Handler(BaseHTTPRequestHandler):
    server_version = "UIDesign/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *unused):
        pass

    @property
    def owner(self):
        return self.server.design_owner

    def respond(self, status, content, content_type="application/json; charset=utf-8", csp=None, extra=None):
        if not isinstance(content, bytes):
            content = canonical(content)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", csp or "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if extra:
            for key, value in extra.items():
                self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)

    def authorized(self, token):
        supplied = self.headers.get("Authorization", "")
        return secrets.compare_digest(supplied, "Bearer " + token)

    def request_host_allowed(self):
        values = self.headers.get_all("Host", [])
        if len(values) != 1 or re.search(r"[\x00-\x20\x7f-\x9f]", values[0]):
            return False
        host = values[0]
        if self.server.shutdown_only:
            self.request_base = f"http://127.0.0.1:{self.owner.local.server_port}/"
            return host.lower() == urlsplit(self.request_base).netloc
        with self.owner.state.lock:
            self.addresses = self.owner.state.addresses
        try:
            candidates = [base for base in self.addresses.bases
                          if http_origin(base, allow_path=True) == http_origin(f"{urlsplit(base).scheme}://{host}")]
        except ValueError:
            return False
        if not candidates:
            return False
        path = unquote(urlsplit(self.path).path)
        matching = [base for base in candidates if path.startswith(unquote(urlsplit(base).path))]
        self.request_base = max(matching, key=lambda base: len(unquote(urlsplit(base).path))) if matching else candidates[0]
        return True

    def mutation_origin_allowed(self):
        origin = self.headers.get("Origin")
        fetch_site = self.headers.get("Sec-Fetch-Site")
        if fetch_site in ("cross-site", "same-site"):
            return False
        if origin is None:
            return True
        if len(self.headers.get_all("Origin", [])) != 1:
            return False
        try:
            return http_origin(origin) in self.addresses.origins
        except ValueError:
            return False

    def request_path(self):
        parsed = urlsplit(self.path)
        if parsed.query or parsed.fragment or parsed.scheme or parsed.netloc:
            raise ValueError("Queries and absolute request targets are not accepted")
        value = unquote(parsed.path)
        prefix = unquote(urlsplit(self.request_base).path).rstrip("/")
        if prefix and value.startswith(prefix + "/"):
            value = value[len(prefix):]
        if "\\" in value or any(piece in (".", "..") for piece in value.split("/")) or any(ord(c) < 32 for c in value):
            raise ValueError("Unsafe URL path")
        return value

    def do_GET(self):
        owner = self.owner
        try:
            if not self.request_host_allowed():
                self.respond(403, {"error": "Unadvertised request Host"})
                return
            path = self.request_path()
            if path == "/api/identity":
                if not self.authorized(owner.token):
                    self.respond(401, {"error": "Bearer authentication required"})
                    return
                self.respond(200, {"instanceId": owner.instance_id, "run": str(owner.root)})
                return
            if self.server.shutdown_only:
                self.respond(404, {"error": "Not found"})
                return
            if path == "/api/snapshot":
                if not self.authorized(owner.token):
                    self.respond(401, {"error": "Bearer authentication required"})
                    return
                self.respond(200, owner.state.snapshot())
                return
            if path.startswith("/preview/"):
                self.preview(path)
                return
            assets = {"/": ("index.html", "text/html; charset=utf-8"), "/index.html": ("index.html", "text/html; charset=utf-8"),
                      "/dashboard.css": ("dashboard.css", "text/css; charset=utf-8"), "/dashboard.js": ("dashboard.js", "text/javascript; charset=utf-8")}
            if path not in assets:
                self.respond(404, {"error": "Not found"})
                return
            name, content_type = assets[path]
            content = owner.studio.safe_path(Path(__file__).resolve().parent.parent / "dashboard", name).read_bytes()
            self.respond(200, content, content_type,
                         "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; frame-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        except (owner.studio.StudioError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            self.respond(400, {"error": str(exc)})

    def preview(self, path):
        owner = self.owner
        parts = path.split("/", 4)
        if len(parts) != 5 or not secrets.compare_digest(parts[2], owner.preview_capability):
            self.respond(404, {"error": "Not found"})
            return
        version, relative = parts[3], parts[4]
        record, content = owner.state.library.file(version, relative)
        directory = owner.state.library.directory / version / "files"
        prefix = urlsplit(self.request_base).path + f"preview/{owner.preview_capability}/{version}/"
        suffix = Path(relative).suffix.lower()
        if suffix in (".html", ".htm"):
            parser = SafeHTML(owner.studio, directory, relative, record["files"], prefix)
            parser.feed(content.decode("utf-8"))
            parser.close()
            content = "".join(parser.output).encode("utf-8")
        elif suffix == ".css":
            content = safe_css(owner.studio, directory, relative, content.decode("utf-8"), record["files"], prefix).encode("utf-8")
        elif suffix == ".svg":
            content = safe_svg(owner.studio, directory, relative, content, record["files"], prefix)
        content_type = mimetypes.guess_type(relative)[0] or "application/octet-stream"
        parsed = urlsplit(self.request_base)
        source = f"{parsed.scheme}://{parsed.netloc}{prefix}"
        csp = f"sandbox; default-src 'none'; script-src 'none'; style-src 'unsafe-inline' {source}; img-src {source} data:; font-src {source} data:; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
        self.respond(200, content, content_type, csp, {"Access-Control-Allow-Origin": "*", "Cross-Origin-Resource-Policy": "cross-origin"})

    def do_POST(self):
        owner = self.owner
        try:
            if not self.request_host_allowed():
                self.respond(403, {"error": "Unadvertised request Host"})
                return
            path = self.request_path()
            shutdown = self.server.shutdown_only
            if (shutdown and path != "/api/shutdown") or (not shutdown and path != "/api/approval"):
                self.respond(404, {"error": "Not found"})
                return
            if not self.authorized(owner.shutdown_token if shutdown else owner.token):
                self.respond(401, {"error": "Bearer authentication required"})
                return
            if (shutdown and (not ipaddress.ip_address(self.client_address[0]).is_loopback or self.headers.get("Origin") is not None)) or (not shutdown and not self.mutation_origin_allowed()):
                self.respond(403, {"error": "Cross-origin mutation forbidden"})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self.respond(415, {"error": "Content-Type application/json required"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY or self.headers.get("Transfer-Encoding"):
                self.respond(413, {"error": "Invalid JSON body length"})
                return
            payload = json.loads(self.rfile.read(length))
            if shutdown:
                if not isinstance(payload, dict) or payload.get("instanceId") != owner.instance_id:
                    self.respond(409, {"error": "Server owner changed"})
                    return
                self.respond(200, {"status": "PASS", "instanceId": owner.instance_id})
                owner.stop.set()
            else:
                self.respond(200, approve(owner.studio, owner.root, payload))
        except ApprovalConflict as exc:
            self.respond(409, {"error": str(exc)})
        except (owner.studio.StudioError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
            self.respond(400, {"error": str(exc)})

    def do_OPTIONS(self):
        self.respond(403, {"error": "Cross-origin access is not enabled"})


class DesignServer:
    def __init__(self, studio, root, host="127.0.0.1", port=0, public_url=None, interval=1.0, repo=None, *, lan_addresses=()):
        self.studio, self.root = studio, checked_root(studio, root)
        need(studio, isinstance(port, int) and 0 <= port <= 65535 and interval > 0, "Port/refresh interval is invalid")
        self.host, self.port, self.public_url, self.interval = host, port, public_url, interval
        self.repo = repo
        self._lan_addresses = validated_lan_addresses(studio, lan_addresses)
        self.lock_contended = False
        self.token, self.preview_capability, self.shutdown_token = (secrets.token_urlsafe(32) for unused in range(3))
        self.instance_id = secrets.token_hex(24)
        self.stop = threading.Event()
        self.closed = threading.Event()
        self.close_lock = threading.RLock()
        self.http = self.local = self.run_lock = self.temporary = self.state = None
        self.threads = []

    @property
    def addresses(self):
        if self.state is None:
            return None
        with self.state.lock:
            return self.state.addresses

    @property
    def base_url(self):
        addresses = self.addresses
        return addresses.bases[0] if addresses else ""

    @property
    def url(self):
        addresses = self.addresses
        return addresses.url if addresses else ""

    @property
    def local_url(self):
        addresses = self.addresses
        return addresses.local_url if addresses else None

    @property
    def lan_urls(self):
        addresses = self.addresses
        return list(addresses.lan_urls) if addresses else []

    def address_snapshot(self, addresses):
        bound = ipaddress.ip_address(self.http.server_address[0])
        port = self.http.server_port
        local_base = None
        if bound.is_loopback or bound.is_unspecified:
            local_host = ("127.0.0.1" if bound.version == 4 else "::1") if bound.is_unspecified else str(bound)
            local_base = public_base(local_host, port, None)
        supported = addresses if str(bound) == "0.0.0.0" else tuple(value for value in addresses if value == str(bound))
        lan_bases = tuple(public_base(value, port, None) for value in supported)
        base = public_base(self.host, port, self.public_url)
        if not self.public_url and lan_bases:
            base = lan_bases[0]
        bases = tuple(dict.fromkeys(value for value in (base, local_base, *lan_bases) if value))
        origins = frozenset(http_origin(base, allow_path=True) for base in bases)
        fragment = "#token=" + self.token
        return ServerAddresses(base + fragment, local_base + fragment if local_base else None,
                               tuple(value + fragment for value in lan_bases), bases, origins)

    def set_lan_addresses(self, addresses: tuple[str, ...]):
        addresses = validated_lan_addresses(self.studio, addresses)
        need(self.studio, self.state is not None, "A design server must start before updating LAN addresses")
        with self.state.lock:
            if self.stop.is_set() or self.closed.is_set():
                return
            updated = self.address_snapshot(addresses)
            if updated == self.state.addresses:
                return
            locator = read_record(self.studio, self.root, ".design-server.json")
            need(self.studio, isinstance(locator, dict) and locator.get("instanceId") == self.instance_id
                 and locator.get("run") == str(self.root), "Server owner changed before updating LAN addresses")
            previous = self.state.addresses
            self.state.addresses = updated
            try:
                private_json(self.studio, self.studio.safe_path(self.root, ".design-server.json"),
                             {**locator, "url": updated.url, "localUrl": updated.local_url, "lanUrls": list(updated.lan_urls)})
                self.publish_status()
            except BaseException:
                self.state.addresses = previous
                private_json(self.studio, self.studio.safe_path(self.root, ".design-server.json"), locator)
                self.publish_status()
                raise

    def start(self):
        need(self.studio, self.run_lock is None and not self.closed.is_set(), "A design server instance can only start once")
        try:
            self.run_lock = FileLock(self.root / ".design-server.lock", self.studio)
            self.run_lock.__enter__()
            previous = read_record(self.studio, self.root, ".design-server.json")
            if previous is not None:
                reap_stale_owner(self.studio, self.root, previous)
            self.temporary = Path(tempfile.mkdtemp(prefix="ui-design-server-"))
            os.chmod(self.temporary, 0o700)
            private_json(self.studio, self.temporary / ".design-owner.json",
                         {"instanceId": self.instance_id, "run": str(self.root), "shutdownTokenDigest": digest(self.shutdown_token.encode())})
            server_type = DesignHTTPServer
            if ":" in self.host:
                class IPv6Server(DesignHTTPServer):
                    address_family = socket.AF_INET6
                server_type = IPv6Server
            self.http = server_type((self.host, self.port), Handler)
            self.local = DesignHTTPServer(("127.0.0.1", 0), Handler)
            self.state = DesignState(self.studio, self.root, preview_capability=self.preview_capability, repo=self.repo,
                                     addresses=self.address_snapshot(self._lan_addresses))
            addresses = self.state.addresses
            locator = {"schemaVersion": "1.0", "instanceId": self.instance_id, "url": addresses.url,
                       "localUrl": addresses.local_url, "lanUrls": list(addresses.lan_urls), "startedAt": self.state.started_at,
                       "pid": os.getpid(), "run": str(self.root), "tempDirectory": str(self.temporary), "previewCapability": self.preview_capability,
                       "probeUrl": f"http://127.0.0.1:{self.local.server_port}/api/identity",
                       "localShutdown": {"url": f"http://127.0.0.1:{self.local.server_port}/api/shutdown", "token": self.shutdown_token}}
            private_json(self.studio, self.studio.safe_path(self.root, ".design-server.json", must_exist=False), locator)
            self.publish_status()
            for server, shutdown_only in ((self.http, False), (self.local, True)):
                server.design_owner, server.shutdown_only = self, shutdown_only
                thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
                thread.start()
                self.threads.append(thread)
            watcher = threading.Thread(target=self.watch, daemon=True)
            watcher.start()
            self.threads.append(watcher)
            return self
        except BaseException:
            self.lock_contended = bool(self.run_lock and self.run_lock.contended)
            self.close()
            raise

    def publish_status(self):
        with self.state.lock:
            if self.stop.is_set() or self.closed.is_set():
                return None
            snapshot = self.state.snapshot()
            if self.stop.is_set() or self.closed.is_set():
                return None
            private_json(self.studio, self.studio.safe_path(self.root, ".design-status.json", must_exist=False),
                         {**snapshot, "lines": status_lines(snapshot), "instanceId": self.instance_id})
            return snapshot

    def watch(self):
        while not self.stop.wait(self.interval):
            try:
                if self.publish_status() is None:
                    break
                if yolo_ready(self.studio, self.root):
                    self.stop.set()
            except (self.studio.StudioError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
                with self.state.lock:
                    if self.stop.is_set() or self.closed.is_set():
                        break
                    try:
                        private_json(self.studio, self.studio.safe_path(self.root, ".design-status.json", must_exist=False),
                                     {"schemaVersion": "1.0", "instanceId": self.instance_id, "observedAt": timestamp(),
                                      "lines": [re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", "UI Design status unavailable: " + str(exc)), self.url], "error": str(exc)})
                    except OSError:
                        pass
        self.close()

    def serve(self):
        self.start()
        print(json.dumps({"status": "PASS", "url": self.url, "run": str(self.root), "instanceId": self.instance_id}), flush=True)
        previous = {}
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM):
                previous[sig] = signal.signal(sig, lambda signum, frame: self.stop.set())
        try:
            self.stop.wait()
        finally:
            self.close()
            for sig, handler in previous.items():
                signal.signal(sig, handler)
        return {"status": "PASS", "stopped": True}

    def close(self):
        with self.close_lock:
            if self.closed.is_set():
                return
            self.stop.set()
            try:
                for index, server in enumerate((self.http, self.local)):
                    if server:
                        if len(self.threads) > index:
                            server.shutdown()
                        server.cancel_pending_reads()
                        server.server_close()
                for thread in self.threads[:2]:
                    if thread is not threading.current_thread():
                        thread.join(timeout=3)
                if self.temporary and self.temporary.exists():
                    shutil.rmtree(self.temporary)
                lock = self.state.lock if self.state else self.close_lock
                with lock:
                    for relative in (".design-status.json", ".design-server.json"):
                        path = self.studio.safe_path(self.root, relative, must_exist=False)
                        record = read_record(self.studio, self.root, relative)
                        if record is not None:
                            need(self.studio, isinstance(record, dict), "Invalid runtime record during owned cleanup")
                            if record.get("instanceId") == self.instance_id:
                                path.unlink()
            finally:
                if self.run_lock:
                    self.run_lock.__exit__()
                    self.run_lock = None
            self.closed.set()


def remove_stale_temporary(studio, root, locator):
    raw = locator.get("tempDirectory")
    if not raw:
        return False
    path = Path(raw)
    if not path.exists():
        return False
    need(studio, path.is_absolute() and not path.is_symlink() and path.parent.resolve() == Path(tempfile.gettempdir()).resolve()
         and re.fullmatch(r"ui-design-server-[a-zA-Z0-9_-]+", path.name), "Refusing an unowned stale temporary directory")
    if hasattr(os, "getuid"):
        need(studio, path.stat().st_uid == os.getuid(), "Stale temporary directory belongs to another user")
    marker = studio.read_json(studio.safe_path(path, ".design-owner.json"))
    expected = {"instanceId": locator["instanceId"], "run": str(root),
                "shutdownTokenDigest": digest(locator["localShutdown"]["token"].encode())}
    need(studio, marker == expected, "Stale temporary ownership marker does not match this run")
    shutil.rmtree(path)
    return True


def validate_locator(studio, root, locator):
    need(studio, isinstance(locator, dict) and locator.get("run") == str(root) and isinstance(locator.get("instanceId"), str), "Invalid server locator")
    connection = locator.get("localShutdown", {})
    need(studio, isinstance(connection, dict) and isinstance(connection.get("token"), str), "Invalid local shutdown credentials")
    parsed = urlsplit(connection.get("url", ""))
    need(studio, parsed.scheme == "http" and parsed.hostname == "127.0.0.1" and parsed.port is not None and parsed.path == "/api/shutdown" and not parsed.query and not parsed.fragment and not parsed.username and not parsed.password, "Shutdown locator must identify the owned loopback endpoint")
    return parsed.port


def reap_stale_owner(studio, root, locator):
    validate_locator(studio, root, locator)
    path = studio.safe_path(root, ".design-server.json", must_exist=False)
    current = read_record(studio, root, ".design-server.json")
    if current is None:
        return {"status": "PASS", "stopped": False, "alreadyStopped": True, "temporaryRemoved": False}
    need(studio, isinstance(current, dict) and current.get("instanceId") == locator["instanceId"], "Server owner changed before stale cleanup")
    removed = remove_stale_temporary(studio, root, locator)
    status = studio.safe_path(root, ".design-status.json", must_exist=False)
    if status.exists() and studio.read_json(status).get("instanceId") == locator["instanceId"]:
        status.unlink()
    path.unlink()
    return {"status": "PASS", "stopped": False, "alreadyStopped": True, "temporaryRemoved": removed,
            "warning": "Removed an unlocked stale owner; no process was killed."}


def cleanup(studio, root):
    root = checked_root(studio, root)
    path = studio.safe_path(root, ".design-server.json", must_exist=False)
    locator = read_record(studio, root, ".design-server.json")
    if locator is None:
        return {"status": "PASS", "stopped": False, "alreadyStopped": True}
    port = validate_locator(studio, root, locator)
    owner_lock = FileLock(root / ".design-server.lock", studio)
    try:
        owner_lock.__enter__()
    except studio.StudioError:
        if not owner_lock.contended:
            raise
    else:
        try:
            return reap_stale_owner(studio, root, locator)
        finally:
            owner_lock.__exit__()
    client = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    failure = None
    try:
        client.request("POST", "/api/shutdown", canonical({"instanceId": locator["instanceId"]}),
                       {"Authorization": "Bearer " + locator["localShutdown"]["token"], "Content-Type": "application/json"})
        response = client.getresponse()
        body = response.read()
        need(studio, response.status == 200 and json.loads(body).get("instanceId") == locator["instanceId"], "Owning server rejected cleanup; no process was killed")
    except (studio.StudioError, OSError, ValueError, http.client.HTTPException) as exc:
        failure = exc
    finally:
        client.close()
    if failure is not None:
        owner_lock = FileLock(root / ".design-server.lock", studio)
        try:
            owner_lock.__enter__()
        except studio.StudioError:
            if not owner_lock.contended:
                raise
            raise studio.StudioError("Owning server is unreachable or rejected cleanup but retains its lock; no process was killed") from failure
        try:
            return reap_stale_owner(studio, root, locator)
        finally:
            owner_lock.__exit__()
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        current = read_record(studio, root, ".design-server.json", {})
        need(studio, isinstance(current, dict), "Invalid runtime locator during shutdown")
        if current.get("instanceId") not in (None, locator["instanceId"]):
            break
        if not path.exists():
            try:
                with FileLock(root / ".design-server.lock", studio):
                    break
            except studio.StudioError:
                pass
        time.sleep(0.05)
    else:
        raise studio.StudioError("Shutdown was accepted but owner cleanup has not completed")
    return {"status": "PASS", "stopped": True, "alreadyStopped": False}


def cleanup_all(studio, repo):
    unused, unused_themes, runs = studio.config_paths(repo)
    cleaned, errors = [], []
    if runs.exists():
        for path in sorted(runs.glob("*/.design-server.json")):
            try:
                relative = path.relative_to(runs).as_posix()
                studio.safe_path(runs, relative)
                cleaned.append({"run": str(path.parent), **cleanup(studio, path.parent)})
            except (studio.StudioError, OSError, ValueError, TypeError) as exc:
                errors.append({"run": str(path.parent), "error": str(exc)})
    return {"status": "FAIL" if errors else "PASS", "runs": cleaned, "errors": errors}


def cleanup_registered_yolo(studio, root):
    if not yolo_ready(studio, root):
        return None
    try:
        return cleanup(studio, root)
    except (studio.StudioError, OSError, ValueError, TypeError) as exc:
        return {"status": "FAIL", "error": str(exc)}


def add_parsers(subs):
    sub = subs.add_parser("design-serve", help="Serve the authenticated live design dashboard in the foreground")
    sub.add_argument("run")
    sub.add_argument("--host", default="127.0.0.1")
    sub.add_argument("--port", type=int, default=0)
    sub.add_argument("--public-url")
    sub.add_argument("--repo", help="Verify and import the active theme's project-local visual artifacts")
    sub = subs.add_parser("design-cleanup", help="Stop owned design servers without killing stored PIDs or deleting evidence")
    sub.add_argument("run", nargs="?")
    sub.add_argument("--all", action="store_true")
    sub.add_argument("--repo")
    sub = subs.add_parser("status", help="Read honest live design status; --watch is the non-OMP fallback")
    sub.add_argument("run")
    sub.add_argument("--watch", action="store_true")
    sub.add_argument("--interval", type=float, default=1.0)
    sub = subs.add_parser("progress", help="Publish the director's next action and blockers")
    sub.add_argument("run")
    sub.add_argument("--next", dest="next_action")
    sub.add_argument("--blocker", action="append")
    sub = subs.add_parser("worker", help="Publish one worker's reported task state")
    sub.add_argument("run")
    sub.add_argument("--id", required=True)
    sub.add_argument("--task", required=True)
    sub.add_argument("--status", required=True, choices=sorted(STATUSES))
    sub.add_argument("--message", required=True)
    sub.add_argument("--model")
    sub = subs.add_parser("artwork", help="Attach a truthful purpose to an automatically retained visual artifact")
    sub.add_argument("run")
    sub.add_argument("--file", required=True)
    sub.add_argument("--context", required=True)
    sub.add_argument("--title")
    sub.add_argument("--repo", help="Interpret --file inside the verified project's active theme directory")
    sub = subs.add_parser("approval-request", help="Publish a digest-bound guided Plan or Design review")
    sub.add_argument("run")
    sub.add_argument("--id", required=True)
    sub.add_argument("--stage", required=True, choices=("plan", "design"))
    sub.add_argument("--title", required=True)
    sub.add_argument("--context", required=True)
    sub.add_argument("--files", required=True, nargs="+")
    sub.add_argument("--choices", help="Run-relative JSON file containing review options")


COMMANDS = {"design-serve", "design-cleanup", "status", "progress", "worker", "artwork", "approval-request"}


def command(studio, args):
    if args.command == "design-serve":
        return DesignServer(studio, args.run, args.host, args.port, args.public_url, repo=args.repo).serve()
    if args.command == "design-cleanup":
        need(studio, (args.all and args.repo and not args.run) or (args.run and not args.all and not args.repo), "Use design-cleanup RUN or design-cleanup --all --repo PATH")
        return cleanup_all(studio, args.repo) if args.all else cleanup(studio, args.run)
    if args.command == "progress":
        need(studio, args.next_action is not None or args.blocker is not None, "Publish --next or --blocker")
        return publish_progress(studio, args.run, args.next_action, args.blocker)
    if args.command == "worker":
        return publish_worker(studio, args.run, args.id, args.task, args.status, args.message, args.model)
    if args.command == "artwork":
        return publish_artwork(studio, args.run, args.file, args.context, args.title, args.repo)
    if args.command == "approval-request":
        choices = studio.read_json(studio.safe_path(args.run, args.choices)) if args.choices else None
        return publish_request(studio, args.run, args.id, args.stage, args.title, args.context, args.files, choices)
    need(studio, args.interval > 0, "Status interval must be positive")
    root = checked_root(studio, args.run)
    locator = read_record(studio, root, ".design-server.json", {})
    state = DesignState(studio, root, preview_capability=locator.get("previewCapability", ""),
                        addresses=ServerAddresses(locator.get("url", ""), locator.get("localUrl"), tuple(locator.get("lanUrls", ()))))
    state.started_at = locator.get("startedAt", state.started_at)
    if not args.watch:
        snap = state.snapshot()
        return {"status": "PASS", **snap, "lines": status_lines(snap)}
    try:
        while True:
            locator = read_record(studio, root, ".design-server.json", {})
            state.addresses = ServerAddresses(locator.get("url", ""), locator.get("localUrl"), tuple(locator.get("lanUrls", ())))
            state.started_at = locator.get("startedAt", state.started_at)
            state.preview_capability = locator.get("previewCapability", "")
            snap = state.snapshot()
            print("\n".join(status_lines(snap)), flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return {"status": "PASS", "watchStopped": True}
