"""Connection-owned landing dashboards and verified, read-only discovery."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import datetime as dt
from functools import lru_cache
import http.client
from http.server import BaseHTTPRequestHandler
from io import StringIO
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import socket
import stat
import sys
import tempfile
import threading
import time
from typing import Any, Literal, Protocol
from urllib.parse import unquote, urlsplit

import psutil
import segno

from .runtime import PAYLOAD, backend, studio


SESSION_DIRECTORY = ".ui-design-studio/runtime/mcp"
POLL_INTERVAL = 2.0
PROBE_TIMEOUT = 2.0
CONTENTION_TIMEOUT = 3.0
MAX_IDENTITY = 16 * 1024
MAX_RECORD = 1024 * 1024
INSTANCE = re.compile(r"[0-9a-f]{48}\Z")
TOKEN = re.compile(r"token=([A-Za-z0-9_-]{16,256})\Z")
CONTROLS = re.compile(r"[\x00-\x20\x7f-\x9f]")
ASSETS = {
    "/": ("landing.html", "text/html; charset=utf-8"),
    "/landing.html": ("landing.html", "text/html; charset=utf-8"),
    "/landing.js": ("landing.js", "text/javascript; charset=utf-8"),
    "/dashboard.css": ("dashboard.css", "text/css; charset=utf-8"),
}
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


class DashboardUnavailable(ValueError):
    def __init__(self):
        super().__init__("Dashboard is not running.")


class AmbiguousSessions(ValueError):
    def __init__(self, session_ids: list[str]):
        self.session_ids = sorted(session_ids)
        super().__init__("Several dashboards are running. Select a session.")


class RunServer(Protocol):
    instance_id: str
    closed: threading.Event
    stop: threading.Event

    def close(self) -> None: ...

    def set_lan_addresses(self, addresses: tuple[str, ...]) -> None: ...


@dataclass(frozen=True)
class OwnedRun:
    server: RunServer


@dataclass(frozen=True)
class ReusedRun:
    instance_id: str
    root: Path


RunHandle = OwnedRun | ReusedRun


def _timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def _no_symlinks(path: Path) -> None:
    for component in (path, *path.parents):
        if component.is_symlink():
            raise ValueError(f"Symlink is not permitted: {component}")


def _repo(value: Path | str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("Repository must be an explicit absolute path")
    _no_symlinks(path)
    if not path.is_dir():
        raise ValueError("Repository must be an existing directory")
    if re.search(r"[\x00-\x1f\x7f-\x9f]", str(path)):
        raise ValueError("Repository must not contain terminal controls")
    return path.resolve()


def _runs_root(repo: Path) -> Path:
    engine = studio()
    engine.safe_path(repo, "ui-design-studio.json", must_exist=False)
    return engine.config_paths(repo)[2]


def _run_target(repo: Path, run: str) -> Path:
    if (not isinstance(run, str) or not run or PurePosixPath(run).as_posix() != run
            or any(piece in ("", ".", "..") for piece in run.split("/"))
            or re.search(r"[\x00-\x1f\x7f-\x9f]", run)):
        raise ValueError("Run must be a portable repository-relative path")
    engine = studio()
    root = engine.safe_path(repo, run, must_exist=False, allow_dir=True)
    runs = _runs_root(repo)
    if root == runs or not root.is_relative_to(runs):
        raise ValueError("Run must be under the configured runs directory")
    return root


def _run_path(repo: Path, run: str) -> Path:
    engine = studio()
    root = _run_target(repo, run)
    engine.safe_path(repo, run, allow_dir=True)
    if not root.is_dir():
        raise ValueError("Run must be a directory")
    record = engine.read_json(engine.safe_path(root, "run.json"))
    if not isinstance(record, dict) or not all(isinstance(record.get(key), str) for key in ("id", "phase", "status")):
        raise ValueError("Invalid design run record")
    return root


def discover_lan_addresses() -> tuple[str, ...]:
    """Return up-interface IPv4 addresses, ordered by interface then numeric IP."""
    interfaces, states = psutil.net_if_addrs(), psutil.net_if_stats()
    result = []
    for name in sorted(interfaces):
        if name not in states or not states[name].isup:
            continue
        addresses = set()
        for entry in interfaces[name]:
            if entry.family != socket.AF_INET:
                continue
            try:
                address = ipaddress.IPv4Address(entry.address)
            except (ipaddress.AddressValueError, TypeError):
                continue
            if not (address.is_loopback or address.is_unspecified or address.is_multicast or address.is_link_local):
                addresses.add(address)
        for address in sorted(addresses):
            if str(address) not in result:
                result.append(str(address))
    return tuple(result)


def _read_json(path: Path, *, private: bool = False) -> dict:
    _no_symlinks(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_RECORD:
            raise ValueError("Runtime record must be a bounded regular file")
        if private and os.name != "nt":
            if stat.S_IMODE(metadata.st_mode) & 0o077 or (hasattr(os, "getuid") and metadata.st_uid != os.getuid()):
                raise ValueError("Runtime record must be private to its owner")
        result = json.loads(handle.read(MAX_RECORD + 1))
    if not isinstance(result, dict):
        raise ValueError("Runtime record must be an object")
    return result


def _private_directory(repo: Path) -> Path:
    directory = repo
    for piece in SESSION_DIRECTORY.split("/"):
        directory = directory / piece
        _no_symlinks(directory)
        directory.mkdir(mode=0o700, exist_ok=True)
        _no_symlinks(directory)
        if not directory.is_dir():
            raise ValueError("Runtime directory must be a directory")
    os.chmod(directory, 0o700)
    return directory


def _write_record(path: Path, value: dict) -> None:
    _no_symlinks(path)
    if path.exists():
        existing = _read_json(path, private=True)
        if existing.get("instanceId") != value["instanceId"] or existing.get("repo") != value["repo"]:
            raise ValueError("Dashboard session record belongs to another owner")
    descriptor, temporary = tempfile.mkstemp(prefix=".session-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            os.chmod(temporary, 0o600)
            json.dump(value, handle, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        _no_symlinks(path)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _public_url(value: str, *, loopback: bool = False, lan: bool = False) -> tuple[Any, str]:
    if not isinstance(value, str) or len(value) > 8192 or CONTROLS.search(value) or "\\" in value:
        raise ValueError("Invalid dashboard URL")
    parsed = urlsplit(value)
    token = TOKEN.fullmatch(parsed.fragment)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or not token or not parsed.path.startswith("/")
            or not parsed.path.endswith("/") or parsed.port == 0
            or any(piece in (".", "..") for piece in unquote(parsed.path).split("/"))):
        raise ValueError("Invalid dashboard URL")
    if loopback and (parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "::1")):
        raise ValueError("Dashboard URL must identify a loopback listener")
    if lan:
        address = ipaddress.IPv4Address(parsed.hostname)
        if parsed.scheme != "http" or address.is_loopback or address.is_unspecified or address.is_link_local or address.is_multicast:
            raise ValueError("Invalid LAN dashboard URL")
    return parsed, token.group(1)


def _normalized_origin(value: str) -> str | None:
    try:
        return backend().http_origin(value)
    except ValueError:
        return None


def _probe_url(value: str) -> Any:
    if not isinstance(value, str) or CONTROLS.search(value):
        raise ValueError("Invalid identity probe URL")
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or parsed.port in (None, 0)
            or parsed.path != "/api/identity" or parsed.query or parsed.fragment
            or parsed.username is not None or parsed.password is not None
            or parsed.netloc != f"127.0.0.1:{parsed.port}"):
        raise ValueError("Identity probe must identify the exact loopback endpoint")
    return parsed


def _probe(value: str, token: str, expected: dict, *, timeout: float = PROBE_TIMEOUT) -> bool:
    parsed = _probe_url(value)
    connection = http.client.HTTPConnection("127.0.0.1", parsed.port, timeout=timeout)
    deadline = time.monotonic() + timeout
    deadline_timer = None
    try:
        connection.connect()
        transport = connection.sock

        def interrupt_read() -> None:
            try:
                transport.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        # Per-read socket timeouts do not bound trickled HTTP response headers.
        deadline_timer = threading.Timer(max(0, deadline - time.monotonic()), interrupt_read)
        deadline_timer.daemon = True
        deadline_timer.start()
        connection.request("GET", "/api/identity", headers={"Authorization": "Bearer " + token, "Connection": "close"})
        response = connection.getresponse()
        length = response.getheader("Content-Length", "")
        if (response.status != 200 or response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json"
                or not length.isdecimal() or not 0 < int(length) <= MAX_IDENTITY or response.getheader("Transfer-Encoding")):
            return False
        remaining = int(length)
        chunks = []
        while remaining:
            budget = deadline - time.monotonic()
            if budget <= 0:
                return False
            if transport is not None:
                transport.settimeout(budget)
            chunk = response.read1(remaining)
            if not chunk:
                return False
            chunks.append(chunk)
            remaining -= len(chunk)
        result = json.loads(b"".join(chunks))
        return isinstance(result, dict) and all(result.get(key) == entry for key, entry in expected.items())
    except (OSError, http.client.HTTPException, UnicodeError, ValueError):
        return False
    finally:
        if deadline_timer is not None:
            deadline_timer.cancel()
            deadline_timer.join()
        connection.close()


@lru_cache(maxsize=64)
def _formatted_text(local_url: str | None, lan_urls: tuple[str, ...], canonical_url: str) -> str:
    qr_url = lan_urls[0] if lan_urls else local_url or canonical_url
    lines = ["[ok] Dashboard live → " + (local_url or canonical_url)]
    lines.extend("[lan] " + value for value in lan_urls)
    if not lan_urls:
        lines.append("[lan] unavailable")
    output = StringIO()
    segno.make_qr(qr_url).terminal(out=output, compact=True, border=4)
    return "\n".join(lines) + "\n\n" + output.getvalue()


def _details(repo: Path, instance_id: str, run: str | None, local_url: str | None,
             lan_urls: list[str] | tuple[str, ...], canonical_url: str, *, observed_at: str | None = None) -> dict:
    if not isinstance(instance_id, str) or not INSTANCE.fullmatch(instance_id):
        raise ValueError("Invalid dashboard instance identity")
    unused, token = _public_url(canonical_url)
    local = None
    if local_url is not None:
        local, local_token = _public_url(local_url, loopback=True)
        if local_token != token:
            raise ValueError("Dashboard aliases have different capabilities")
    if not isinstance(lan_urls, (list, tuple)) or len(lan_urls) > 256:
        raise ValueError("Invalid LAN dashboard aliases")
    for value in lan_urls:
        address, alias_token = _public_url(value, lan=True)
        if alias_token != token or (local is not None and ((address.port or 80) != (local.port or 80) or address.path != local.path)):
            raise ValueError("Dashboard aliases identify different listeners")
    qr_url = lan_urls[0] if lan_urls else local_url or canonical_url
    result = {"schemaVersion": "1.0", "instanceId": instance_id, "repo": str(repo), "run": run, "state": "live",
              "observedAt": observed_at or _timestamp(), "localUrl": local_url, "lanUrls": list(lan_urls), "qrUrl": qr_url,
              "text": _formatted_text(local_url, tuple(lan_urls), canonical_url)}
    if local_url is None:
        result["url"] = canonical_url
    return result


def _run_details(repo: Path, root: Path, *, expected_instance: str | None = None, timeout: float = PROBE_TIMEOUT) -> dict:
    locator = _read_json(studio().safe_path(root, ".design-server.json"), private=True)
    instance_id = locator.get("instanceId")
    if (locator.get("schemaVersion") != "1.0" or locator.get("run") != str(root)
            or (expected_instance is not None and instance_id != expected_instance)):
        raise ValueError("Invalid design server locator identity")
    result = _details(repo, instance_id, root.relative_to(repo).as_posix(), locator.get("localUrl"), locator.get("lanUrls", []), locator.get("url"))
    unused, token = _public_url(locator.get("url"))
    if not _probe(locator.get("probeUrl"), token, {"instanceId": instance_id, "run": str(root)}, timeout=timeout):
        raise DashboardUnavailable()
    return result


def _session_details(repo: Path, path: Path) -> dict:
    record = _read_json(path, private=True)
    instance_id = record.get("instanceId")
    if (record.get("schemaVersion") != "1.0" or record.get("repo") != str(repo) or record.get("state") != "live"
            or record.get("run") is not None or path.name != str(instance_id) + ".json"):
        raise ValueError("Invalid dashboard session record")
    observed = dt.datetime.fromisoformat(record.get("observedAt", ""))
    if observed.tzinfo is None or observed > dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=5):
        raise ValueError("Invalid dashboard observation time")
    local_url = record.get("localUrl")
    parsed, token = _public_url(local_url, loopback=True)
    if parsed.hostname != "127.0.0.1" or parsed.path != "/":
        raise ValueError("Invalid connection dashboard listener")
    result = _details(repo, instance_id, None, local_url, record.get("lanUrls"), local_url, observed_at=record["observedAt"])
    if record.get("qrUrl") != result["qrUrl"]:
        raise ValueError("Invalid cached dashboard QR destination")
    identity_url = f"http://127.0.0.1:{parsed.port or 80}/api/identity"
    if not _probe(identity_url, token, {"instanceId": instance_id, "repo": str(repo)}):
        raise DashboardUnavailable()
    return result


def discover(repo: Path | str, session: str | None = None, run: str | None = None) -> dict:
    """Inspect existing listeners without creating, deleting, or starting anything."""
    repo = _repo(repo)
    if session is not None and run is not None:
        raise ValueError("Select either a run or a session")
    if run is not None:
        try:
            root = _run_target(repo, run)
            record = studio().safe_path(root, "run.json", must_exist=False)
            if not root.is_dir() or not record.is_file():
                raise DashboardUnavailable()
            root = _run_path(repo, run)
        except studio().StudioError as exc:
            raise ValueError(str(exc)) from exc
        try:
            return _run_details(repo, root)
        except (OSError, ValueError, TypeError, studio().StudioError) as exc:
            raise DashboardUnavailable() from exc
    directory = repo / SESSION_DIRECTORY
    try:
        _no_symlinks(directory)
        if not directory.is_dir():
            raise DashboardUnavailable()
        if session is not None and (not isinstance(session, str) or not INSTANCE.fullmatch(session)):
            raise DashboardUnavailable()
        paths = [directory / (session + ".json")] if session is not None else sorted(directory.glob("*.json"))
        candidates = []
        for path in paths:
            try:
                candidates.append(_session_details(repo, path))
            except (OSError, ValueError, TypeError, KeyError, studio().StudioError):
                continue
    except (OSError, ValueError) as exc:
        raise DashboardUnavailable() from exc
    if not candidates:
        raise DashboardUnavailable()
    if len(candidates) > 1:
        raise AmbiguousSessions([value["instanceId"] for value in candidates])
    return candidates[0]


class _LandingServer(backend().DesignHTTPServer):
    daemon_threads = False
    allow_reuse_address = False


class _LandingHandler(BaseHTTPRequestHandler):
    server_version = "UIDesignLanding/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *unused):
        pass

    @property
    def owner(self) -> DashboardSession:
        return self.server.dashboard_session

    def _respond(self, status: int, value: Any, content_type: str = "application/json; charset=utf-8") -> None:
        content = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(content)

    def _path(self) -> str:
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        if (parsed.query or parsed.fragment or parsed.scheme or parsed.netloc or "\\" in path
                or re.search(r"[\x00-\x1f\x7f-\x9f]", path) or any(piece in (".", "..") for piece in path.split("/"))):
            raise ValueError("Unsafe URL path")
        return path

    def _origin(self) -> str | None:
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1:
            return None
        origin = _normalized_origin("http://" + hosts[0])
        return origin if origin in self.owner._origins else None

    def _authorized(self) -> bool:
        headers = self.headers.get_all("Authorization", [])
        return len(headers) == 1 and secrets.compare_digest(headers[0], "Bearer " + self.owner.token)

    def do_GET(self):
        try:
            if self._origin() is None:
                self._respond(403, {"error": "Unlisted dashboard Host"})
                return
            path = self._path()
            if path in ("/api/identity", "/api/session"):
                if not self._authorized():
                    self._respond(401, {"error": "Bearer authentication required"})
                    return
                result = {"instanceId": self.owner.instance_id, "repo": str(self.owner.repo)} if path == "/api/identity" else self.owner.session_data()
                self._respond(200, result)
                return
            if path not in ASSETS:
                self._respond(404, {"error": "Not found"})
                return
            name, content_type = ASSETS[path]
            root = PAYLOAD / "skills/ui-design-studio/dashboard"
            self._respond(200, studio().safe_path(root, name).read_bytes(), content_type)
        except (OSError, ValueError, TypeError, studio().StudioError) as exc:
            self._respond(400, {"error": self.owner._safe_error(exc)})

    def do_POST(self):
        try:
            origin = self._origin()
            if origin is None:
                self._respond(403, {"error": "Unlisted dashboard Host"})
                return
            if self._path() != "/api/open":
                self._respond(404, {"error": "Not found"})
                return
            if not self._authorized():
                self._respond(401, {"error": "Bearer authentication required"})
                return
            origins = self.headers.get_all("Origin", [])
            if (len(origins) > 1 or (origins and _normalized_origin(origins[0]) != origin)
                    or self.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site")):
                self._respond(403, {"error": "Cross-origin mutation forbidden"})
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self._respond(415, {"error": "Content-Type application/json required"})
                return
            lengths = self.headers.get_all("Content-Length", [])
            if (len(lengths) != 1 or not lengths[0].isdecimal() or not 0 < int(lengths[0]) <= backend().MAX_BODY
                    or self.headers.get("Transfer-Encoding") is not None):
                self._respond(413, {"error": "Invalid JSON body length"})
                return
            payload = json.loads(self.rfile.read(int(lengths[0])))
            if not isinstance(payload, dict) or set(payload) != {"run"} or not isinstance(payload["run"], str):
                raise ValueError('Expected only {"run": "<repository-relative run path>"}')
            details = self.owner.open_run(payload["run"])
            candidates = [details["localUrl"], *details["lanUrls"], details.get("url")]
            hostname = urlsplit(origin).hostname
            destination = next((value for value in candidates if value and urlsplit(value).hostname == hostname), None)
            self._respond(200, {**details, "url": destination or details["qrUrl"] or details["localUrl"]})
        except (OSError, ValueError, TypeError, studio().StudioError) as exc:
            self._respond(400, {"error": self.owner._safe_error(exc)})

    def do_OPTIONS(self):
        self._respond(403, {"error": "Cross-origin access is not enabled"})


class DashboardSession:
    def __init__(self, repo: Path | str, host: str = "0.0.0.0", port: int = 0, lan_address: str | None = None):
        self.repo = _repo(repo)
        if host not in ("0.0.0.0", "127.0.0.1"):
            raise ValueError("Dashboard host must be 0.0.0.0 or 127.0.0.1")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError("Dashboard port must be between 0 and 65535")
        if lan_address is not None:
            lan_address = str(ipaddress.IPv4Address(lan_address))
        self.host, self.port, self.lan_address = host, port, lan_address
        self.instance_id = secrets.token_hex(24)
        self.token = secrets.token_urlsafe(32)
        self.selected_run: str | None = None
        self._handles: dict[Path, RunHandle] = {}
        self._lock = threading.RLock()
        self._closing = threading.Event()
        self._state: Literal["new", "starting", "live", "closing", "closed"] = "new"
        self._http: _LandingServer | None = None
        self._listener: threading.Thread | None = None
        self._watcher: threading.Thread | None = None
        self._record: Path | None = None
        self._published = False
        self._origins: frozenset[str] = frozenset()
        self._lan_addresses: tuple[str, ...] = ()
        self.local_url = ""
        self.lan_urls: list[str] = []
        self.url = ""
        self.started_at = ""
        self._closed = threading.Event()

    def _safe_error(self, error: BaseException) -> str:
        return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(error)).replace(self.token, "[private]")

    def _require_live(self) -> None:
        if self._closing.is_set() or self._state != "live":
            raise ValueError("Dashboard session is closed or unavailable")

    def _addresses(self, *, initial: bool = False) -> tuple[str, ...]:
        addresses = discover_lan_addresses()
        if self.lan_address is not None:
            if self.lan_address not in addresses:
                if initial:
                    raise ValueError("Selected LAN address is not on an up local interface")
                addresses = ()
            else:
                addresses = (self.lan_address,)
        return addresses if self.host == "0.0.0.0" else ()

    def _set_addresses(self, addresses: tuple[str, ...]) -> None:
        port = self._http.server_port
        self._lan_addresses = addresses
        self.local_url = f"http://127.0.0.1:{port}/#token={self.token}"
        self.lan_urls = [f"http://{address}:{port}/#token={self.token}" for address in addresses]
        self.url = self.lan_urls[0] if self.lan_urls else self.local_url
        suffix = "" if port == 80 else f":{port}"
        self._origins = frozenset(f"http://{address}{suffix}" for address in ("127.0.0.1", *addresses))

    def start(self) -> DashboardSession:
        admitted = False
        try:
            with self._lock:
                if self._state != "new" or self._closing.is_set():
                    raise ValueError("A dashboard session can only start once")
                admitted = True
                self._state = "starting"
                addresses = self._addresses(initial=True)
                directory = _private_directory(self.repo)
                self._record = directory / (self.instance_id + ".json")
                if self._record.exists() or self._record.is_symlink():
                    raise ValueError("Dashboard session identity already exists")
                self._http = _LandingServer((self.host, self.port), _LandingHandler)
                self._http.dashboard_session = self
                self._set_addresses(addresses)
                self._listener = threading.Thread(target=self._http.serve_forever, kwargs={"poll_interval": 0.1}, daemon=True)
                self._listener.start()
                identity_url = f"http://127.0.0.1:{self._http.server_port}/api/identity"
                if not _probe(identity_url, self.token, {"instanceId": self.instance_id, "repo": str(self.repo)}):
                    raise ValueError("Connection dashboard readiness check failed")
                self.started_at = _timestamp()
                self._state = "live"
                self._publish()
                self._watcher = threading.Thread(target=self._watch, daemon=True)
                self._watcher.start()
                return self
        except BaseException:
            if admitted:
                try:
                    self.close()
                except Exception as exc:
                    print("Dashboard startup cleanup incomplete: " + self._safe_error(exc), file=sys.stderr)
            raise

    def _landing_details(self) -> dict:
        return _details(self.repo, self.instance_id, None, self.local_url, self.lan_urls, self.url)

    def _live_details(self, root: Path, *, timeout: float = PROBE_TIMEOUT) -> dict | None:
        handle = self._handles.get(root)
        if isinstance(handle, OwnedRun):
            if handle.server.closed.is_set() or handle.server.stop.is_set():
                return None
            expected = handle.server.instance_id
        else:
            expected = handle.instance_id if isinstance(handle, ReusedRun) else None
        try:
            return _run_details(self.repo, root, expected_instance=expected, timeout=timeout)
        except (OSError, ValueError, TypeError, studio().StudioError):
            return None

    def _selected_details(self, observed: dict[Path, dict | None] | None = None) -> dict | None:
        if self.selected_run is None:
            return None
        try:
            root = _run_path(self.repo, self.selected_run)
            details = self._live_details(root) if observed is None else observed.get(root)
            if details is None:
                return None
            run = studio().read_json(studio().safe_path(root, "run.json"))
            return {key: details[key] for key in ("run", "instanceId", "localUrl", "lanUrls", "qrUrl", "url") if key in details} | {"id": run["id"]}
        except (OSError, ValueError, TypeError, studio().StudioError):
            return None

    def _publish(self) -> None:
        _write_record(self._record, {**self._landing_details(), "startedAt": self.started_at, "selectedRun": self._selected_details()})
        self._published = True

    def _refresh(self) -> None:
        with self._lock:
            self._require_live()
            addresses = self._addresses()
            for handle in self._handles.values():
                if isinstance(handle, OwnedRun) and not handle.server.closed.is_set() and not handle.server.stop.is_set():
                    handle.server.set_lan_addresses(addresses)
            if addresses != self._lan_addresses:
                self._set_addresses(addresses)
            self._publish()

    def _watch(self) -> None:
        while not self._closing.wait(POLL_INTERVAL):
            try:
                self._refresh()
            except Exception as exc:
                if not self._closing.is_set():
                    print("Dashboard observation failed: " + self._safe_error(exc), file=sys.stderr)

    def open_run(self, run: str) -> dict:
        if self._closing.is_set():
            raise ValueError("Dashboard session is closed or unavailable")
        with self._lock:
            self._require_live()
            root = _run_path(self.repo, run)
            details = self._live_details(root) if root in self._handles else None
            if details is None:
                handle = self._handles.get(root)
                if isinstance(handle, OwnedRun):
                    handle.server.close()
                self._handles.pop(root, None)
                try:
                    details = _run_details(self.repo, root)
                except (OSError, ValueError, TypeError, studio().StudioError):
                    details = None
                if details is not None:
                    self._handles[root] = ReusedRun(details["instanceId"], root)
                else:
                    engine = backend()
                    server = engine.DesignServer(engine.studio, root, host=self.host, port=0, repo=self.repo, lan_addresses=self._lan_addresses)
                    try:
                        server.start()
                    except Exception:
                        if not server.lock_contended:
                            raise
                        deadline = time.monotonic() + CONTENTION_TIMEOUT
                        while time.monotonic() < deadline:
                            remaining = deadline - time.monotonic()
                            details = self._live_details(root, timeout=min(PROBE_TIMEOUT, remaining))
                            if details is not None:
                                break
                            self._closing.wait(min(0.05, max(0.0, deadline - time.monotonic())))
                        if details is None:
                            raise ValueError("Design server owner is starting or unavailable.") from None
                        self._handles[root] = ReusedRun(details["instanceId"], root)
                    else:
                        self._handles[root] = OwnedRun(server)
                        details = self._live_details(root)
                        if details is None:
                            server.close()
                            self._handles.pop(root, None)
                            raise ValueError("Design dashboard readiness check failed")
            if root not in self._handles:
                self._handles[root] = ReusedRun(details["instanceId"], root)
            self.selected_run = root.relative_to(self.repo).as_posix()
            self._publish()
            return details

    def info(self, run: str | None = None) -> dict:
        with self._lock:
            self._require_live()
            if run is None:
                return self._landing_details()
            root = _run_path(self.repo, run)
            details = self._live_details(root)
            if details is None:
                raise DashboardUnavailable()
            return details

    def session_data(self) -> dict:
        with self._lock:
            self._require_live()
            candidates = []
            runs_root = _runs_root(self.repo)
            if runs_root.exists():
                for directory, children, files in os.walk(runs_root, followlinks=False):
                    children[:] = sorted(name for name in children if not name.startswith(".") and not (Path(directory) / name).is_symlink())
                    if "run.json" not in files:
                        continue
                    relative = Path(directory).relative_to(self.repo).as_posix()
                    try:
                        root = _run_path(self.repo, relative)
                        record = studio().read_json(studio().safe_path(root, "run.json"))
                    except (OSError, ValueError, TypeError, studio().StudioError):
                        continue
                    candidates.append((root, relative, record))
            deadline = time.monotonic() + PROBE_TIMEOUT

            def inspect(root):
                remaining = deadline - time.monotonic()
                return self._live_details(root, timeout=remaining) if remaining > 0 else None

            observed = {}
            if candidates:
                with ThreadPoolExecutor(max_workers=min(4, len(candidates))) as pool:
                    futures = {root: pool.submit(inspect, root) for root, unused, unused_record in candidates}
                    observed = {root: future.result() for root, future in futures.items()}
            runs = []
            for root, relative, record in candidates:
                details = observed[root]
                runs.append({"run": relative, "id": record["id"], "phase": record["phase"], "status": record["status"],
                             "selected": relative == self.selected_run, "live": details is not None, "dashboard": details})
            return {**self._landing_details(), "selectedRun": self._selected_details(observed), "runs": runs}

    def close(self) -> None:
        self._closing.set()
        with self._lock:
            if self._state == "closed":
                return
            wait_for_close = self._state == "closing"
            if not wait_for_close:
                self._state = "closing"
                handles = list(self._handles.values())
        if wait_for_close:
            self._closed.wait()
            return
        errors = []
        for handle in handles:
            if isinstance(handle, OwnedRun):
                try:
                    handle.server.close()
                except Exception as exc:
                    errors.append(self._safe_error(exc))
        if self._http is not None:
            try:
                if self._listener is not None and self._listener.is_alive():
                    self._http.shutdown()
                self._http.cancel_pending_reads()
                self._http.server_close()
            except Exception as exc:
                errors.append(self._safe_error(exc))
        for thread in (self._listener, self._watcher):
            if thread is not None and thread is not threading.current_thread():
                thread.join()
        with self._lock:
            if self._record is not None and self._published:
                try:
                    record = _read_json(self._record, private=True)
                    if record.get("instanceId") == self.instance_id and record.get("repo") == str(self.repo):
                        self._record.unlink()
                except FileNotFoundError:
                    pass
                except Exception as exc:
                    errors.append(self._safe_error(exc))
            self._state = "closed"
            self._closed.set()
        if errors:
            raise RuntimeError("Dashboard cleanup incomplete: " + "; ".join(errors))
