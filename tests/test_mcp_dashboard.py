"""Isolated adapter behavior checks, not application review evidence."""
from concurrent.futures import ThreadPoolExecutor
import asyncio
import contextlib
import datetime as dt
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ui_design_studio import dashboard
from ui_design_studio.runtime import backend, studio


def decode_terminal_qr(text):
    from PIL import Image
    import zxingcpp

    lines = text.splitlines()
    width = max(map(len, lines))
    image = Image.new("L", (width, len(lines) * 2), 0)
    glyphs = {" ": (0, 0), "▀": (255, 0), "▄": (0, 255), "█": (255, 255)}
    for row, line in enumerate(lines):
        for column, character in enumerate(line.ljust(width)):
            top, bottom = glyphs[character]
            image.putpixel((column, row * 2), top)
            image.putpixel((column, row * 2 + 1), bottom)
    decoded = zxingcpp.read_barcode(image.resize((width * 8, len(lines) * 16), Image.Resampling.NEAREST))
    return None if decoded is None else decoded.text


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name).resolve()
        self.real_inventory = dashboard.discover_lan_addresses
        self.inventory = mock.patch.object(dashboard, "discover_lan_addresses", return_value=()).start()
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(dashboard, "POLL_INTERVAL", 60).start()
        self.engine = studio()

    def session(self, **kwargs):
        session = dashboard.DashboardSession(self.repo, **kwargs)
        self.addCleanup(session.close)
        return session.start()

    def new_run(self):
        result = self.engine.init_run(self.repo, theme_id="mcp-smoke")
        root = Path(result["run"])
        return root, root.relative_to(self.repo).as_posix()

    def record(self, session):
        return self.repo / dashboard.SESSION_DIRECTORY / (session.instance_id + ".json")

    def write_private(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        path.chmod(0o600)

    def request(self, url, path="/api/session", *, method="GET", body=None, headers=None, authenticated=True, address=None):
        parsed = urlsplit(url)
        headers = dict(headers or {})
        if authenticated:
            headers.setdefault("Authorization", "Bearer " + parsed.fragment.removeprefix("token="))
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
            headers.setdefault("Content-Type", "application/json")
        client = http.client.HTTPConnection(address or parsed.hostname, parsed.port, timeout=5)
        try:
            client.request(method, path, body=body, headers=headers)
            response = client.getresponse()
            content = response.read()
            metadata = dict(response.getheaders())
            if response.getheader("Content-Type", "").startswith("application/json"):
                content = json.loads(content)
            return response.status, metadata, content
        finally:
            client.close()

    def assert_stopped(self, url):
        parsed = urlsplit(url)
        with self.assertRaises(OSError):
            with socket.create_connection((parsed.hostname, parsed.port), timeout=0.2):
                pass

    def test_waiting_session_has_real_listener_private_record_and_no_fake_run(self):
        session = self.session()
        details = session.info()
        self.assertIsNone(details["run"])
        self.assertEqual(details["lanUrls"], [])
        self.assertEqual(urlsplit(details["localUrl"]).port, session._http.server_port)
        self.assertRegex(details["instanceId"], r"^[0-9a-f]{48}$")
        self.assertFalse(list(self.repo.rglob("run.json")))
        record = json.loads(self.record(session).read_text())
        self.assertIsNone(record["selectedRun"])
        self.assertIsNone(record["run"])
        self.assertEqual(record["repo"], str(self.repo))
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.record(session).stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(self.record(session).parent.stat().st_mode), 0o700)
        code, headers, data = self.request(details["localUrl"])
        self.assertEqual(code, 200)
        self.assertEqual(data["runs"], [])
        self.assertEqual(data["text"], details["text"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        identity = self.request(details["localUrl"], "/api/identity")[2]
        self.assertEqual(identity, {"instanceId": session.instance_id, "repo": str(self.repo)})
        for path in ("/api/identity", "/api/session"):
            self.assertEqual(self.request(details["localUrl"], path, authenticated=False)[0], 401)
            self.assertEqual(self.request(details["localUrl"], path, headers={"Authorization": "Bearer wrong"})[0], 401)
        for path in ("/", "/landing.html", "/landing.js", "/dashboard.css"):
            code, unused, content = self.request(details["localUrl"], path, authenticated=False)
            self.assertEqual(code, 200)
            self.assertNotIn(session.token.encode(), content)
            self.assertNotIn(str(self.repo).encode(), content)
        html = self.request(details["localUrl"], "/")[2]
        self.assertIn(b"No design runs yet.", html)
        self.assertIn(b"Start or resume a run from your coding client.", html)
        self.assertNotIn(b"<progress", html)
        for path in ("/run.json", "/dashboard.js", "/../run.json", "/%2e%2e/run.json", "/api/session?token=secret"):
            self.assertIn(self.request(details["localUrl"], path)[0], (400, 404))

    def test_open_and_resume_use_one_owned_server_and_preserve_pending_run(self):
        session = self.session()
        root, relative = self.new_run()
        first = session.open_run(relative)
        second = session.open_run(relative)
        self.assertEqual(first["instanceId"], second["instanceId"])
        self.assertEqual(first["run"], relative)
        self.assertEqual(session.selected_run, relative)
        self.assertIsInstance(session._handles[root], dashboard.OwnedRun)
        self.assertEqual(len(list(self.repo.rglob("run.json"))), 1)
        self.assertEqual(self.engine.read_json(root / "run.json")["status"], "pending")
        self.assertEqual(session.info(relative)["instanceId"], first["instanceId"])
        self.assertEqual(dashboard.discover(self.repo, run=relative)["instanceId"], first["instanceId"])
        selected = json.loads(self.record(session).read_text())["selectedRun"]
        self.assertEqual(selected["run"], relative)
        self.assertEqual(selected["instanceId"], first["instanceId"])
        self.assertEqual(selected["id"], root.name)
        data = session.session_data()
        self.assertEqual(len(data["runs"]), 1)
        self.assertEqual(data["runs"][0]["phase"], "assessment")
        self.assertTrue(data["runs"][0]["live"])
        self.assertTrue(data["runs"][0]["selected"])
        locator = self.engine.read_json(root / ".design-server.json")
        public = json.dumps([first, data, json.loads(self.record(session).read_text())])
        for private in (locator["localShutdown"]["token"], locator["previewCapability"], locator["tempDirectory"]):
            self.assertNotIn(private, public)
        session.close()
        session.close()
        self.assert_stopped(first["localUrl"])
        self.assertTrue((root / "run.json").exists())
        self.assertTrue((root / ".design-server.lock").exists())
        self.assertFalse(self.record(session).exists())

    def test_landing_open_auth_origin_host_and_body_guards(self):
        self.inventory.return_value = ("192.0.2.8",)
        session = self.session()
        root, relative = self.new_run()
        url = session.local_url
        origin = "http://" + urlsplit(url).netloc
        body = {"run": relative}
        for headers, expected in (({"Origin": "https://attacker.invalid"}, 403), ({"Origin": "null"}, 403),
                                  ({"Sec-Fetch-Site": "cross-site"}, 403), ({"Sec-Fetch-Site": "same-site"}, 403),
                                  ({"Content-Type": "text/plain"}, 415), ({"Content-Length": "-1"}, 413),
                                  ({"Content-Length": str(backend().MAX_BODY + 1)}, 413), ({"Transfer-Encoding": "chunked"}, 413),
                                  ({"Host": "attacker.invalid"}, 403),
                                  ({"Host": "attacker.invalid", "Origin": "http://attacker.invalid"}, 403)):
            with self.subTest(headers=headers):
                self.assertEqual(self.request(url, "/api/open", method="POST", body=body, headers=headers)[0], expected)
        self.assertEqual(self.request(url, "/api/open", method="POST", body=body, authenticated=False)[0], 401)
        for payload in ({"run": relative, "extra": True}, {"run": 1}, {}, [], {"run": "../escape"}):
            self.assertEqual(self.request(url, "/api/open", method="POST", body=payload)[0], 400)
        self.assertEqual(self.request(url, "/api/open", method="POST", body="{", headers={"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request(url, "/api/shutdown", method="POST", body=body)[0], 404)
        self.assertFalse((root / ".design-server.json").exists())
        code, unused, opened = self.request(url, "/api/open", method="POST", body=body, headers={"Origin": origin})
        self.assertEqual(code, 200)
        self.assertEqual(opened["url"], opened["localUrl"])
        lan_origin = "http://" + urlsplit(session.lan_urls[0]).netloc
        self.assertEqual(self.request(url, "/api/open", method="POST", body=body,
                                      headers={"Host": urlsplit(session.lan_urls[0]).netloc, "Origin": origin})[0], 403)
        code, unused, opened = self.request(url, "/api/open", method="POST", body=body,
                                           headers={"Host": urlsplit(session.lan_urls[0]).netloc, "Origin": lan_origin})
        self.assertEqual(code, 200)
        self.assertEqual(urlsplit(opened["url"]).hostname, "192.0.2.8")

    def test_duplicate_host_and_body_length_are_rejected(self):
        session = self.session()
        unused, relative = self.new_run()
        port = session._http.server_port
        for duplicate, expected in (("Host", 403), ("Content-Length", 413)):
            client = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            self.addCleanup(client.close)
            payload = json.dumps({"run": relative}).encode()
            client.putrequest("POST", "/api/open", skip_host=True)
            client.putheader("Host", f"127.0.0.1:{port}")
            client.putheader("Authorization", "Bearer " + session.token)
            client.putheader("Content-Type", "application/json")
            client.putheader("Content-Length", str(len(payload)))
            client.putheader(duplicate, f"127.0.0.1:{port}" if duplicate == "Host" else str(len(payload)))
            client.endheaders(payload)
            response = client.getresponse()
            self.assertEqual(response.status, expected)
            response.read()

    def test_network_inventory_filters_and_sorts_without_hostname_guessing(self):
        address = lambda value, family=socket.AF_INET: SimpleNamespace(family=family, address=value)
        interfaces = {"z-wire": [address("10.0.0.12"), address("10.0.0.2")],
                      "a-wire": [address("192.168.2.8"), address("127.0.0.1"), address("169.254.1.2"),
                                 address("0.0.0.0"), address("224.0.0.2"), address("::1", socket.AF_INET6), address("invalid")],
                      "down": [address("10.9.9.9")], "missing": [address("10.8.8.8")]}
        with mock.patch.object(dashboard.psutil, "net_if_addrs", return_value=interfaces), \
             mock.patch.object(dashboard.psutil, "net_if_stats", return_value={"z-wire": SimpleNamespace(isup=True), "a-wire": SimpleNamespace(isup=True), "down": SimpleNamespace(isup=False)}):
            self.assertEqual(self.real_inventory(), ("192.168.2.8", "10.0.0.2", "10.0.0.12"))
        with mock.patch.object(dashboard.psutil, "net_if_addrs", return_value={}), mock.patch.object(dashboard.psutil, "net_if_stats", return_value={}):
            self.assertEqual(self.real_inventory(), ())
        self.inventory.return_value = ("10.0.0.2", "10.0.0.12")
        selected = self.session(lan_address="10.0.0.12")
        self.assertEqual([urlsplit(value).hostname for value in selected.info()["lanUrls"]], ["10.0.0.12"])
        self.assertEqual(selected.info()["qrUrl"], selected.info()["lanUrls"][0])
        loopback = self.session(host="127.0.0.1")
        self.assertEqual(loopback.info()["lanUrls"], [])
        self.assertEqual(loopback.info()["qrUrl"], loopback.info()["localUrl"])
        with self.assertRaisesRegex(ValueError, "not on an up local interface"):
            self.session(lan_address="192.0.2.99")

    def test_refresh_replaces_owned_aliases_and_revokes_removed_origins(self):
        self.inventory.return_value = ("192.0.2.8", "192.0.2.9")
        session = self.session()
        root, relative = self.new_run()
        session.open_run(relative)
        owned = session._handles[root].server
        removed_host = urlsplit(session.lan_urls[0]).netloc
        run_host = urlsplit(owned.lan_urls[0]).netloc
        first_observation = json.loads(self.record(session).read_text())["observedAt"]
        self.inventory.return_value = ("192.0.2.9",)
        session._refresh()
        self.assertEqual([urlsplit(value).hostname for value in session.lan_urls], ["192.0.2.9"])
        self.assertEqual([urlsplit(value).hostname for value in owned.lan_urls], ["192.0.2.9"])
        self.assertEqual(self.request(session.local_url, headers={"Host": removed_host})[0], 403)
        self.assertEqual(self.request(owned.local_url, "/api/snapshot", headers={"Host": run_host})[0], 403)
        record = json.loads(self.record(session).read_text())
        self.assertNotEqual(record["observedAt"], first_observation)
        self.assertEqual(record["lanUrls"], session.lan_urls)
        self.assertEqual(record["selectedRun"]["lanUrls"], owned.lan_urls)
        locator = self.engine.read_json(root / ".design-server.json")
        snapshot = self.engine.read_json(root / ".design-status.json")
        self.assertEqual(locator["lanUrls"], owned.lan_urls)
        self.assertEqual(snapshot["server"]["lanUrls"], owned.lan_urls)
        self.assertEqual(snapshot["server"]["url"], owned.lan_urls[0])

    def test_explicit_address_removed_later_advertises_no_lan(self):
        self.inventory.return_value = ("192.0.2.8",)
        session = self.session(lan_address="192.0.2.8")
        self.inventory.return_value = ("192.0.2.9",)
        session._refresh()
        self.assertEqual(session.info()["lanUrls"], [])
        self.assertIn("[lan] unavailable\n", session.info()["text"])
        self.assertEqual(session.info()["qrUrl"], session.local_url)

    def test_heartbeat_updates_private_observation_without_a_run(self):
        with mock.patch.object(dashboard, "POLL_INTERVAL", 0.02):
            session = self.session()
            first = json.loads(self.record(session).read_text())["observedAt"]
            deadline = time.monotonic() + 2
            observed = first
            while observed == first and time.monotonic() < deadline:
                time.sleep(0.02)
                observed = json.loads(self.record(session).read_text())["observedAt"]
            self.assertNotEqual(observed, first)
            self.assertFalse(list(self.repo.rglob("run.json")))
            session.close()

    def test_two_clients_open_concurrently_borrow_without_borrower_teardown(self):
        first, second = self.session(), self.session()
        root, relative = self.new_run()
        self.assertNotEqual(first.instance_id, second.instance_id)
        self.assertNotEqual(first._http.server_port, second._http.server_port)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(session.open_run, relative) for session in (first, second)]
            details = [future.result(timeout=10) for future in futures]
        self.assertEqual(details[0]["instanceId"], details[1]["instanceId"])
        owner, borrower = (first, second) if isinstance(first._handles[root], dashboard.OwnedRun) else (second, first)
        self.assertIsInstance(owner._handles[root], dashboard.OwnedRun)
        self.assertIsInstance(borrower._handles[root], dashboard.ReusedRun)
        borrowed_url = details[0]["localUrl"]
        borrower.close()
        self.assertEqual(self.request(borrowed_url, "/api/identity")[0], 200)
        third = self.session()
        self.assertEqual(third.open_run(relative)["instanceId"], details[0]["instanceId"])
        owner.close()
        data = third.session_data()
        self.assertFalse(data["runs"][0]["live"])
        self.assertIsNone(data["runs"][0]["dashboard"])
        self.assertIsNone(data["selectedRun"])
        self.assertEqual(self.request(third.local_url, "/api/identity")[0], 200)
        reopened = third.open_run(relative)
        self.assertNotEqual(reopened["instanceId"], details[0]["instanceId"])
        self.assertIsInstance(third._handles[root], dashboard.OwnedRun)

    def test_borrowed_loopback_server_is_not_given_fake_lan_aliases(self):
        owner = self.session(host="127.0.0.1")
        root, relative = self.new_run()
        owned = owner.open_run(relative)
        self.inventory.return_value = ("192.0.2.8",)
        borrower = self.session()
        borrowed = borrower.open_run(relative)
        self.assertEqual(borrowed["instanceId"], owned["instanceId"])
        self.assertEqual(borrowed["lanUrls"], [])
        self.assertEqual(borrowed["localUrl"], owned["localUrl"])
        with mock.patch.object(owner._handles[root].server, "set_lan_addresses", wraps=owner._handles[root].server.set_lan_addresses) as mutate:
            self.inventory.return_value = ("192.0.2.9",)
            borrower._refresh()
            mutate.assert_not_called()
        self.assertEqual(self.engine.read_json(root / ".design-server.json")["lanUrls"], [])

    def test_owner_publication_race_retries_only_after_actual_lock_contention(self):
        owner, borrower = self.session(), self.session()
        root, relative = self.new_run()
        engine = backend()
        publishing, release, contended = threading.Event(), threading.Event(), threading.Event()
        original_publish, original_start = engine.private_json, engine.DesignServer.start

        def publication(studio_module, path, value):
            if Path(path).name == ".design-server.json" and not publishing.is_set():
                publishing.set()
                if not release.wait(5):
                    raise RuntimeError("Test did not release the owner publication")
            return original_publish(studio_module, path, value)

        def start(server):
            try:
                return original_start(server)
            except Exception:
                if server.lock_contended:
                    contended.set()
                raise

        with mock.patch.object(engine, "private_json", side_effect=publication), mock.patch.object(engine.DesignServer, "start", start):
            with ThreadPoolExecutor(max_workers=2) as pool:
                owning = pool.submit(owner.open_run, relative)
                self.assertTrue(publishing.wait(3))
                borrowing = pool.submit(borrower.open_run, relative)
                try:
                    self.assertTrue(contended.wait(3))
                finally:
                    release.set()
                first, second = owning.result(timeout=10), borrowing.result(timeout=10)
        self.assertEqual(first["instanceId"], second["instanceId"])
        self.assertIsInstance(borrower._handles[root], dashboard.ReusedRun)
        self.assertEqual(self.engine.read_json(root / ".design-server.json")["instanceId"], first["instanceId"])

    def test_locked_unresponsive_owner_is_not_replaced_or_killed(self):
        session = self.session()
        root, relative = self.new_run()
        engine = backend()
        foreign = {"schemaVersion": "1.0", "instanceId": "a" * 48, "run": str(root),
                   "url": "http://127.0.0.1:1/#token=" + "b" * 43, "localUrl": "http://127.0.0.1:1/#token=" + "b" * 43,
                   "lanUrls": [], "probeUrl": "http://127.0.0.1:1/api/identity"}
        self.write_private(root / ".design-server.json", foreign)
        before = (root / ".design-server.json").read_bytes()
        with engine.FileLock(root / ".design-server.lock", engine.studio), mock.patch.object(dashboard, "CONTENTION_TIMEOUT", 0.1):
            with self.assertRaisesRegex(ValueError, r"^Design server owner is starting or unavailable\.$"):
                session.open_run(relative)
        self.assertEqual((root / ".design-server.json").read_bytes(), before)
        self.assertIsNone(session.selected_run)
        self.assertEqual(session._handles, {})
        self.assertEqual(len(list(self.repo.rglob("run.json"))), 1)

    def test_malformed_locked_locator_is_not_replaced(self):
        session = self.session()
        root, relative = self.new_run()
        path = root / ".design-server.json"
        path.write_text("{malformed", encoding="utf-8")
        path.chmod(0o600)
        engine = backend()
        with engine.FileLock(root / ".design-server.lock", engine.studio), mock.patch.object(dashboard, "CONTENTION_TIMEOUT", 0.1):
            with self.assertRaisesRegex(ValueError, "Design server owner is starting or unavailable"):
                session.open_run(relative)
        self.assertEqual(path.read_text(), "{malformed")
        self.assertIsNone(session.selected_run)

    def test_noncontention_run_listener_failure_is_not_retried(self):
        session = self.session()
        root, relative = self.new_run()
        with mock.patch.object(backend(), "DesignHTTPServer", side_effect=PermissionError("Synthetic bind denied")) as listener, \
             mock.patch.object(dashboard, "_probe", wraps=dashboard._probe) as probe:
            with self.assertRaisesRegex(PermissionError, "Synthetic bind denied"):
                session.open_run(relative)
        self.assertEqual(listener.call_count, 1)
        probe.assert_not_called()
        self.assertFalse((root / ".design-server.json").exists())
        self.assertEqual(session._handles, {})
        with backend().FileLock(root / ".design-server.lock", backend().studio):
            pass

    def test_occupied_landing_port_fails_without_fallback_or_foreign_cleanup(self):
        occupied = socket.socket()
        self.addCleanup(occupied.close)
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        session = dashboard.DashboardSession(self.repo, port=occupied.getsockname()[1])
        self.addCleanup(session.close)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(OSError):
            session.start()
        self.assertEqual(output.getvalue(), "")
        self.assertFalse(list((self.repo / dashboard.SESSION_DIRECTORY).glob("*.json")))
        self.assertFalse(list(self.repo.rglob("run.json")))
        self.assertGreater(occupied.fileno(), -1)

    def test_failed_publication_and_readiness_unwind_partial_listeners(self):
        for failure in ("publication", "readiness"):
            with self.subTest(failure=failure):
                session = dashboard.DashboardSession(self.repo)
                self.addCleanup(session.close)
                patch = mock.patch.object(dashboard, "_write_record", side_effect=OSError("Synthetic private-record failure")) if failure == "publication" else mock.patch.object(dashboard, "_probe", return_value=False)
                with patch, self.assertRaises((OSError, ValueError)):
                    session.start()
                self.assert_stopped(session.local_url)
                self.assertFalse(session._listener.is_alive())
                self.assertFalse(self.record(session).exists())
        self.assertFalse(list(self.repo.rglob("run.json")))

    def test_second_start_does_not_close_a_live_session(self):
        session = self.session()
        with self.assertRaisesRegex(ValueError, "only start once"):
            session.start()
        self.assertEqual(self.request(session.local_url, "/api/identity")[0], 200)

    def test_close_drains_an_admitted_open_and_rejects_new_opens(self):
        session = self.session()
        root, relative = self.new_run()
        admitted, release = threading.Event(), threading.Event()
        original = backend().DesignServer.start

        def slow_start(server):
            admitted.set()
            if not release.wait(5):
                raise RuntimeError("Test did not release admitted startup")
            return original(server)

        with mock.patch.object(backend().DesignServer, "start", slow_start):
            with ThreadPoolExecutor(max_workers=3) as pool:
                opening = pool.submit(session.open_run, relative)
                self.assertTrue(admitted.wait(3))
                closing = pool.submit(session.close)
                self.assertTrue(session._closing.wait(3))
                with self.assertRaisesRegex(ValueError, "closed or unavailable"):
                    session.open_run(relative)
                other_close = pool.submit(session.close)
                release.set()
                details = opening.result(timeout=10)
                closing.result(timeout=10)
                other_close.result(timeout=10)
        self.assert_stopped(details["localUrl"])
        self.assert_stopped(session.local_url)
        self.assertFalse((root / ".design-server.json").exists())

    def test_run_paths_obey_custom_configuration_and_reject_symlinks(self):
        (self.repo / "ui-design-studio.json").write_text(json.dumps({"paths": {"runs": "work/design-runs"}}))
        session = self.session()
        root, relative = self.new_run()
        self.assertTrue(relative.startswith("work/design-runs/"))
        for unsafe in (str(root), "../escape", "work/design-runs/../escape", relative + "/.", relative.replace("/", "\\"), relative + "/", "themes"):
            with self.subTest(unsafe=unsafe), self.assertRaises((ValueError, self.engine.StudioError)):
                session.open_run(unsafe)
        target = self.repo / "work/design-runs/link"
        target.symlink_to(root, target_is_directory=True)
        with self.assertRaisesRegex(self.engine.StudioError, "Symlink"):
            session.open_run(target.relative_to(self.repo).as_posix())
        session.open_run(relative)
        self.assertEqual([run["run"] for run in session.session_data()["runs"]], [relative])

    def test_symlink_runtime_paths_are_never_followed(self):
        outside = self.repo / "outside"
        outside.mkdir()
        (self.repo / ".ui-design-studio").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.session()
        with self.assertRaises(dashboard.DashboardUnavailable):
            dashboard.discover(self.repo)
        self.assertEqual(list(outside.iterdir()), [])

    def test_private_record_replacement_does_not_overwrite_or_remove_foreign_owner(self):
        session = self.session()
        path = self.record(session)
        foreign = json.loads(path.read_text())
        foreign["instanceId"] = "f" * 48
        self.write_private(path, foreign)
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "another owner"):
            session._refresh()
        session.close()
        self.assertEqual(path.read_bytes(), before)
        self.assert_stopped(session.local_url)

    def test_session_identity_collision_never_removes_an_existing_connection_record(self):
        existing = self.session()
        path = self.record(existing)
        before = path.read_bytes()
        collision = dashboard.DashboardSession(self.repo)
        self.addCleanup(collision.close)
        collision.instance_id = existing.instance_id
        with self.assertRaisesRegex(ValueError, "identity already exists"):
            collision.start()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.request(existing.local_url, "/api/identity")[0], 200)

    def test_discovery_is_read_only_and_ambiguous_sessions_need_explicit_selection(self):
        with self.assertRaisesRegex(dashboard.DashboardUnavailable, r"^Dashboard is not running\.$"):
            dashboard.discover(self.repo)
        self.assertFalse((self.repo / dashboard.SESSION_DIRECTORY).exists())
        with self.assertRaises(dashboard.DashboardUnavailable):
            dashboard.discover(self.repo, run="docs/design/runs/missing")
        with self.assertRaisesRegex(ValueError, "portable repository-relative"):
            dashboard.discover(self.repo, run="../escape")
        self.assertFalse((self.repo / dashboard.SESSION_DIRECTORY).exists())
        first, second = self.session(), self.session()
        with self.assertRaises(dashboard.AmbiguousSessions) as raised:
            dashboard.discover(self.repo)
        self.assertEqual(raised.exception.session_ids, sorted([first.instance_id, second.instance_id]))
        self.assertNotIn(first.token, str(raised.exception))
        self.assertEqual(dashboard.discover(self.repo, session=second.instance_id)["localUrl"], second.local_url)
        second.close()
        self.assertEqual(dashboard.discover(self.repo)["instanceId"], first.instance_id)
        with self.assertRaises(dashboard.DashboardUnavailable):
            dashboard.discover(self.repo, session="../foreign")

    def test_discovery_verifies_stale_records_and_reconstructs_untrusted_cached_text(self):
        session = self.session()
        path = self.record(session)
        original = json.loads(path.read_text())
        record = dict(original, observedAt=(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)).isoformat(), text="\x1b[2JUNTRUSTED")
        self.write_private(path, record)
        with mock.patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:1", "http_proxy": "http://127.0.0.1:1", "NO_PROXY": "", "no_proxy": ""}):
            live = dashboard.discover(self.repo)
        self.assertEqual(live["instanceId"], session.instance_id)
        self.assertEqual(live["text"], original["text"])
        self.assertNotIn("\x1b", live["text"])
        session.close()
        self.write_private(path, record)
        with self.assertRaises(dashboard.DashboardUnavailable):
            dashboard.discover(self.repo)
        self.assertTrue(path.exists(), "Discovery must not delete a crashed connection's record")

    def test_forged_and_unsafe_session_records_are_not_reported_as_live(self):
        session = self.session()
        path = self.record(session)
        original = json.loads(path.read_text())
        for change in ({"repo": str(self.repo / "other")}, {"instanceId": "a" * 48}, {"state": "stopped"},
                       {"localUrl": "http://attacker.invalid:1234/#token=" + session.token},
                       {"localUrl": "http://127.0.0.2:1234/#token=" + session.token},
                       {"qrUrl": "http://attacker.invalid/#token=" + session.token}, {"observedAt": "tomorrow"},
                       {"lanUrls": ["http://192.0.2.8:1/#token=" + "x" * 43]}):
            with self.subTest(change=change):
                self.write_private(path, dict(original, **change))
                with self.assertRaises(dashboard.DashboardUnavailable):
                    dashboard.discover(self.repo)
        self.write_private(path, original)
        if os.name != "nt":
            path.chmod(0o644)
            with self.assertRaises(dashboard.DashboardUnavailable):
                dashboard.discover(self.repo)
            path.chmod(0o600)
        saved = path.with_suffix(".saved")
        path.rename(saved)
        path.symlink_to(saved)
        try:
            with self.assertRaises(dashboard.DashboardUnavailable):
                dashboard.discover(self.repo)
        finally:
            path.unlink()
            saved.rename(path)

    def test_run_discovery_rejects_forged_probe_before_any_network_access(self):
        session = self.session()
        root, relative = self.new_run()
        session.open_run(relative)
        path = root / ".design-server.json"
        original = self.engine.read_json(path)
        for probe in ("http://attacker.invalid:1234/api/identity", "http://localhost:1234/api/identity", "http://127.0.0.1:1234/api/shutdown",
                      "http://user@127.0.0.1:1234/api/identity", "http://127.0.0.1:1234/api/identity?token=private"):
            self.write_private(path, dict(original, probeUrl=probe))
            with mock.patch.object(dashboard.http.client, "HTTPConnection") as connection:
                with self.assertRaises(dashboard.DashboardUnavailable):
                    dashboard.discover(self.repo, run=relative)
                connection.assert_not_called()
        self.write_private(path, original)

    def test_probe_forbids_redirects_bounds_bodies_and_checks_full_identity(self):
        expected = {"instanceId": "a" * 48, "repo": str(self.repo)}
        observed = []
        state = {"status": 200, "payload": expected, "delay": 0}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *unused):
                pass

            def do_GET(self):
                observed.append((self.path, self.headers.get("Authorization")))
                if state["delay"]:
                    time.sleep(state["delay"])
                payload = json.dumps(state["payload"]).encode()
                try:
                    self.send_response(state["status"])
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("Location", "http://attacker.invalid/")
                    self.end_headers()
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        listener = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        listener.daemon_threads = True
        thread = threading.Thread(target=listener.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(listener.server_close)
        self.addCleanup(listener.shutdown)
        url = f"http://127.0.0.1:{listener.server_port}/api/identity"
        self.assertTrue(dashboard._probe(url, "private-token", expected))
        state["status"] = 302
        before = len(observed)
        self.assertFalse(dashboard._probe(url, "private-token", expected))
        self.assertEqual(len(observed), before + 1)
        state.update(status=200, payload={"instanceId": expected["instanceId"], "repo": "/forged"})
        self.assertFalse(dashboard._probe(url, "private-token", expected))
        state["payload"] = {**expected, "padding": "x" * (dashboard.MAX_IDENTITY + 1)}
        self.assertFalse(dashboard._probe(url, "private-token", expected))
        state.update(payload=expected, delay=0.2)
        self.assertFalse(dashboard._probe(url, "private-token", expected, timeout=0.03))
        self.assertTrue(all(path == "/api/identity" and authorization == "Bearer private-token" for path, authorization in observed))

    def test_probe_deadline_cannot_be_extended_by_trickled_response_headers(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *unused):
                pass

            def do_GET(self):
                try:
                    for value in b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}":
                        self.connection.sendall(bytes([value]))
                        time.sleep(0.005)
                except OSError:
                    pass

        listener = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        listener.daemon_threads = True
        thread = threading.Thread(target=listener.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(listener.server_close)
        self.addCleanup(listener.shutdown)
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(dashboard._probe, f"http://127.0.0.1:{listener.server_port}/api/identity",
                                 "private-token", {"instanceId": "a" * 48}, timeout=0.03)
            self.assertFalse(result.result(timeout=0.2))

    def test_real_lan_listener_and_specific_bind_never_claim_false_loopback(self):
        available = self.real_inventory()
        if not available:
            self.skipTest("No up non-loopback IPv4 interface exists for the real LAN listener check")
        address = available[0]
        self.inventory.return_value = (address,)
        session = self.session()
        code, unused, identity = self.request(session.lan_urls[0], "/api/identity")
        self.assertEqual(code, 200)
        self.assertEqual(identity["instanceId"], session.instance_id)
        root, relative = self.new_run()
        server = backend().DesignServer(backend().studio, root, host=address, repo=self.repo).start()
        self.addCleanup(server.close)
        details = dashboard.discover(self.repo, run=relative)
        self.assertIsNone(details["localUrl"])
        self.assertEqual(urlsplit(details["qrUrl"]).hostname, address)
        self.assertTrue(details["text"].startswith("[ok] Dashboard live → " + server.url + "\n"))
        self.assertNotIn("http://127.0.0.1:", details["text"])

    def test_cli_json_and_human_output_share_independently_decodable_qr(self):
        self.inventory.return_value = ("192.0.2.8",)
        session = self.session()
        root, relative = self.new_run()
        session.open_run(relative)
        source = Path(__file__).resolve().parents[1] / "src"
        environment = dict(os.environ, PYTHONPATH=str(source) + os.pathsep + os.environ.get("PYTHONPATH", ""))
        command = [sys.executable, "-c", "from ui_design_studio.cli import main; raise SystemExit(main())", "dashboard-info", "--repo", str(self.repo)]
        for selection in (["--session", session.instance_id], ["--run", relative]):
            with self.subTest(selection=selection):
                human = subprocess.run([*command, *selection], text=True, capture_output=True, cwd=self.repo, env=environment, timeout=10)
                encoded = subprocess.run([*command, *selection, "--json"], text=True, capture_output=True, cwd=self.repo, env=environment, timeout=10)
                self.assertEqual(human.returncode, 0, human.stderr)
                self.assertEqual(encoded.returncode, 0, encoded.stderr)
                details = json.loads(encoded.stdout)
                self.assertEqual(human.stdout.rstrip("\n"), details["text"].rstrip("\n"))
                labels, qr = human.stdout.split("\n\n", 1)
                self.assertEqual(labels.splitlines(), ["[ok] Dashboard live → " + details["localUrl"], *["[lan] " + value for value in details["lanUrls"]]])
                self.assertIn("#token=", labels)
                self.assertTrue(all(character == " " or character == "\n" or "\u2580" <= character <= "\u259f" for character in qr))
                self.assertEqual(decode_terminal_qr(qr), details["qrUrl"], "The emitted terminal QR must decode independently")
                self.assertEqual(human.stderr, "")
        self.assertTrue((root / "run.json").exists())

    def test_cli_errors_never_print_success_or_qr_and_ambiguity_lists_session_commands(self):
        source = Path(__file__).resolve().parents[1] / "src"
        environment = dict(os.environ, PYTHONPATH=str(source) + os.pathsep + os.environ.get("PYTHONPATH", ""))
        command = [sys.executable, "-c", "from ui_design_studio.cli import main; raise SystemExit(main())", "dashboard-info", "--repo", str(self.repo)]
        unavailable = subprocess.run(command, text=True, capture_output=True, env=environment, timeout=10)
        self.assertEqual(unavailable.returncode, 1)
        self.assertEqual(unavailable.stdout, "")
        self.assertEqual(unavailable.stderr.strip(), "[error] Dashboard is not running.")
        first, second = self.session(), self.session()
        ambiguous = subprocess.run(command, text=True, capture_output=True, env=environment, timeout=10)
        self.assertEqual(ambiguous.returncode, 2)
        for session in (first, second):
            self.assertIn(session.instance_id, ambiguous.stderr)
            self.assertIn("--session " + session.instance_id, ambiguous.stderr)
            self.assertNotIn(session.token, ambiguous.stderr)
        encoded = subprocess.run([*command, "--json"], text=True, capture_output=True, env=environment, timeout=10)
        self.assertEqual(encoded.returncode, 2)
        result = json.loads(encoded.stdout)
        self.assertNotIn("[ok]", encoded.stdout)
        self.assertIn(first.instance_id, json.dumps(result))

    def test_default_ports_normalize_origins_without_changing_printed_urls(self):
        capability = "#token=" + "t" * 43
        local = "http://127.0.0.1:80/" + capability
        lan = "http://192.0.2.8:80/" + capability
        details = dashboard._details(self.repo, "a" * 48, None, local, [lan], lan)
        self.assertEqual(details["localUrl"], local)
        self.assertEqual(details["qrUrl"], lan)
        self.assertTrue(details["text"].startswith("[ok] Dashboard live → " + local + "\n[lan] " + lan + "\n\n"))
        implicit = dashboard._details(self.repo, "a" * 48, None, local.replace(":80", ""), [lan], lan)
        self.assertEqual(implicit["localUrl"], local.replace(":80", ""))
        self.assertEqual(dashboard._normalized_origin("http://127.0.0.1:80"), "http://127.0.0.1")
        self.assertEqual(dashboard._normalized_origin("https://example.test:443"), "https://example.test")
        for invalid in ("http://127.0.0.1/path", "http://user@127.0.0.1", "http://127.0.0.1#fragment", "null"):
            self.assertIsNone(dashboard._normalized_origin(invalid))
        handler = object.__new__(dashboard._LandingHandler)
        handler.server = SimpleNamespace(dashboard_session=SimpleNamespace(_origins=frozenset({"http://127.0.0.1"})))
        handler.headers = http.client.HTTPMessage()
        handler.headers["Host"] = "127.0.0.1"
        self.assertEqual(handler._origin(), "http://127.0.0.1")
        handler.headers.replace_header("Host", "127.0.0.1:80")
        self.assertEqual(handler._origin(), "http://127.0.0.1")
        handler.headers.replace_header("Host", "127.0.0.1:81")
        self.assertIsNone(handler._origin())

    def test_constructor_rejects_implicit_repo_bad_bind_and_invalid_port(self):
        for arguments in ((Path("."), {}), (self.repo, {"host": "192.0.2.8"}), (self.repo, {"port": -1}),
                          (self.repo, {"port": 65536}), (self.repo, {"port": True}), (self.repo, {"lan_address": "localhost"})):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                dashboard.DashboardSession(arguments[0], **arguments[1])

    def test_close_cancels_unfinished_landing_headers_without_leaving_a_record(self):
        session = self.session()
        entered = threading.Event()
        setup = dashboard._LandingHandler.setup

        def observe_setup(handler):
            setup(handler)
            entered.set()

        with mock.patch.object(dashboard._LandingHandler, "setup", observe_setup):
            client = socket.create_connection(("127.0.0.1", session._http.server_port), timeout=2)
            self.addCleanup(client.close)
            client.sendall(b"GET /api/session HTTP/1.1\r\nX-Slow: unfinished")
            self.assertTrue(entered.wait(2))
            closer = threading.Thread(target=session.close, daemon=True)
            closer.start()
            self.assertTrue(session._closed.wait(3))
            closer.join(3)
        self.assertFalse(self.record(session).exists())

    def test_refresh_retries_owned_alias_publication_before_committing_session_addresses(self):
        self.inventory.return_value = ("192.0.2.8",)
        session = self.session()
        root, relative = self.new_run()
        session.open_run(relative)
        owned = session._handles[root].server
        update = owned.set_lan_addresses
        failed = False

        def fail_once(addresses):
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("Synthetic owned alias update failure")
            update(addresses)

        self.inventory.return_value = ("192.0.2.9",)
        with mock.patch.object(owned, "set_lan_addresses", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "Synthetic owned alias update failure"):
                session._refresh()
            session._refresh()
        self.assertEqual(urlsplit(owned.lan_urls[0]).hostname, "192.0.2.9")
        self.assertEqual(urlsplit(session.lan_urls[0]).hostname, "192.0.2.9")
        self.assertEqual(self.engine.read_json(root / ".design-server.json")["lanUrls"], owned.lan_urls)

    def test_empty_query_and_fragment_delimiters_are_not_valid_host_or_origin_values(self):
        session = self.session()
        port = session._http.server_port
        for suffix in ("?", "#"):
            code, unused_headers, unused_body = self.request(session.local_url, headers={"Host": f"127.0.0.1:{port}{suffix}"})
            self.assertEqual(code, 403)

    def test_refresh_reconciles_each_owned_server_when_inventory_returns_after_partial_failure(self):
        self.inventory.return_value = ("192.0.2.8",)
        session = self.session()
        first_root, first_run = self.new_run()
        second_root, second_run = self.new_run()
        session.open_run(first_run)
        session.open_run(second_run)
        second = session._handles[second_root].server
        self.inventory.return_value = ("192.0.2.9",)
        with mock.patch.object(second, "set_lan_addresses", side_effect=OSError("Synthetic second run update failure")):
            with self.assertRaisesRegex(OSError, "Synthetic second run update failure"):
                session._refresh()
        self.inventory.return_value = ("192.0.2.8",)
        session._refresh()
        for run in (first_run, second_run):
            self.assertEqual(urlsplit(session.info(run)["lanUrls"][0]).hostname, "192.0.2.8")
        self.assertEqual(urlsplit(self.engine.read_json(first_root / ".design-server.json")["url"]).hostname, "192.0.2.8")

    def test_unresponsive_foreign_runs_do_not_hide_a_healthy_landing_or_owned_run(self):
        release = threading.Event()

        class StalledOwner(BaseHTTPRequestHandler):
            def log_message(self, *unused):
                pass

            def do_GET(self):
                release.wait(5)

        listener = ThreadingHTTPServer(("127.0.0.1", 0), StalledOwner)
        listener.daemon_threads = True
        thread = threading.Thread(target=listener.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(listener.server_close)
        self.addCleanup(listener.shutdown)
        self.addCleanup(release.set)
        session = self.session()
        for index in range(3):
            root, unused_run = self.new_run()
            url = f"http://127.0.0.1:{listener.server_port}/#token=" + "t" * 43
            self.write_private(root / ".design-server.json", {
                "schemaVersion": "1.0", "instanceId": str(index) * 48, "run": str(root),
                "url": url, "localUrl": url, "lanUrls": [],
                "probeUrl": f"http://127.0.0.1:{listener.server_port}/api/identity",
            })
        unused_root, healthy_run = self.new_run()
        healthy = session.open_run(healthy_run)
        code, unused_headers, data = self.request(session.local_url)
        self.assertEqual(code, 200)
        self.assertEqual(len(data["runs"]), 4)
        live = [run for run in data["runs"] if run["live"]]
        self.assertEqual([run["run"] for run in live], [healthy_run])
        self.assertEqual(data["selectedRun"]["instanceId"], healthy["instanceId"])


class ForegroundDashboardTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ui-design-foreground-")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name).resolve()
        source = Path(__file__).resolve().parents[1] / "src"
        self.environment = dict(os.environ, PYTHONPATH=str(source))
        self.command = [sys.executable, "-m", "ui_design_studio.cli"]

    async def launch(self, *extra, parent_stdio=True, json_output=True, host="127.0.0.1"):
        arguments = [*self.command, "dashboard-serve", "--repo", str(self.repo), "--dashboard-host", host]
        if parent_stdio:
            arguments.append("--parent-stdio")
        if json_output:
            arguments.append("--json")
        process = await asyncio.create_subprocess_exec(
            *arguments, *extra, stdin=asyncio.subprocess.PIPE if parent_stdio else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.repo, env=self.environment,
        )

        async def cleanup():
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=10)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            if process.stdin is not None:
                process.stdin.close()

        self.addAsyncCleanup(cleanup)
        line = await asyncio.wait_for(process.stdout.readline(), timeout=15)
        self.assertTrue(line, "The dashboard must publish readiness before waiting.")
        return process, line.decode("utf-8")

    async def finish(self, process):
        await asyncio.wait_for(process.wait(), timeout=10)
        output = await asyncio.wait_for(process.stdout.read(), timeout=3)
        errors = await asyncio.wait_for(process.stderr.read(), timeout=3)
        return output.decode("utf-8"), errors.decode("utf-8")

    def records(self):
        return list((self.repo / dashboard.SESSION_DIRECTORY).glob("*.json"))

    def request(self, url, path="/api/identity", *, body=None, authenticated=True):
        parsed = urlsplit(url)
        headers = {}
        if authenticated:
            headers["Authorization"] = "Bearer " + parsed.fragment.removeprefix("token=")
        if body is not None:
            body = json.dumps(body)
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        try:
            connection.request("GET" if body is None else "POST", path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def assert_stopped(self, url):
        parsed = urlsplit(url)
        with self.assertRaises(OSError):
            with socket.create_connection((parsed.hostname, parsed.port), timeout=0.2):
                pass

    async def test_parent_eof_stops_owned_listeners_and_preserves_real_run_evidence(self):
        process, line = await self.launch()
        details = json.loads(line)
        self.assertEqual(set(details), {"schemaVersion", "instanceId", "repo", "run", "state", "observedAt",
                                        "localUrl", "lanUrls", "qrUrl", "text"})
        self.assertEqual(details["schemaVersion"], "1.0")
        self.assertEqual(details["state"], "live")
        self.assertEqual(details["repo"], str(self.repo))
        self.assertIsNone(details["run"])
        self.assertFalse(list(self.repo.rglob("run.json")))
        self.assertEqual(self.request(details["localUrl"]), (200, {"instanceId": details["instanceId"], "repo": str(self.repo)}))
        self.assertEqual(self.request(details["localUrl"], authenticated=False)[0], 401)
        self.assertEqual(self.request(details["localUrl"], "/api/session")[1]["runs"], [])
        record, = self.records()
        self.assertEqual(record.name, details["instanceId"] + ".json")
        cached = json.loads(record.read_text(encoding="utf-8"))
        self.assertEqual(cached["localUrl"], details["localUrl"])
        self.assertEqual(cached["text"].splitlines()[0], "[ok] Dashboard live → " + details["localUrl"])
        self.assertEqual(details["text"].splitlines()[0],
                         "[ok] Dashboard live → " + details["localUrl"] + " (/ui-design-dashboard stop to stop)")
        self.assertEqual(decode_terminal_qr(details["text"].split("\n\n", 1)[1]), details["qrUrl"])
        self.assertEqual(dashboard.discover(self.repo, session=details["instanceId"])["instanceId"], details["instanceId"])
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
        root = Path(studio().init_run(self.repo, theme_id="foreground-regression")["run"])
        relative = root.relative_to(self.repo).as_posix()
        evidence = root / "foreground-evidence.txt"
        evidence.write_bytes(b"Keep this real run evidence.\n")
        run_before = (root / "run.json").read_bytes()
        code, opened = self.request(details["localUrl"], "/api/open", body={"run": relative})
        self.assertEqual(code, 200)
        self.assertEqual(opened["run"], relative)
        self.assertEqual(self.request(opened["localUrl"])[0], 200)
        process.stdin.close()
        output, errors = await self.finish(process)
        self.assertEqual(process.returncode, 0, errors)
        self.assertEqual(output, "")
        self.assertEqual(errors, "")
        self.assertEqual(self.records(), [])
        self.assert_stopped(details["localUrl"])
        self.assert_stopped(opened["localUrl"])
        self.assertEqual((root / "run.json").read_bytes(), run_before)
        self.assertEqual(evidence.read_bytes(), b"Keep this real run evidence.\n")
        self.assertEqual(list(self.repo.rglob("run.json")), [root / "run.json"])

    @unittest.skipIf(os.name == "nt", "POSIX signal delivery is required for this process check.")
    async def test_signals_stop_with_parent_stdin_open_and_standalone_stdin_closed(self):
        for signum, parent_stdio, expected in ((signal.SIGTERM, True, 0), (signal.SIGINT, False, 130)):
            with self.subTest(signal=signum, parent_stdio=parent_stdio):
                process, line = await self.launch(parent_stdio=parent_stdio)
                details = json.loads(line)
                suffix = " (/ui-design-dashboard stop to stop)" if parent_stdio else " (Ctrl-C to stop)"
                self.assertEqual(details["text"].splitlines()[0], "[ok] Dashboard live → " + details["localUrl"] + suffix)
                self.assertEqual(self.request(details["localUrl"])[0], 200)
                process.send_signal(signum)
                output, errors = await self.finish(process)
                self.assertEqual(process.returncode, expected, errors)
                self.assertEqual(output, "")
                self.assertEqual(errors, "")
                self.assertEqual(self.records(), [])
                self.assert_stopped(details["localUrl"])
                self.assertFalse(list(self.repo.rglob("run.json")))

    @unittest.skipIf(os.name == "nt", "POSIX signal delivery is required for this process check.")
    async def test_human_foreground_prints_real_labels_and_independently_decodable_qr(self):
        process, first_line = await self.launch(parent_stdio=False, json_output=False, host="0.0.0.0")
        record, = self.records()
        details = json.loads(record.read_text(encoding="utf-8"))
        self.assertEqual(first_line.rstrip("\n"), "[ok] Dashboard live → " + details["localUrl"] + " (Ctrl-C to stop)")
        self.assertEqual(self.request(details["localUrl"])[0], 200)
        process.send_signal(signal.SIGTERM)
        output, errors = await self.finish(process)
        self.assertEqual(process.returncode, 0, errors)
        self.assertEqual(errors, "")
        labels, qr = (first_line + output).split("\n\n", 1)
        lan_lines = ["[lan] " + value for value in details["lanUrls"]] or ["[lan] unavailable"]
        self.assertEqual(labels.splitlines(), [first_line.rstrip("\n"), *lan_lines])
        self.assertNotIn('"schemaVersion"', labels)
        self.assertEqual(decode_terminal_qr(qr), details["qrUrl"])
        self.assertEqual(self.records(), [])
        self.assertFalse(list(self.repo.rglob("run.json")))

    async def test_occupied_port_fails_without_hanging_on_parent_stdin_or_publishing_success(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            process, line = await self.launch("--dashboard-port", str(listener.getsockname()[1]))
            output, errors = await self.finish(process)
            self.assertEqual(process.returncode, 1)
            self.assertEqual(json.loads(line)["status"], "FAIL")
            self.assertNotIn("[ok]", line)
            self.assertEqual(output, "")
            self.assertEqual(errors, "")
            self.assertGreater(listener.fileno(), -1)
        self.assertEqual(self.records(), [])
        self.assertFalse(list(self.repo.rglob("run.json")))

    async def test_top_level_help_exposes_dashboard_and_preserves_engine_commands(self):
        result = subprocess.run([*self.command, "--help"], capture_output=True, text=True,
                                cwd=self.repo, env=self.environment, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("dashboard-serve", "dashboard-info", "init-run", "doctor", "design-serve"):
            self.assertIn(command, result.stdout)
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.records(), [])


if __name__ == "__main__":
    unittest.main()
