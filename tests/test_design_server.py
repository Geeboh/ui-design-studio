"""Synthetic, isolated behavior tests. These are not application review evidence."""
import argparse
import base64
import contextlib
import hashlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
from urllib.parse import urlsplit

from test_studio import SCRIPT, fixture_run, fixture_theme, studio, write_json


spec = importlib.util.spec_from_file_location("design_server_tests_backend", SCRIPT.with_name("design_server.py"))
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aT9sAAAAASUVORK5CYII=")


class DesignServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        self.theme = fixture_theme(self.repo)
        self.root = Path(studio.init_run(self.repo, theme_id="fixture")["run"])
        self.servers = []

    def tearDown(self):
        for server in reversed(self.servers):
            server.close()
        self.temporary.cleanup()

    def start(self, root=None, **kwargs):
        kwargs.setdefault("interval", 60)
        server = backend.DesignServer(studio, root or self.root, **kwargs).start()
        self.servers.append(server)
        return server

    def request(self, server, path="/api/snapshot", method="GET", body=None, headers=None, authenticated=True, local=False, connect_host="127.0.0.1"):
        headers = dict(headers or {})
        if authenticated:
            headers.setdefault("Authorization", "Bearer " + (server.shutdown_token if local else server.token))
        if isinstance(body, dict):
            body = json.dumps(body)
            headers.setdefault("Content-Type", "application/json")
        connection = http.client.HTTPConnection(connect_host, server.local.server_port if local else server.http.server_port, timeout=3)
        try:
            connection.request(method, path if path.startswith("/") else "/" + path, body, headers)
            response = connection.getresponse()
            content = response.read()
            response_headers = dict(response.getheaders())
            if response.getheader("Content-Type", "").startswith("application/json"):
                content = json.loads(content)
            return response.status, response_headers, content
        finally:
            connection.close()

    def local_lan_address(self):
        try:
            import psutil
        except ImportError:
            try:
                inventory = backend.socket.getaddrinfo(backend.socket.gethostname(), 0, backend.socket.AF_INET, backend.socket.SOCK_STREAM)
            except OSError as exc:
                self.skipTest("No discoverable local IPv4 LAN interface: " + str(exc))
            addresses = {backend.ipaddress.IPv4Address(item[4][0]) for item in inventory}
        else:
            stats = psutil.net_if_stats()
            addresses = {backend.ipaddress.IPv4Address(item.address)
                         for name, entries in psutil.net_if_addrs().items() if name in stats and stats[name].isup
                         for item in entries if item.family == backend.socket.AF_INET}
        usable = sorted((value for value in addresses if not (value.is_loopback or value.is_unspecified
                        or value.is_multicast or value.is_link_local)), key=int)
        if not usable:
            self.skipTest("No discoverable local IPv4 LAN interface")
        return str(usable[0])

    def plan(self, request_id="plan-choice", files=None, choices=None):
        (self.root / "plan.html").write_text("<h1>Synthetic concept board</h1>", encoding="utf-8")
        return backend.publish_request(studio, self.root, request_id, "plan", "Select a synthetic concept", "Review the fixture concept, not a real application.", files or ["plan.html"], choices)["request"]

    def payload(self, request, option_id="approve", outcome="approved"):
        return {"id": request["id"], "inputsDigest": request["inputsDigest"], "optionId": option_id,
                "outcome": outcome, "rationale": "Synthetic user review of these exact fixture bytes."}

    def stale_owner(self, root=None, port=1, instance_id="crashed-fixture"):
        root = root or self.root
        temporary = Path(tempfile.mkdtemp(prefix="ui-design-server-"))
        self.addCleanup(backend.shutil.rmtree, temporary, ignore_errors=True)
        locator = {"schemaVersion": "1.0", "instanceId": instance_id, "run": str(root), "pid": os.getpid(),
                   "tempDirectory": str(temporary), "localShutdown": {"url": f"http://127.0.0.1:{port}/api/shutdown", "token": "old-fixture-token"}}
        backend.private_json(studio, temporary / ".design-owner.json",
                             {"instanceId": instance_id, "run": str(root), "shutdownTokenDigest": hashlib.sha256(b"old-fixture-token").hexdigest()})
        write_json(root / ".design-server.json", locator)
        return locator, temporary

    def test_lazy_sibling_loading_preserves_importlib_callers(self):
        specification = importlib.util.spec_from_file_location("isolated_studio_without_sys_modules", SCRIPT)
        isolated = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(isolated)
        self.assertFalse(hasattr(isolated._design_backend, "module"))
        parsed = isolated.parser().parse_args(["status", str(self.root)])
        self.assertEqual(parsed.command, "status")
        self.assertTrue(hasattr(isolated._design_backend, "module"))

    def test_lan_snapshot_requires_bearer_and_url_has_actual_port(self):
        server = self.start(host="0.0.0.0", public_url="http://192.0.2.25")
        self.assertEqual(urlsplit(server.url).port, server.http.server_port)
        self.assertEqual(urlsplit(server.url).fragment, "token=" + server.token)
        code, headers, content = self.request(server, authenticated=False)
        self.assertEqual(code, 401)
        self.assertNotIn(server.token, json.dumps(content))
        code, headers, content = self.request(server, headers={"Authorization": "Bearer wrong"})
        self.assertEqual(code, 401)
        code, headers, content = self.request(server)
        self.assertEqual(code, 200)
        self.assertEqual(content["server"]["url"], server.url)
        self.assertFalse(any(gate["status"] == "passed" for gate in content["gates"]))
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_lan_keyword_preserves_positional_constructor_and_coherent_metadata(self):
        server = backend.DesignServer(studio, self.root, "0.0.0.0", 0, None, 60, self.repo,
                                      lan_addresses=("192.0.2.25", "192.0.2.10", "192.0.2.25")).start()
        self.servers.append(server)
        local_url = f"http://127.0.0.1:{server.http.server_port}/#token={server.token}"
        lan_urls = [f"http://{value}:{server.http.server_port}/#token={server.token}" for value in ("192.0.2.25", "192.0.2.10")]
        self.assertEqual(server.local_url, local_url)
        self.assertEqual(server.lan_urls, lan_urls)
        self.assertEqual(server.url, lan_urls[0])
        self.assertEqual(server.base_url, lan_urls[0].split("#")[0])
        locator = studio.read_json(self.root / ".design-server.json")
        cached = studio.read_json(self.root / ".design-status.json")
        snapshot = self.request(server)[2]
        status = backend.command(studio, argparse.Namespace(command="status", run=str(self.root), watch=False, interval=1))
        expected = {"url": lan_urls[0], "localUrl": local_url, "lanUrls": lan_urls, "startedAt": locator["startedAt"]}
        for observed in (cached["server"], snapshot["server"], status["server"]):
            self.assertEqual(observed, expected)
        self.assertEqual({key: locator[key] for key in expected}, expected)
        returned = server.lan_urls
        returned.clear()
        self.assertEqual(server.lan_urls, lan_urls)

    def test_loopback_binding_does_not_advertise_unreachable_lan_aliases(self):
        server = self.start(lan_addresses=("192.0.2.25",))
        self.assertEqual(server.local_url, server.url)
        self.assertEqual(server.lan_urls, [])
        self.assertEqual(self.request(server, headers={"Host": f"192.0.2.25:{server.http.server_port}"})[0], 403)
        server.set_lan_addresses(("192.0.2.26",))
        self.assertEqual(self.request(server)[2]["server"]["lanUrls"], [])

    def test_lan_aliases_require_safe_canonical_ipv4_addresses(self):
        for addresses in ("192.0.2.25", (None,), ("invalid",), ("127.0.0.1",), ("0.0.0.0",),
                          ("224.0.0.1",), ("169.254.1.2",), ("::1",), ("192.000.2.25",)):
            with self.subTest(addresses=addresses):
                with self.assertRaisesRegex(studio.StudioError, "LAN addresses"):
                    backend.DesignServer(studio, self.root, lan_addresses=addresses)
        self.assertFalse((self.root / ".design-server.json").exists())
        server = self.start(host="0.0.0.0", lan_addresses=("192.0.2.25",))
        before = studio.read_json(self.root / ".design-server.json")
        with self.assertRaisesRegex(studio.StudioError, "LAN addresses"):
            server.set_lan_addresses(("192.0.2.26", "https://attacker.invalid"))
        self.assertEqual(studio.read_json(self.root / ".design-server.json"), before)
        self.assertEqual(server.lan_urls, before["lanUrls"])

    def test_public_and_control_identity_use_dashboard_token_without_shutdown_disclosure(self):
        server = self.start()
        expected = {"instanceId": server.instance_id, "run": str(self.root.resolve())}
        locator = studio.read_json(self.root / ".design-server.json")
        self.assertEqual(locator["probeUrl"], f"http://127.0.0.1:{server.local.server_port}/api/identity")
        self.assertEqual(urlsplit(locator["probeUrl"]).fragment, "")
        if os.name != "nt":
            self.assertEqual((self.root / ".design-server.json").stat().st_mode & 0o777, 0o600)
        for local in (False, True):
            with self.subTest(control=local):
                self.assertEqual(self.request(server, "/api/identity", authenticated=False, local=local)[0], 401)
                self.assertEqual(self.request(server, "/api/identity", headers={"Authorization": "Bearer wrong"}, local=local)[0], 401)
                self.assertEqual(self.request(server, "/api/identity", headers={"Authorization": "Bearer " + server.shutdown_token}, local=local)[0], 401)
                code, headers, content = self.request(server, "/api/identity", headers={"Authorization": "Bearer " + server.token}, local=local)
                self.assertEqual(code, 200)
                self.assertEqual(content, expected)
                self.assertEqual(headers["Cache-Control"], "no-store")
                self.assertNotIn(server.shutdown_token, json.dumps(content))
        self.assertNotIn(server.shutdown_token, json.dumps(self.request(server)[2]))
        for path in ("/", "/api/snapshot", "/dashboard.js", "/preview/anything"):
            self.assertEqual(self.request(server, path, local=True)[0], 404)

    def test_unadvertised_hosts_and_duplicate_host_headers_are_rejected(self):
        request = self.plan()
        server = self.start()
        for host in ("", "attacker.invalid", f"0.0.0.0:{server.http.server_port}",
                     f"127.0.0.1:{server.local.server_port}", f"127.0.0.1:{server.http.server_port}@attacker.invalid"):
            with self.subTest(host=host):
                for path in ("/", "/api/identity", "/api/snapshot", "/preview/anything"):
                    self.assertEqual(self.request(server, path, headers={"Host": host})[0], 403)
                self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request), {"Host": host})[0], 403)
        for values in ((), (f"127.0.0.1:{server.http.server_port}", "attacker.invalid")):
            connection = http.client.HTTPConnection("127.0.0.1", server.http.server_port, timeout=3)
            try:
                connection.putrequest("GET", "/api/identity", skip_host=True)
                for value in values:
                    connection.putheader("Host", value)
                connection.putheader("Authorization", "Bearer " + server.token)
                connection.endheaders()
                response = connection.getresponse()
                self.assertEqual(response.status, 403)
                response.read()
            finally:
                connection.close()
        self.assertEqual(studio.read_json(self.root / "decisions.json")["decisions"], [])

    def test_lan_removal_replaces_urls_hosts_and_approval_origins_together(self):
        request = self.plan()
        server = self.start(host="0.0.0.0", lan_addresses=("192.0.2.25", "192.0.2.26"))
        previous = studio.read_json(self.root / ".design-server.json")
        old_origin = f"http://192.0.2.25:{server.http.server_port}"
        new_origin = f"http://192.0.2.26:{server.http.server_port}"
        server.set_lan_addresses(("192.0.2.26",))
        locator = studio.read_json(self.root / ".design-server.json")
        snapshot = self.request(server)[2]
        self.assertEqual(server.url, new_origin + "/#token=" + server.token)
        self.assertEqual(server.lan_urls, [server.url])
        for key in ("url", "localUrl", "lanUrls"):
            self.assertEqual(locator[key], snapshot["server"][key])
            self.assertEqual(locator[key], studio.read_json(self.root / ".design-status.json")["server"][key])
        self.assertEqual(locator["localShutdown"], previous["localShutdown"])
        self.assertEqual(locator["probeUrl"], previous["probeUrl"])
        self.assertEqual(self.request(server, "/api/identity", headers={"Host": urlsplit(previous["lanUrls"][0]).netloc})[0], 403)
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request), {"Origin": old_origin})[0], 403)
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request),
                                      {"Origin": new_origin, "Host": urlsplit(server.url).netloc})[0], 200)
        server.set_lan_addresses(())
        self.assertEqual(server.url, server.local_url)
        self.assertEqual(server.lan_urls, [])
        self.assertEqual(self.request(server, headers={"Host": urlsplit(locator["lanUrls"][0]).netloc})[0], 403)
        second = self.plan("loopback-after-removal")
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(second), {"Origin": new_origin})[0], 403)
        local = urlsplit(server.local_url)
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(second),
                                      {"Origin": f"{local.scheme}://{local.netloc}"})[0], 200)
        server.close()
        server.set_lan_addresses(("192.0.2.27",))
        self.assertFalse((self.root / ".design-server.json").exists())
        self.assertFalse((self.root / ".design-status.json").exists())

    def test_alias_update_blocks_readers_until_locator_and_snapshot_are_published(self):
        server = self.start(host="0.0.0.0", lan_addresses=("192.0.2.25",))
        entered, released, reading, completed = (threading.Event() for unused in range(4))
        self.addCleanup(released.set)
        write = backend.private_json
        failures, observed = [], []
        def delayed_write(engine, path, value):
            if path.name == ".design-server.json":
                entered.set()
                if not released.wait(5):
                    raise RuntimeError("Synthetic alias publication barrier was not released")
            write(engine, path, value)
        def update():
            try:
                server.set_lan_addresses(("192.0.2.26",))
            except BaseException as exc:
                failures.append(exc)
        def read():
            reading.set()
            try:
                observed.append(self.request(server))
            except BaseException as exc:
                failures.append(exc)
            finally:
                completed.set()
        with mock.patch.object(backend, "private_json", side_effect=delayed_write):
            writer = threading.Thread(target=update)
            writer.start()
            self.assertTrue(entered.wait(3))
            reader = threading.Thread(target=read)
            reader.start()
            self.assertTrue(reading.wait(3))
            self.assertFalse(completed.wait(0.1))
            released.set()
            writer.join(timeout=5)
            reader.join(timeout=5)
        self.assertFalse(writer.is_alive())
        self.assertFalse(reader.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(observed[0][0], 200)
        locator = studio.read_json(self.root / ".design-server.json")
        for key in ("url", "localUrl", "lanUrls"):
            self.assertEqual(observed[0][2]["server"][key], locator[key])

    def test_specific_lan_binding_never_claims_a_loopback_public_listener(self):
        address = self.local_lan_address()
        server = self.start(host=address, lan_addresses=(address, "192.0.2.25"))
        self.assertIsNone(server.local_url)
        self.assertEqual(server.lan_urls, [server.url])
        self.assertEqual(urlsplit(server.url).hostname, address)
        self.assertEqual(self.request(server, "/api/identity", connect_host=address)[2],
                         {"instanceId": server.instance_id, "run": str(self.root)})
        self.assertIsNone(studio.read_json(self.root / ".design-server.json")["localUrl"])

    def test_public_urls_keep_the_actual_port_and_reject_terminal_controls(self):
        self.assertEqual(backend.public_base("0.0.0.0", 43210, "http://192.0.2.25:0"), "http://192.0.2.25:43210/")
        self.assertEqual(backend.public_base("::", 43210, None), "http://[::1]:43210/")
        with self.assertRaisesRegex(ValueError, "terminal controls"):
            backend.public_base("127.0.0.1", 43210, "http://example.invalid/\x1b[2J")

    def test_default_proxy_ports_match_normalized_hosts_and_origins(self):
        for case, (scheme, default_port, explicit) in enumerate((("http", 80, True), ("https", 443, True), ("https", 443, False))):
            suffix = ":" + str(default_port) if explicit else ""
            advertised = f"{scheme}://studio.example.invalid{suffix}/design/view/"
            server = self.start(public_url=advertised)
            self.assertEqual(server.base_url, advertised)
            for index, (host, origin) in enumerate((
                    ("studio.example.invalid", f"{scheme}://studio.example.invalid"),
                    (f"STUDIO.EXAMPLE.INVALID:{default_port}", f"{scheme}://studio.example.invalid"),
                    ("studio.example.invalid", f"{scheme}://STUDIO.EXAMPLE.INVALID:{default_port}"),
                    (f"studio.example.invalid:{default_port}", f"{scheme}://studio.example.invalid:{default_port}"))):
                with self.subTest(scheme=scheme, explicit=explicit, host=host, origin=origin):
                    request = self.plan(f"default-port-{case}-{index}")
                    identity = self.request(server, "/design/view/api/identity", headers={"Host": host})
                    self.assertEqual(identity[0], 200)
                    self.assertEqual(identity[2], {"instanceId": server.instance_id, "run": str(self.root)})
                    snapshot = self.request(server)[2]
                    art = next(item for item in snapshot["artworks"] if item["path"] == "plan.html")
                    code, headers, content = self.request(server, "/design/view/" + art["url"],
                                                          headers={"Host": host}, authenticated=False)
                    self.assertEqual(code, 200)
                    self.assertIn(advertised + "preview/", headers["Content-Security-Policy"])
                    self.assertIn(b"Synthetic concept board", content)
                    self.assertEqual(self.request(server, "/design/view/api/approval", "POST", self.payload(request),
                                                  {"Host": host, "Origin": origin})[0], 200)
            self.assertEqual(self.request(server, "/api/identity",
                                          headers={"Host": f"studio.example.invalid:{default_port + 1}"})[0], 403)
            self.assertEqual(self.request(server, "/api/identity",
                                          headers={"Host": "studio.example.invalid:invalid"})[0], 403)
            for forbidden in (f"{scheme}://studio.example.invalid:{default_port + 1}",
                              f"{scheme}://studio.example.invalid:{default_port}/",
                              f"{scheme}://studio.example.invalid:{default_port}?",
                              f"{scheme}://studio.example.invalid:{default_port}#",
                              f"{scheme}://user@studio.example.invalid:{default_port}"):
                self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request),
                                              {"Host": "studio.example.invalid", "Origin": forbidden})[0], 403)
            server.close()
        self.assertEqual(backend.http_origin("http://[::1]:80"), "http://[::1]")
        self.assertEqual(backend.http_origin("https://[::1]:443"), "https://[::1]")
        self.assertEqual(backend.http_origin("https://[::1]:444"), "https://[::1]:444")

    def test_tokens_in_queries_and_unknown_files_are_not_data_routes(self):
        server = self.start()
        self.assertEqual(self.request(server, "/api/snapshot?token=" + server.token, authenticated=False)[0], 400)
        self.assertEqual(self.request(server, "/run.json")[0], 404)
        self.assertEqual(self.request(server, "/api/shutdown", "POST", {"instanceId": server.instance_id})[0], 404)

    def test_approval_csrf_origin_and_content_type_are_rejected(self):
        request = self.plan()
        server = self.start()
        for origin in ("https://attacker.invalid", "null"):
            self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request), {"Origin": origin})[0], 403)
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request), {"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request), {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(studio.read_json(self.root / "decisions.json")["decisions"], [])

    def test_authenticated_same_origin_approval_records_real_user_decision(self):
        request = self.plan()
        server = self.start()
        parsed = urlsplit(server.base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        code, unused, result = self.request(server, "/api/approval", "POST", self.payload(request), {"Origin": origin})
        self.assertEqual(code, 200)
        decision = studio.read_json(self.root / "decisions.json")["decisions"][-1]
        self.assertEqual(decision["actor"], "user")
        self.assertEqual(decision["outcome"], "approved")
        self.assertEqual(decision["optionId"], "approve")
        self.assertEqual(decision["inputsDigest"], studio.file_digest(self.root, decision["inputs"]))
        self.assertIn("project-context.md", decision["inputs"])
        self.assertTrue(decision["recordedAt"])
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request))[0], 409)
        snapshot = self.request(server)[2]
        self.assertEqual(snapshot["approvals"][0]["status"], "approved")
        self.assertEqual(snapshot["decisions"][-1]["actor"], "user")
        self.assertNotEqual(next(g for g in snapshot["gates"] if g["id"] == "finalize")["status"], "passed")

    def test_html_css_image_and_font_changes_make_approval_stale(self):
        (self.root / "board.css").write_text('@import "palette.css"; @font-face{font-family:test;src:url(font.woff2)}', encoding="utf-8")
        (self.root / "palette.css").write_text("body{color:#123456}", encoding="utf-8")
        (self.root / "font.woff2").write_bytes(b"synthetic font fixture")
        (self.root / "concept.png").write_bytes(PNG)
        (self.root / "board.html").write_text('<link rel="stylesheet" href="board.css"><img src="concept.png">', encoding="utf-8")
        request = backend.publish_request(studio, self.root, "dependency-choice", "plan", "Dependency review", "Synthetic dependent concept board.", ["board.html"])["request"]
        self.assertTrue({"board.html", "board.css", "palette.css", "font.woff2", "concept.png"}.issubset(request["inputs"]))
        server = self.start()
        (self.root / "palette.css").write_text("body{color:#654321}", encoding="utf-8")
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request))[0], 409)
        self.assertEqual(studio.read_json(self.root / "decisions.json")["decisions"], [])
        self.assertEqual(self.request(server)[2]["approvals"][0]["status"], "stale")
        (self.root / "palette.css").unlink()
        self.assertEqual(self.request(server)[2]["approvals"][0]["status"], "stale")

    def test_decision_and_context_changes_conflict_without_writing(self):
        request = self.plan()
        decisions = studio.read_json(self.root / "decisions.json")
        decisions["decisions"].append({"stage": "plan", "actor": "user", "outcome": "pending", "rationale": "Another review is underway."})
        write_json(self.root / "decisions.json", decisions)
        with self.assertRaises(backend.ApprovalConflict):
            backend.approve(studio, self.root, self.payload(request))
        request = self.plan("new-plan-choice")
        (self.root / "project-context.md").write_text("Changed project context fixture", encoding="utf-8")
        with self.assertRaises(backend.ApprovalConflict):
            backend.approve(studio, self.root, self.payload(request))
        self.assertEqual(len(studio.read_json(self.root / "decisions.json")["decisions"]), 1)

    def test_request_ids_are_immutable_but_identical_publication_is_idempotent(self):
        request = self.plan()
        same = self.plan()
        self.assertEqual(same, request)
        with self.assertRaisesRegex(studio.StudioError, "immutable"):
            backend.publish_request(studio, self.root, request["id"], "plan", "Changed review meaning", request["context"], ["plan.html"])

    def test_design_request_includes_current_approved_plan_dependencies(self):
        with self.assertRaisesRegex(studio.StudioError, "approved Plan"):
            backend.publish_request(studio, self.root, "design-before-plan", "design", "Design", "Synthetic design review.", ["project-context.md"])
        request = self.plan()
        backend.approve(studio, self.root, self.payload(request))
        (self.root / "mockup.html").write_text("<main>Synthetic page</main>", encoding="utf-8")
        design = backend.publish_request(studio, self.root, "design-choice", "design", "Design", "Synthetic design review.", ["mockup.html"])["request"]
        self.assertTrue(set(request["inputs"]).issubset(design["inputs"]))
        (self.root / "plan.html").write_text("Changed upstream concept fixture", encoding="utf-8")
        with self.assertRaises(backend.ApprovalConflict):
            backend.approve(studio, self.root, self.payload(design))

    def test_a_new_plan_choice_supersedes_design_and_finalize_without_byte_changes(self):
        root = fixture_run(self.repo, self.theme)
        for name, title in (("concept-a.html", "Concept A"), ("concept-b.html", "Concept B")):
            (root / name).write_text(f"<h1>{title}</h1>", encoding="utf-8")
        records, unused = backend.ArtworkLibrary(studio, root).discover()
        choices = [{"id": option, "label": label, "artworkIds": [next(item["id"] for item in records if item["path"] == path)]}
                   for option, label, path in (("concept-a", "Choose concept A", "concept-a.html"), ("concept-b", "Choose concept B", "concept-b.html"))]
        choices.append({"id": "request-changes", "label": "Request changes", "artworkIds": []})
        first = backend.publish_request(studio, root, "plan-a", "plan", "Select a concept", "Synthetic concept comparison.", ["concept-a.html", "concept-b.html"], choices)["request"]
        backend.approve(studio, root, self.payload(first, "concept-a"))
        design = backend.publish_request(studio, root, "design-a", "design", "Review concept A design", "Synthetic completed design.", ["mockup.html"])["request"]
        backend.approve(studio, root, self.payload(design))
        review = studio.check_run(root)
        decisions = studio.read_json(root / "decisions.json")
        decisions["decisions"].append({"stage": "finalize", "actor": "director", "outcome": "approved",
                                      "rationale": "Synthetic independent final review.", "inputsDigest": review["reviewDigest"]})
        write_json(root / "decisions.json", decisions)
        self.assertEqual(studio.check_run(root)["status"], "PASS")
        self.assertEqual(next(g for g in backend.DesignState(studio, root).snapshot()["gates"] if g["id"] == "design")["status"], "passed")
        unchanged = {name: studio.sha_file(root / name) for name in ("concept-a.html", "concept-b.html", "mockup.html")}
        second = backend.publish_request(studio, root, "plan-b", "plan", "Select a different concept", "The same rendered alternatives remain current.", ["concept-a.html", "concept-b.html"], choices)["request"]
        backend.approve(studio, root, self.payload(second, "concept-b"))
        history, latest = backend.latest_decisions(studio, root)
        self.assertEqual(latest["plan"]["optionId"], "concept-b")
        self.assertEqual(latest["design"]["outcome"], "superseded")
        self.assertEqual(latest["finalize"]["outcome"], "superseded")
        self.assertTrue(any(item.get("requestId") == "design-a" and item["outcome"] == "approved" for item in history["decisions"]))
        self.assertEqual(unchanged, {name: studio.sha_file(root / name) for name in unchanged})
        self.assertEqual(studio.check_run(root)["status"], "BLOCKED")
        self.assertNotEqual(next(g for g in backend.DesignState(studio, root).snapshot()["gates"] if g["id"] == "design")["status"], "passed")

    def test_choices_must_own_current_art_and_named_choice_is_a_real_approval(self):
        self.plan("seed")
        records, unused = backend.ArtworkLibrary(studio, self.root).discover()
        art_id = next(item["id"] for item in records if item["path"] == "plan.html")
        choices = [{"id": "concept-a", "label": "Choose rendered concept A", "artworkIds": [art_id]},
                   {"id": "request-changes", "label": "Request a reconciled board", "artworkIds": []}]
        request = self.plan("named-choice", choices=choices)
        result = backend.approve(studio, self.root, self.payload(request, "concept-a"))
        self.assertEqual(result["decision"]["outcome"], "approved")
        self.assertEqual(result["decision"]["optionId"], "concept-a")
        bad = [{"id": "concept-a", "label": "Unreviewed", "artworkIds": ["not-in-this-request"]}, choices[1]]
        with self.assertRaisesRegex(studio.StudioError, "request-owned"):
            self.plan("bad-choice", choices=bad)

    def test_choices_cannot_relabel_a_retained_noncurrent_art_version(self):
        (self.root / "concept.png").write_bytes(PNG)
        prior = backend.publish_artwork(studio, self.root, "concept.png", "The prior synthetic purpose.")["artwork"]
        current = backend.publish_artwork(studio, self.root, "concept.png", "The current synthetic purpose.")["artwork"]
        choices = [{"id": "concept", "label": "Choose this rendered concept", "artworkIds": [prior["id"]]},
                   {"id": "request-changes", "label": "Request changes", "artworkIds": []}]
        with self.assertRaisesRegex(studio.StudioError, "request-owned"):
            backend.publish_request(studio, self.root, "prior-context", "plan", "Concept review", "Review the current concept context.", ["concept.png"], choices)
        choices[0]["artworkIds"] = [current["id"]]
        request = backend.publish_request(studio, self.root, "current-context", "plan", "Concept review", "Review the current concept context.", ["concept.png"], choices)["request"]
        self.assertEqual(request["options"][0]["artworkIds"], [current["id"]])

    def test_request_changes_cannot_grant_an_approval(self):
        request = self.plan()
        with self.assertRaisesRegex(studio.StudioError, "cannot grant"):
            backend.approve(studio, self.root, self.payload(request, "request-changes", "approved"))
        result = backend.approve(studio, self.root, self.payload(request, "request-changes", "rejected"))
        self.assertEqual(result["decision"]["outcome"], "rejected")

    def test_discovery_retains_versions_and_excludes_symlinks_and_runtime(self):
        (self.root / "board.html").write_text("<h1>First synthetic board</h1>", encoding="utf-8")
        for suffix in ("png", "jpg", "jpeg", "gif", "webp", "avif", "svg", "htm", "pdf"):
            content = b'<svg xmlns="http://www.w3.org/2000/svg"/>' if suffix == "svg" else b"<h1>Synthetic HTML fixture</h1>" if suffix == "htm" else PNG
            (self.root / ("fixture." + suffix)).write_bytes(content)
        (self.root / ".cache").mkdir()
        (self.root / ".cache/hidden.png").write_bytes(PNG)
        (self.root / "secret.png").symlink_to(self.theme / "icons.svg")
        library = backend.ArtworkLibrary(studio, self.root)
        first, warnings = library.discover()
        self.assertFalse(warnings)
        self.assertTrue(all(not item["path"].startswith(".cache/") and item["path"] != "secret.png" for item in first))
        old = next(item for item in first if item["path"] == "board.html")
        (self.root / "board.html").write_text("<h1>Second synthetic board</h1>", encoding="utf-8")
        second, unused = library.discover()
        versions = [item for item in second if item["path"] == "board.html"]
        self.assertEqual(len(versions), 2)
        self.assertEqual(library.file(old["version"], "board.html")[1], b"<h1>First synthetic board</h1>")
        (self.root / "board.html").unlink()
        self.assertEqual(len([item for item in library.discover()[0] if item["path"] == "board.html"]), 2)

    def test_explicit_context_is_retained_with_art_version(self):
        (self.root / "concept.png").write_bytes(PNG)
        backend.publish_artwork(studio, self.root, "concept.png", "Compare the fixture palette against the neutral concept.", "Fixture palette")
        record = next(item for item in backend.ArtworkLibrary(studio, self.root).discover()[0] if item["path"] == "concept.png")
        self.assertEqual(record["title"], "Fixture palette")
        self.assertEqual(record["context"], "Compare the fixture palette against the neutral concept.")

    def test_two_publications_between_polls_retain_both_exact_versions(self):
        (self.root / "board.css").write_text("body{color:#123456}", encoding="utf-8")
        (self.root / "board.html").write_text('<link rel="stylesheet" href="board.css"><h1>First board</h1>', encoding="utf-8")
        first = backend.publish_artwork(studio, self.root, "board.html", "Compare this exact synthetic board.")["artwork"]
        (self.root / "board.css").write_text("body{color:#654321}", encoding="utf-8")
        (self.root / "board.html").write_text('<link rel="stylesheet" href="board.css"><h1>Second board</h1>', encoding="utf-8")
        second = backend.publish_artwork(studio, self.root, "board.html", "Compare this exact synthetic board.")["artwork"]
        self.assertNotEqual(first["id"], second["id"])
        self.assertNotEqual(first["version"], second["version"])
        library = backend.ArtworkLibrary(studio, self.root)
        self.assertEqual(len([item for item in library.records() if item["path"] == "board.html"]), 2)
        self.assertEqual([item["id"] for item in library.records() if item["path"] == "board.html"], [first["id"], second["id"]])
        self.assertLess(first["createdAt"], second["createdAt"])
        self.assertIn(b"First board", library.file(first["version"], "board.html")[1])
        self.assertIn(b"Second board", library.file(second["version"], "board.html")[1])
        self.assertEqual(library.file(first["version"], "board.css")[1], b"body{color:#123456}")
        self.assertEqual(library.file(second["version"], "board.css")[1], b"body{color:#654321}")

    def test_reverting_to_prior_bytes_makes_that_retained_version_current(self):
        path = self.root / "board.html"
        path.write_text("<h1>First board</h1>", encoding="utf-8")
        first = backend.publish_artwork(studio, self.root, "board.html", "Compare the synthetic board.")["artwork"]
        path.write_text("<h1>Second board</h1>", encoding="utf-8")
        second = backend.publish_artwork(studio, self.root, "board.html", "Compare the synthetic board.")["artwork"]
        path.write_text("<h1>First board</h1>", encoding="utf-8")
        reverted = backend.publish_artwork(studio, self.root, "board.html", "Compare the synthetic board.")["artwork"]
        self.assertEqual(reverted["id"], first["id"])
        self.assertEqual(reverted["createdAt"], first["createdAt"])
        library = backend.ArtworkLibrary(studio, self.root)
        versions = [item for item in library.records() if item["path"] == "board.html"]
        self.assertEqual([item["id"] for item in versions], [second["id"], first["id"]])
        self.assertIn(b"First board", library.file(first["version"], "board.html")[1])
        self.assertIn(b"Second board", library.file(second["version"], "board.html")[1])
        snapshot = backend.DesignState(studio, self.root, preview_capability="fixture-preview").snapshot()
        self.assertEqual([item for item in snapshot["artworks"] if item["path"] == "board.html"][-1]["id"], first["id"])

    def test_explicit_publication_fails_when_its_dependency_cannot_be_captured(self):
        (self.root / "missing.html").write_text('<img src="missing.png">', encoding="utf-8")
        with self.assertRaisesRegex(studio.StudioError, "missing.png"):
            backend.publish_artwork(studio, self.root, "missing.html", "This incomplete fixture must not get a success receipt.")
        self.assertFalse(any(item["path"] == "missing.html" for item in backend.ArtworkLibrary(studio, self.root).records()))

    def test_missing_preview_dependency_does_not_hide_the_visual_artifact(self):
        (self.root / "incomplete.html").write_text('<img src="not-yet-generated.png"><h1>Fixture</h1>', encoding="utf-8")
        records, warnings = backend.ArtworkLibrary(studio, self.root).discover()
        self.assertTrue(any(item["path"] == "incomplete.html" for item in records))
        self.assertTrue(any("not-yet-generated.png" in warning for warning in warnings))
        with self.assertRaises(studio.StudioError):
            backend.publish_request(studio, self.root, "incomplete-choice", "plan", "Incomplete", "Review incomplete fixture.", ["incomplete.html"])

    def test_preview_is_scoped_scriptless_and_dependency_aware(self):
        (self.root / "photo.png").write_bytes(PNG)
        (self.root / "board.css").write_text('body{background:url(photo.png)} a{background:url(https://attacker.invalid/exfil)}', encoding="utf-8")
        html = '<base href="https://attacker.invalid/"><meta http-equiv="refresh" content="0;url=https://attacker.invalid/"><link rel="stylesheet" href="board.css"><script>window.parent.fetch("api/approval")</script><img src="photo.png" onerror="steal()"><a href="https://attacker.invalid/" target="_top">external</a><iframe src="https://attacker.invalid/"></iframe><form action="api/approval"><button formaction="api/approval">Send</button></form>'
        (self.root / "board.html").write_text(html, encoding="utf-8")
        server = self.start()
        snapshot = self.request(server)[2]
        art = next(item for item in snapshot["artworks"] if item["path"] == "board.html")
        self.assertNotIn(server.token, art["url"])
        self.assertNotEqual(server.token, server.preview_capability)
        code, headers, content = self.request(server, art["url"], authenticated=False)
        self.assertEqual(code, 200)
        text = content.decode()
        for forbidden in ("<script", "window.parent", "onerror", "http-equiv", "attacker.invalid", "<base", "<iframe", "formaction", "action="):
            self.assertNotIn(forbidden, text)
        self.assertIn(server.preview_capability, text)
        self.assertIn("sandbox;", headers["Content-Security-Policy"])
        self.assertIn("script-src 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("allow-same-origin", headers["Content-Security-Policy"])
        css_url = art["url"].rsplit("/", 1)[0] + "/board.css"
        code, unused, css = self.request(server, css_url, authenticated=False)
        self.assertEqual(code, 200)
        self.assertIn(server.preview_capability, css.decode())
        self.assertNotIn("attacker.invalid", css.decode())
        self.assertEqual(self.request(server, art["url"].replace(server.preview_capability, "wrong-capability"), authenticated=False)[0], 404)

    def test_proxy_and_alias_previews_keep_the_validated_origin_and_base_path(self):
        directory = self.root / "mockups"
        for child in ("styles", "fonts", "images"):
            (directory / child).mkdir(parents=True, exist_ok=True)
        (directory / "scene.html").write_text('<link rel="stylesheet" href="styles/scene.css"><img src="images/pixel.png">', encoding="utf-8")
        (directory / "styles/scene.css").write_text('@import "palette.css";@font-face{font-family:fixture;src:url(../fonts/fixture.woff2)}body{background:url(../images/pixel.png)}', encoding="utf-8")
        (directory / "styles/palette.css").write_text("body{color:#123456}", encoding="utf-8")
        (directory / "fonts/fixture.woff2").write_bytes(b"synthetic retained font")
        (directory / "images/pixel.png").write_bytes(PNG)
        server = self.start(host="0.0.0.0", public_url="https://studio.example.invalid/design/view/",
                            lan_addresses=("192.0.2.25",))
        self.assertEqual(server.base_url, "https://studio.example.invalid/design/view/")
        art = next(item for item in self.request(server)[2]["artworks"] if item["path"] == "mockups/scene.html")
        for index, url in enumerate((server.url, server.local_url, *server.lan_urls)):
            parsed = urlsplit(url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            headers = {"Host": parsed.netloc}
            prefix = parsed.path + f"preview/{server.preview_capability}/{art['version']}/"
            with self.subTest(origin=origin):
                identity = self.request(server, parsed.path + "api/identity", headers=headers)
                self.assertEqual(identity[0], 200)
                self.assertEqual(identity[2], {"instanceId": server.instance_id, "run": str(self.root)})
                code, response_headers, html = self.request(server, parsed.path + art["url"], headers=headers, authenticated=False)
                self.assertEqual(code, 200)
                policy = response_headers["Content-Security-Policy"]
                for directive in ("style-src 'unsafe-inline' ", "img-src ", "font-src "):
                    self.assertIn(directive + origin + prefix, policy)
                self.assertIn((prefix + "mockups/styles/scene.css").encode(), html)
                self.assertIn((prefix + "mockups/images/pixel.png").encode(), html)
                code, unused, css = self.request(server, prefix + "mockups/styles/scene.css", headers=headers, authenticated=False)
                self.assertEqual(code, 200)
                self.assertIn((prefix + "mockups/fonts/fixture.woff2").encode(), css)
                self.assertIn((prefix + "mockups/styles/palette.css").encode(), css)
                self.assertEqual(self.request(server, prefix + "mockups/images/pixel.png", headers=headers, authenticated=False)[2], PNG)
                self.assertEqual(self.request(server, prefix + "mockups/fonts/fixture.woff2", headers=headers, authenticated=False)[2], b"synthetic retained font")
                request = self.plan("alias-choice-" + str(index), ["mockups/scene.html"])
                self.assertEqual(self.request(server, parsed.path + "api/approval", "POST", self.payload(request),
                                              {**headers, "Origin": origin})[0], 200)
        stripped = self.request(server, art["url"], headers={"Host": "studio.example.invalid"}, authenticated=False)
        self.assertEqual(stripped[0], 200)
        self.assertIn("https://studio.example.invalid/design/view/preview/", stripped[1]["Content-Security-Policy"])
        for candidate in ("https://unlisted.example.invalid", "http://studio.example.invalid", "https://studio.example.invalid/design/view/"):
            request = self.plan("forbidden-proxy-origin", ["mockups/scene.html"])
            self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request), {"Origin": candidate})[0], 403)

    def test_real_lan_alias_serves_nested_preview_and_accepts_digest_bound_approval(self):
        address = self.local_lan_address()
        directory = self.root / "concept"
        directory.mkdir()
        (directory / "pixel.png").write_bytes(PNG)
        (directory / "board.css").write_text("body{background:url(pixel.png)}", encoding="utf-8")
        (directory / "board.html").write_text('<link rel="stylesheet" href="board.css"><img src="pixel.png">', encoding="utf-8")
        server = self.start(host="0.0.0.0", lan_addresses=(address,))
        for index, host in enumerate(("127.0.0.1", address)):
            with self.subTest(interface=host):
                snapshot = self.request(server, connect_host=host)[2]
                art = next(item for item in snapshot["artworks"] if item["path"] == "concept/board.html")
                code, headers, html = self.request(server, art["url"], authenticated=False, connect_host=host)
                self.assertEqual(code, 200)
                self.assertIn(b"concept/board.css", html)
                source = f"http://{host}:{server.http.server_port}/preview/"
                self.assertIn(source, headers["Content-Security-Policy"])
                prefix = art["url"].rsplit("/", 1)[0] + "/"
                self.assertEqual(self.request(server, prefix + "board.css", authenticated=False, connect_host=host)[0], 200)
                self.assertEqual(self.request(server, prefix + "pixel.png", authenticated=False, connect_host=host)[2], PNG)
                request = self.plan("real-interface-" + str(index), ["concept/board.html"])
                self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request),
                                              {"Origin": f"http://{host}:{server.http.server_port}"}, connect_host=host)[0], 200)
                decision = studio.read_json(self.root / "decisions.json")["decisions"][-1]
                self.assertEqual(decision["actor"], "user")
                self.assertEqual(decision["inputsDigest"], studio.file_digest(self.root, decision["inputs"]))

    def test_inline_svg_cannot_restore_navigation_through_animation(self):
        html = '<svg xmlns="http://www.w3.org/2000/svg"><a href="https://attacker.invalid/"><text>Fixture</text><set attributeName="href" to="/"/><animate attributeName="href" values="/;https://attacker.invalid/"/><animateMotion path="M0 0L1 1"/><animateTransform attributeName="transform" type="rotate" to="360"/></a></svg>'
        (self.root / "animated.html").write_text(html, encoding="utf-8")
        server = self.start()
        art = next(item for item in self.request(server)[2]["artworks"] if item["path"] == "animated.html")
        code, headers, content = self.request(server, art["url"], authenticated=False)
        self.assertEqual(code, 200)
        for forbidden in (b"<set", b"<animate", b"attributeName", b"attributename", b"attacker.invalid", b'href='):
            self.assertNotIn(forbidden, content)
        self.assertIn("sandbox;", headers["Content-Security-Policy"])
        self.assertEqual(server.state.library.file(art["version"], "animated.html")[1], html.encode("utf-8"))

    def test_preview_rejects_traversal_and_nonvisual_files(self):
        server = self.start()
        art = self.request(server)[2]["artworks"][0]
        for path in ("/%2e%2e/run.json", "/preview/" + server.preview_capability + "/" + art["version"] + "/%2e%2e/run.json",
                     art["url"].rsplit("/", 1)[0] + "/run.json"):
            self.assertEqual(self.request(server, path, authenticated=False)[0], 400)
        with self.assertRaises(studio.StudioError):
            server.state.library.file(art["version"], "../run.json")

    def test_svg_scripts_and_external_navigation_are_removed(self):
        (self.root / "active.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" xml:base="https://attacker.invalid/" onload="steal()"><script>steal()</script><foreignObject><iframe src="https://attacker.invalid/"/></foreignObject><a href="#destination"><text>Fixture</text></a><animate attributeName="href" to="https://attacker.invalid/"/></svg>', encoding="utf-8")
        server = self.start()
        art = next(item for item in self.request(server)[2]["artworks"] if item["path"] == "active.svg")
        code, headers, svg = self.request(server, art["url"], authenticated=False)
        self.assertEqual(code, 200)
        for forbidden in (b"steal", b"attacker.invalid", b"foreignObject", b"animate"):
            self.assertNotIn(forbidden, svg)
        self.assertIn("script-src 'none'", headers["Content-Security-Policy"])

    def test_theme_visuals_import_without_exposing_generic_project_files(self):
        (self.repo / "private.png").write_bytes(PNG)
        server = self.start(repo=self.repo)
        snapshot = self.request(server)[2]
        paths = {item["path"] for item in snapshot["artworks"]}
        self.assertIn("theme-artwork/fixture/preview.html", paths)
        self.assertIn("theme-artwork/fixture/icons.svg", paths)
        self.assertNotIn("private.png", paths)
        self.assertEqual((self.root / "theme-artwork/fixture/preview.html").read_bytes(), (self.theme / "preview.html").read_bytes())
        with self.assertRaisesRegex(studio.StudioError, "active theme"):
            backend.publish_artwork(studio, self.root, "private.png", "Not an active theme artifact.", repo=self.repo)

    def test_theme_source_edit_between_polls_conflicts_with_approval(self):
        backend.ArtworkLibrary(studio, self.root).discover()
        request = backend.publish_request(studio, self.root, "theme-choice", "plan", "Theme preview", "Review this exact imported theme preview.", ["theme-artwork/fixture/preview.html"])["request"]
        self.assertIn(".design-theme-sources.json", request["inputs"])
        (self.theme / "preview.html").write_text("<h1>Edited original after review</h1>", encoding="utf-8")
        with self.assertRaises(backend.ApprovalConflict):
            backend.approve(studio, self.root, self.payload(request))
        self.assertIn(b"Edited original", (self.root / "theme-artwork/fixture/preview.html").read_bytes())
        self.assertEqual(studio.read_json(self.root / "decisions.json")["decisions"], [])

    def test_coverage_requires_implementation_and_fresh_qa_bytes(self):
        root = fixture_run(self.repo, self.theme)
        state = backend.DesignState(studio, root)
        snapshot = state.snapshot()
        self.assertEqual(snapshot["coverage"], {"required": 4, "mockups": 4, "verified": 4, "inventoryComplete": True})
        self.assertTrue(all(gate["status"] == "passed" for gate in snapshot["gates"]))
        (root / "visual.md").write_text("Evidence changed since its recorded digest.", encoding="utf-8")
        changed = state.snapshot()
        self.assertEqual(changed["coverage"]["verified"], 0)
        self.assertEqual(changed["statistics"]["passedEvidence"], 5)
        self.assertEqual(next(g for g in changed["gates"] if g["id"] == "produce")["status"], "failed")
        (root / "implementation.md").unlink()
        self.assertEqual(state.snapshot()["coverage"]["verified"], 0)

    def test_sparse_applicability_changes_dashboard_required_count(self):
        root = fixture_run(self.repo, self.theme)
        coverage = studio.read_json(root / "coverage.json")
        surface = coverage["surfaces"][0]
        required = {("ready", "mobile"), ("ready", "desktop"), ("error", "mobile")}
        surface["applicableCases"] = [{"state": state, "viewport": viewport} for state, viewport in sorted(required)]
        surface["excludedCases"] = [{"state": "error", "viewport": "desktop", "reason": "Desktop uses inline recovery."}]
        surface["cases"] = [case for case in surface["cases"] if (case["state"], case["viewport"]) in required]
        write_json(root / "coverage.json", coverage)
        snapshot = backend.DesignState(studio, root).snapshot()
        self.assertEqual(snapshot["coverage"]["required"], 3)
        self.assertEqual(snapshot["coverage"]["verified"], 3)

    def test_status_page_rejects_stale_revision_cursor(self):
        snapshot = backend.DesignState(studio, fixture_run(self.repo, self.theme)).snapshot()
        page = backend.status_page(snapshot, "artworks", 1)
        with self.assertRaisesRegex(ValueError, "stale or invalid"):
            backend.status_page(snapshot, "artworks", 1, "old-revision:0")

    def test_status_page_rejects_malformed_inputs(self):
        snapshot = backend.DesignState(studio, fixture_run(self.repo, self.theme)).snapshot()
        with self.assertRaisesRegex(ValueError, "stale or invalid"):
            backend.status_page(snapshot, "artworks", 1, "malformed")
        with self.assertRaisesRegex(ValueError, "must be artworks or evidence"):
            backend.status_page(snapshot, "decisions", 1)
        with self.assertRaisesRegex(ValueError, "between 1 and 100"):
            backend.status_page(snapshot, "artworks", 0)
        with self.assertRaisesRegex(ValueError, "stale or invalid"):
            backend.status_page(snapshot, "artworks", 1, f"{snapshot['revision']}:999")

    def test_missing_duplicate_cases_do_not_inflate_coverage(self):
        root = fixture_run(self.repo, self.theme)
        coverage = studio.read_json(root / "coverage.json")
        coverage["surfaces"][0]["cases"] = [coverage["surfaces"][0]["cases"][0]] * 2
        write_json(root / "coverage.json", coverage)
        snapshot = backend.DesignState(studio, root).snapshot()
        self.assertEqual(snapshot["coverage"]["required"], 4)
        self.assertEqual(snapshot["coverage"]["mockups"], 0)
        self.assertEqual(snapshot["coverage"]["verified"], 0)
        self.assertFalse(snapshot["coverage"]["inventoryComplete"])

    def test_corrupt_records_fail_closed_in_the_snapshot(self):
        write_json(self.root / "coverage.json", [])
        snapshot = backend.DesignState(studio, self.root).snapshot()
        self.assertEqual(snapshot["coverage"]["verified"], 0)
        self.assertFalse(snapshot["coverage"]["inventoryComplete"])
        self.assertTrue(all(gate["status"] == "failed" for gate in snapshot["gates"]))
        self.assertTrue(snapshot["blockers"])

    def test_publications_and_native_tasks_are_reported_without_invented_liveness(self):
        backend.publish_progress(studio, self.root, "Review the fixture palette", ["Waiting for the human choice"])
        backend.publish_worker(studio, self.root, "palette-worker", "Prepare fixture options", "active", "Generating source artifacts", "fixture/model")
        run_id = studio.read_json(self.root / "run.json")["id"]
        session_id = "director-α"
        write_json(self.root / "progress-pi-tasks-director.json", {"schemaVersion": "1.0", "runId": run_id, "sessionId": session_id})
        filename = hashlib.sha256(session_id.encode("utf-8")).hexdigest() + ".json"
        write_json(self.root / "progress-pi-tasks" / filename, {"version": 1, "runId": run_id, "sessionId": session_id,
            "state": {"tasks": {"real-task": {"title": "Actual emitted task title", "status": "blocked", "progress": 25},
                                "cancelled-task": {"title": "Actual cancelled task", "status": "cancelled", "progress": 0},
                                "review-task": {"title": "Actual review task", "status": "review", "progress": 90}}}})
        snapshot = backend.DesignState(studio, self.root).snapshot()
        self.assertEqual(snapshot["nextAction"], "Review the fixture palette")
        self.assertEqual(snapshot["workers"][0]["id"], "palette-worker")
        self.assertEqual(snapshot["tasks"], [{"id": "real-task", "title": "Actual emitted task title", "status": "blocked", "progress": 25},
                                           {"id": "cancelled-task", "title": "Actual cancelled task", "status": "cancelled", "progress": 0},
                                           {"id": "review-task", "title": "Actual review task", "status": "review", "progress": 90}])
        self.assertEqual(snapshot["statistics"]["workers"], 1)
        self.assertTrue(any("not proof of process liveness" in warning for warning in snapshot["warnings"]))

    def test_native_tasks_require_the_exact_selected_director_and_run(self):
        run_id = studio.read_json(self.root / "run.json")["id"]
        session_id = "selected-director"
        own_file = self.root / "progress-pi-tasks" / (hashlib.sha256(session_id.encode("utf-8")).hexdigest() + ".json")
        foreign_file = self.root / "progress-pi-tasks" / (hashlib.sha256(b"foreign-session").hexdigest() + ".json")
        pointer = {"schemaVersion": "1.0", "runId": run_id, "sessionId": session_id}
        own = {"version": 1, "runId": run_id, "sessionId": session_id,
               "state": {"tasks": {"owned": {"title": "Actual director task", "status": "active"}}}}
        foreign = {"version": 1, "runId": run_id, "sessionId": "foreign-session",
                   "state": {"tasks": {"foreign": {"title": "Unrelated session task", "status": "active"}}}}
        write_json(self.root / "progress-pi-tasks-director.json", pointer)
        write_json(own_file, own)
        write_json(foreign_file, foreign)
        state = backend.DesignState(studio, self.root)
        self.assertEqual([item["id"] for item in state.snapshot()["tasks"]], ["owned"])
        write_json(own_file, foreign)
        mismatch = state.snapshot()
        self.assertEqual(mismatch["tasks"], [])
        self.assertTrue(any("selected director" in warning for warning in mismatch["warnings"]))
        write_json(own_file, {**own, "runId": "another-run"})
        self.assertEqual(state.snapshot()["tasks"], [])
        write_json(own_file, own)
        write_json(self.root / "progress-pi-tasks-director.json", {**pointer, "runId": "another-run"})
        self.assertEqual(state.snapshot()["tasks"], [])
        (self.root / "progress-pi-tasks-director.json").unlink()
        write_json(self.root / "progress-pi-tasks.json", foreign)
        self.assertEqual(state.snapshot()["tasks"], [])
        self.assertEqual(studio.read_json(foreign_file), foreign)

    def test_status_widget_has_full_url_and_history_changes_only_with_records(self):
        server = self.start()
        status = studio.read_json(self.root / ".design-status.json")
        self.assertEqual(status["lines"][-1], server.url)
        self.assertTrue(any("(unknown)" in line or "unknown" in line for line in status["lines"]))
        self.assertIn("Blocked: none", status["lines"])
        self.assertTrue(any("gates (0%)" in line for line in status["lines"]))
        self.assertEqual(status["instanceId"], server.instance_id)
        first = server.state.snapshot()
        second = server.state.snapshot()
        self.assertEqual(first["revision"], second["revision"])
        self.assertEqual(len(first["history"]), len(second["history"]))
        backend.publish_progress(studio, self.root, "A changed observed next action")
        third = server.state.snapshot()
        self.assertNotEqual(second["revision"], third["revision"])
        self.assertEqual(len(third["history"]), len(second["history"]) + 1)

    def test_status_watch_prints_periodically_without_starting_a_server(self):
        args = argparse.Namespace(command="status", run=str(self.root), watch=True, interval=0.1)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), mock.patch.object(backend.time, "sleep", side_effect=[None, KeyboardInterrupt]):
            result = backend.command(studio, args)
        self.assertEqual(result, {"status": "PASS", "watchStopped": True})
        self.assertEqual(stream.getvalue().count("Coverage ["), 2)
        self.assertFalse((self.root / ".design-server.json").exists())

    def test_local_shutdown_rejects_browser_origins_and_public_token(self):
        server = self.start()
        body = {"instanceId": server.instance_id}
        self.assertEqual(self.request(server, "/api/shutdown", "POST", body, {"Authorization": "Bearer " + server.token}, local=True)[0], 401)
        self.assertEqual(self.request(server, "/api/shutdown", "POST", body, {"Origin": "null"}, local=True)[0], 403)
        self.assertFalse(server.stop.is_set())

    def test_status_watch_tracks_alias_replacement_without_old_lan_links(self):
        server = self.start(host="0.0.0.0", lan_addresses=("192.0.2.25",))
        previous = server.url
        outputs = []
        stream = io.StringIO()
        def refresh(unused):
            outputs.append(stream.getvalue())
            stream.seek(0)
            stream.truncate(0)
            if len(outputs) == 1:
                server.set_lan_addresses(("192.0.2.26",))
            else:
                raise KeyboardInterrupt
        args = argparse.Namespace(command="status", run=str(self.root), watch=True, interval=0.1)
        with contextlib.redirect_stdout(stream), mock.patch.object(backend.time, "sleep", side_effect=refresh):
            result = backend.command(studio, args)
        self.assertTrue(result["watchStopped"])
        self.assertEqual(len(outputs), 2)
        self.assertIn(previous, outputs[0])
        self.assertNotIn(previous, outputs[1])
        self.assertIn(server.url, outputs[1])

    def test_public_aliases_cannot_reach_shutdown_and_control_rejects_public_hosts(self):
        server = self.start(host="0.0.0.0", lan_addresses=("192.0.2.25",))
        body = {"instanceId": server.instance_id}
        for url in (server.local_url, *server.lan_urls):
            host = urlsplit(url).netloc
            with self.subTest(host=host):
                self.assertEqual(self.request(server, "/api/shutdown", "POST", body,
                                              {"Host": host, "Authorization": "Bearer " + server.shutdown_token})[0], 404)
                self.assertEqual(self.request(server, "/api/shutdown", "POST", body, {"Host": host}, local=True)[0], 403)
                self.assertEqual(self.request(server, "/api/identity", headers={"Host": host}, local=True)[0], 403)
        self.assertEqual(self.request(server, "/api/approval", "POST", {}, local=True)[0], 404)
        self.assertFalse(server.stop.is_set())
        self.assertEqual(backend.cleanup(studio, self.root)["status"], "PASS")
        self.assertTrue(server.closed.wait(3))

    def test_watch_neutralizes_terminal_controls_without_mutating_records(self):
        malicious = "Review\x1b[2J the fixture\nwith \x9b31mcontrols\r"
        backend.publish_progress(studio, self.root, malicious)
        progress = studio.read_json(self.root / "progress.json")
        progress["tasks"] = [{"id": "unsafe-title", "title": malicious, "status": "active"}]
        write_json(self.root / "progress.json", progress)
        args = argparse.Namespace(command="status", run=str(self.root), watch=True, interval=0.1)
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), mock.patch.object(backend.time, "sleep", side_effect=KeyboardInterrupt):
            backend.command(studio, args)
        output = stream.getvalue()
        self.assertNotIn("\x1b", output)
        self.assertNotIn("\x9b", output)
        self.assertNotIn("\r", output)
        self.assertEqual(studio.read_json(self.root / "progress.json")["nextAction"], malicious)

    def test_cleanup_failure_retains_ownership_for_a_safe_retry(self):
        server = self.start()
        temporary = server.temporary
        with server.close_lock:
            with mock.patch.object(backend.shutil, "rmtree", side_effect=OSError("Synthetic temporary removal failure")):
                with self.assertRaisesRegex(OSError, "Synthetic temporary removal failure"):
                    server.close()
            self.assertFalse(server.closed.is_set())
            self.assertTrue(temporary.exists())
            self.assertEqual(studio.read_json(self.root / ".design-server.json")["instanceId"], server.instance_id)
            result = backend.cleanup(studio, self.root)
            self.assertTrue(result["temporaryRemoved"])
            self.assertFalse(temporary.exists())
            self.assertFalse((self.root / ".design-server.json").exists())
            server.close()
            self.assertTrue(server.closed.is_set())

    def test_owned_cleanup_is_complete_and_idempotent_without_deleting_art(self):
        (self.root / "board.html").write_text("<h1>Durable fixture art</h1>", encoding="utf-8")
        server = self.start()
        temporary = server.temporary
        library = self.root / "artwork-library"
        result = backend.cleanup(studio, self.root)
        self.assertTrue(result["stopped"])
        self.assertTrue(server.closed.wait(3))
        self.assertFalse(temporary.exists())
        self.assertFalse((self.root / ".design-server.json").exists())
        self.assertFalse((self.root / ".design-status.json").exists())
        self.assertTrue(library.exists())
        self.assertTrue((self.root / "board.html").exists())
        self.assertTrue(backend.cleanup(studio, self.root)["alreadyStopped"])

    def test_delayed_watcher_cannot_recreate_or_overwrite_runtime_after_shutdown(self):
        for fail_after_release in (False, True):
            with self.subTest(error_fallback=fail_after_release):
                server = self.start(interval=0.01)
                entered, released = threading.Event(), threading.Event()
                self.addCleanup(released.set)
                publish = server.publish_status
                def delayed_publish():
                    entered.set()
                    if not released.wait(10):
                        raise RuntimeError("Synthetic watcher barrier was not released")
                    if fail_after_release:
                        raise studio.StudioError("Synthetic delayed watcher failure")
                    return publish()
                with mock.patch.object(server, "publish_status", side_effect=delayed_publish):
                    self.assertTrue(entered.wait(5))
                    server.close()
                    self.assertFalse((self.root / ".design-server.json").exists())
                    self.assertFalse((self.root / ".design-status.json").exists())
                    replacement = self.start()
                    released.set()
                    server.threads[-1].join(timeout=5)
                    self.assertFalse(server.threads[-1].is_alive())
                    self.assertEqual(studio.read_json(self.root / ".design-server.json")["instanceId"], replacement.instance_id)
                    self.assertEqual(studio.read_json(self.root / ".design-status.json")["instanceId"], replacement.instance_id)
                    replacement.close()

    def test_second_server_cannot_steal_run_lock_or_remove_owner_locator(self):
        server = self.start()
        contender = backend.DesignServer(studio, self.root)
        self.assertFalse(contender.lock_contended)
        with self.assertRaisesRegex(studio.StudioError, "locked"):
            contender.start()
        self.assertTrue(contender.lock_contended)
        self.assertIsNone(contender.run_lock)
        self.assertTrue(contender.closed.is_set())
        self.assertEqual(studio.read_json(self.root / ".design-server.json")["instanceId"], server.instance_id)
        self.assertEqual(self.request(server)[0], 200)

    def test_bind_and_lock_permission_failures_are_not_reported_as_contention(self):
        with backend.socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen(1)
            failed = backend.DesignServer(studio, self.root, port=occupied.getsockname()[1])
            with self.assertRaises(OSError):
                failed.start()
        self.assertFalse(failed.lock_contended)
        self.assertTrue(failed.closed.is_set())
        self.assertIsNone(failed.run_lock)
        self.assertFalse((self.root / ".design-server.json").exists())
        if failed.temporary:
            self.assertFalse(failed.temporary.exists())
        denied = backend.DesignServer(studio, self.root)
        with mock.patch.object(backend.FileLock, "__enter__", side_effect=studio.StudioError("Cannot lock design records")):
            with self.assertRaisesRegex(studio.StudioError, "Cannot lock design records"):
                denied.start()
        self.assertFalse(denied.lock_contended)
        self.assertTrue(denied.closed.is_set())
        self.assertIsNone(denied.run_lock)
        server = self.start()
        self.assertEqual(self.request(server)[0], 200)

    def test_cleanup_all_only_uses_configured_run_locations(self):
        server = self.start()
        unrelated = self.repo / "unrelated"
        unrelated.mkdir()
        locator = studio.read_json(self.root / ".design-server.json")
        write_json(unrelated / ".design-server.json", locator)
        with mock.patch.dict(os.environ, {"HTTP_PROXY": "http://127.0.0.1:1", "ALL_PROXY": "http://127.0.0.1:1"}):
            result = backend.cleanup_all(studio, self.repo)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["runs"]), 1)
        self.assertTrue((unrelated / ".design-server.json").exists())
        self.assertTrue(server.closed.wait(3))

    def test_cleanup_never_uses_arbitrary_locator_hosts_or_claimed_pid(self):
        locator = {"instanceId": "fixture", "run": str(self.root), "pid": os.getpid(),
                   "localShutdown": {"url": "http://attacker.invalid/api/shutdown", "token": "fixture"}}
        write_json(self.root / ".design-server.json", locator)
        with mock.patch.object(backend.http.client, "HTTPConnection") as connection:
            with self.assertRaisesRegex(studio.StudioError, "loopback"):
                backend.cleanup(studio, self.root)
            connection.assert_not_called()
        self.assertTrue((self.root / ".design-server.json").exists())

    def test_stale_cleanup_requires_a_matching_owned_temporary_marker(self):
        outside = self.repo / "do-not-delete"
        outside.mkdir()
        (outside / "evidence.txt").write_text("Preserve this unrelated fixture.", encoding="utf-8")
        locator = {"instanceId": "stale-fixture", "run": str(self.root), "pid": os.getpid(), "tempDirectory": str(outside),
                   "localShutdown": {"url": "http://127.0.0.1:1/api/shutdown", "token": "fixture"}}
        write_json(self.root / ".design-server.json", locator)
        with self.assertRaisesRegex(studio.StudioError, "unowned"):
            backend.cleanup(studio, self.root)
        self.assertTrue((outside / "evidence.txt").exists())
        self.assertTrue((self.root / ".design-server.json").exists())

    def test_stale_cleanup_removes_only_a_matching_owned_temporary_directory(self):
        temporary = Path(tempfile.mkdtemp(prefix="ui-design-server-"))
        self.addCleanup(backend.shutil.rmtree, temporary, ignore_errors=True)
        locator = {"instanceId": "stale-owned-fixture", "run": str(self.root), "tempDirectory": str(temporary),
                   "localShutdown": {"url": "http://127.0.0.1:1/api/shutdown", "token": "fixture-token"}}
        backend.private_json(studio, temporary / ".design-owner.json",
                             {"instanceId": locator["instanceId"], "run": str(self.root),
                              "shutdownTokenDigest": backend.digest(b"fixture-token")})
        write_json(self.root / ".design-server.json", locator)
        with mock.patch.object(backend.http.client, "HTTPConnection") as connection:
            connection.return_value.request.side_effect = ConnectionRefusedError("Synthetic stale endpoint")
            result = backend.cleanup(studio, self.root)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["temporaryRemoved"])
        self.assertFalse(temporary.exists())
        self.assertFalse((self.root / ".design-server.json").exists())

    def test_an_unreachable_locked_owner_is_not_deleted_or_killed(self):
        server = self.start()
        locator = studio.read_json(self.root / ".design-server.json")
        locator["localShutdown"]["url"] = "http://127.0.0.1:1/api/shutdown"
        write_json(self.root / ".design-server.json", locator)
        with mock.patch.object(backend.http.client, "HTTPConnection") as connection:
            connection.return_value.request.side_effect = ConnectionRefusedError("Synthetic unreachable owner")
            with self.assertRaisesRegex(studio.StudioError, "retains its lock"):
                backend.cleanup(studio, self.root)
        self.assertFalse(server.stop.is_set())
        self.assertTrue((self.root / ".design-server.json").exists())
        self.assertEqual(self.request(server)[0], 200)

    def test_stale_cleanup_does_not_contact_a_reused_unauthorized_port(self):
        other_root = Path(studio.init_run(self.repo, theme_id="fixture")["run"])
        other = self.start(other_root)
        for local, expected_status in ((True, 401), (False, 404)):
            with self.subTest(reused_status=expected_status):
                root = Path(studio.init_run(self.repo, theme_id="fixture")["run"])
                port = other.local.server_port if local else other.http.server_port
                locator, temporary = self.stale_owner(root, port, "stale-" + str(expected_status))
                self.assertEqual(self.request(other, "/api/shutdown", "POST", {"instanceId": locator["instanceId"]},
                                              {"Authorization": "Bearer " + locator["localShutdown"]["token"]}, local=local)[0], expected_status)
                with mock.patch.object(backend.http.client, "HTTPConnection") as connection:
                    result = backend.cleanup(studio, root)
                    connection.assert_not_called()
                self.assertEqual(result["status"], "PASS")
                self.assertTrue(result["temporaryRemoved"])
                self.assertFalse(temporary.exists())
                self.assertFalse(other.stop.is_set())
                self.assertEqual(self.request(other)[0], 200)

    def test_restart_reaps_the_prior_crashed_owner_before_replacing_its_locator(self):
        previous, old_temporary = self.stale_owner()
        server = self.start()
        self.assertFalse(old_temporary.exists())
        self.assertNotEqual(studio.read_json(self.root / ".design-server.json")["instanceId"], previous["instanceId"])
        current_temporary = server.temporary
        backend.cleanup(studio, self.root)
        self.assertFalse(current_temporary.exists())
        self.assertTrue(server.closed.wait(3))

    def test_restart_keeps_stale_recovery_information_when_reaping_fails(self):
        previous, old_temporary = self.stale_owner()
        with mock.patch.object(backend, "remove_stale_temporary", side_effect=OSError("Synthetic stale temporary failure")):
            with self.assertRaisesRegex(OSError, "Synthetic stale temporary failure"):
                backend.DesignServer(studio, self.root).start()
        self.assertEqual(studio.read_json(self.root / ".design-server.json"), previous)
        self.assertTrue(old_temporary.exists())
        self.assertTrue(backend.cleanup(studio, self.root)["temporaryRemoved"])

    def test_yolo_cleanup_requires_current_check_run_pass_and_no_human_form(self):
        root = fixture_run(self.repo, self.theme, mode="yolo")
        self.assertTrue(backend.yolo_ready(studio, root))
        (root / "visual.md").write_text("Changed synthetic evidence after final approval.", encoding="utf-8")
        self.assertFalse(backend.yolo_ready(studio, root))
        server = self.start(root, interval=0.05)
        self.assertFalse(server.closed.wait(0.2))
        request = backend.publish_request(studio, root, "yolo-plan", "plan", "Autonomous fixture", "No human approval form applies.", ["plan.html"])["request"]
        self.assertEqual(self.request(server, "/api/approval", "POST", self.payload(request))[0], 400)

    def test_successful_yolo_watcher_removes_its_own_runtime(self):
        root = fixture_run(self.repo, self.theme, mode="yolo")
        server = self.start(root, interval=0.05)
        temporary = server.temporary
        self.assertTrue(server.closed.wait(5))
        self.assertFalse((root / ".design-server.json").exists())
        self.assertFalse(temporary.exists())
        self.assertTrue((root / "artwork-library").exists())

    def test_registration_requests_cleanup_only_after_success(self):
        root = fixture_run(self.repo, self.theme, mode="yolo")
        server = self.start(root)
        with mock.patch.object(studio, "atomic_json", side_effect=OSError("Synthetic registry write failure")):
            with self.assertRaises(OSError):
                studio.register_theme(self.repo, "fixture", root)
        self.assertFalse(server.stop.is_set())
        result = studio.register_theme(self.repo, "fixture", root)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(server.closed.wait(5))
        self.assertFalse((root / ".design-server.json").exists())

    def test_registration_reports_cleanup_failure_without_undoing_registry(self):
        root = fixture_run(self.repo, self.theme, mode="yolo")
        registered_backend = studio._design_backend()
        with mock.patch.object(registered_backend, "cleanup_registered_yolo", return_value={"status": "FAIL", "error": "Synthetic local cleanup failure"}):
            result = studio.register_theme(self.repo, "fixture", root)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                exit_code = studio.main(["register", "--repo", str(self.repo), "--theme", "fixture", "--run", str(root)])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["cleanup"]["status"], "FAIL")
        self.assertIn("Registry registration succeeded", result["message"])
        self.assertEqual(exit_code, 2)
        self.assertEqual(studio.registry_read(self.repo / "themes")["themes"][0]["id"], "fixture")

    def test_failed_alias_publication_rolls_back_and_can_retry_the_same_addresses(self):
        for filename in (".design-server.json", ".design-status.json"):
            with self.subTest(failed_record=filename):
                server = self.start(host="0.0.0.0", lan_addresses=("192.0.2.25",))
                before = studio.read_json(self.root / ".design-server.json")
                write = backend.private_json
                failed = False

                def fail_once(engine, path, value):
                    nonlocal failed
                    if path.name == filename and not failed:
                        failed = True
                        raise OSError("Synthetic alias publication failure")
                    return write(engine, path, value)

                with mock.patch.object(backend, "private_json", side_effect=fail_once):
                    with self.assertRaisesRegex(OSError, "Synthetic alias publication failure"):
                        server.set_lan_addresses(("192.0.2.26",))
                locator = studio.read_json(self.root / ".design-server.json")
                status = studio.read_json(self.root / ".design-status.json")
                for key in ("url", "localUrl", "lanUrls"):
                    self.assertEqual(locator[key], before[key])
                    self.assertEqual(status["server"][key], before[key])
                self.assertEqual(self.request(server, headers={"Host": urlsplit(before["url"]).netloc})[0], 200)
                replacement_host = f"192.0.2.26:{server.http.server_port}"
                self.assertEqual(self.request(server, headers={"Host": replacement_host})[0], 403)
                server.set_lan_addresses(("192.0.2.26",))
                self.assertEqual(self.request(server, headers={"Host": replacement_host})[0], 200)
                self.assertEqual(studio.read_json(self.root / ".design-server.json")["url"], server.url)
                server.close()

    def test_encoded_proxy_prefix_routes_identity_approval_and_retained_dependencies(self):
        (self.root / "scene.css").write_text("body{color:#123456}", encoding="utf-8")
        (self.root / "scene.html").write_text('<link rel="stylesheet" href="scene.css"><h1>Encoded prefix fixture</h1>', encoding="utf-8")
        server = self.start(public_url="https://studio.example.invalid:443/design%20review/")
        headers = {"Host": "studio.example.invalid"}
        code, unused, identity = self.request(server, "/design%20review/api/identity", headers=headers)
        self.assertEqual(code, 200)
        self.assertEqual(identity["run"], str(self.root))
        artwork = next(item for item in server.state.snapshot()["artworks"] if item["path"] == "scene.html")
        prefix = f"/design%20review/preview/{server.preview_capability}/{artwork['version']}/"
        code, response_headers, content = self.request(server, prefix + "scene.html", headers=headers, authenticated=False)
        self.assertEqual(code, 200)
        self.assertIn((prefix + "scene.css").encode(), content)
        self.assertIn("/design%20review/preview/", response_headers["Content-Security-Policy"])
        self.assertEqual(self.request(server, prefix + "scene.css", headers=headers, authenticated=False)[0], 200)
        request = self.plan("encoded-prefix-choice", ["scene.html"])
        code, unused, unused_body = self.request(server, "/design%20review/api/approval", "POST", self.payload(request),
                                               {**headers, "Origin": "https://studio.example.invalid"})
        self.assertEqual(code, 200)
        self.assertEqual(studio.read_json(self.root / "decisions.json")["decisions"][-1]["outcome"], "approved")

    def test_close_cancels_an_unfinished_header_without_retaining_the_run_lock(self):
        server = self.start()
        entered = threading.Event()
        setup = backend.Handler.setup

        def observe_setup(handler):
            setup(handler)
            entered.set()

        with mock.patch.object(backend.Handler, "setup", observe_setup):
            client = backend.socket.create_connection(("127.0.0.1", server.http.server_port), timeout=2)
            self.addCleanup(client.close)
            client.sendall(b"GET /api/identity HTTP/1.1\r\nX-Slow: unfinished")
            self.assertTrue(entered.wait(2))
            closer = threading.Thread(target=server.close, daemon=True)
            closer.start()
            self.assertTrue(server.closed.wait(3))
            closer.join(3)
        replacement = self.start()
        self.assertEqual(self.request(replacement)[0], 200)

    def test_close_drains_a_fully_admitted_approval_before_cleanup(self):
        request = self.plan()
        server = self.start()
        admitted, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        approve = backend.approve
        results = []

        def hold_approval(*args):
            admitted.set()
            if not release.wait(5):
                raise RuntimeError("Synthetic approval barrier was not released")
            return approve(*args)

        with mock.patch.object(backend, "approve", side_effect=hold_approval):
            writer = threading.Thread(target=lambda: results.append(self.request(server, "/api/approval", "POST", self.payload(request))), daemon=True)
            writer.start()
            self.assertTrue(admitted.wait(2))
            closer = threading.Thread(target=server.close, daemon=True)
            closer.start()
            try:
                self.assertFalse(server.closed.wait(0.05))
            finally:
                release.set()
            writer.join(3)
            closer.join(3)
        self.assertTrue(server.closed.is_set())
        self.assertEqual(results[0][0], 200)
        decision = studio.read_json(self.root / "decisions.json")["decisions"][-1]
        self.assertEqual(decision["outcome"], "approved")
        self.assertEqual(decision["inputsDigest"], request["inputsDigest"])


if __name__ == "__main__":
    unittest.main()
