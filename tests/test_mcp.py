"""Isolated MCP protocol fixtures. These are not application design evidence."""
from __future__ import annotations

import argparse
import asyncio
import base64
from contextlib import asynccontextmanager
from datetime import timedelta
import http.client
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qs, quote, urljoin, urlsplit

import mcp.client.stdio as transport
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from mcp.types import CallToolResult

from test_studio import fixture_theme, studio, write_json

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE / "src"))
from ui_design_studio import cli, server as server_module


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aT9sAAAAASUVORK5CYII=")
ENTRY = "from ui_design_studio.cli import mcp_main; raise SystemExit(mcp_main())"
CLI_ENTRY = "from ui_design_studio.cli import main; raise SystemExit(main())"
COMMANDS = (
    "doctor", "theme-new", "build-theme", "check-theme", "theme-digest", "check-run",
    "context-digest", "models-digest", "decision-digest", "package", "register", "status",
    "progress", "worker", "artwork", "approval-request", "design-cleanup",
)


def request(url: str, endpoint: str = "api/identity"):
    parsed = urlsplit(urljoin(url, endpoint))
    token = parse_qs(urlsplit(url).fragment)["token"][0]
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
    try:
        connection.request("GET", parsed.path, headers={"Authorization": "Bearer " + token})
        response = connection.getresponse()
        body = response.read()
        if response.getheader("Content-Type", "").startswith("application/json"):
            body = json.loads(body)
        return response.status, body
    finally:
        connection.close()


class MCPProtocolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ui-design-mcp-protocol-")
        self.repo = Path(self.temporary.name) / "project with spaces"
        self.repo.mkdir()
        self.theme = fixture_theme(self.repo)
        self.errors = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        self.processes = {}
        self.environment = {"PYTHONPATH": str(SOURCE / "src"), "PYTHONUNBUFFERED": "1"}
        original = transport._create_platform_compatible_process

        async def capture(*args, **kwargs):
            process = await original(*args, **kwargs)
            self.processes[asyncio.current_task()] = process
            return process

        self.launcher_patch = mock.patch.object(transport, "_create_platform_compatible_process", capture)
        self.launcher_patch.start()

    def tearDown(self):
        self.launcher_patch.stop()
        self.errors.close()
        self.temporary.cleanup()

    @asynccontextmanager
    async def connect(self, *extra):
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-c", ENTRY, "--repo", str(self.repo), "--dashboard-host", "127.0.0.1", *extra],
            env=self.environment, cwd=Path(self.temporary.name),
        )
        async with stdio_client(parameters, errlog=self.errors) as (read, write):
            process = self.processes[asyncio.current_task()]
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as client:
                initialized = await client.initialize()
                self.assertEqual(initialized.serverInfo.name, "UI Design Studio")
                self.assertEqual(initialized.serverInfo.version, "1.4.0")
                yield client, process

    async def call(self, client, tool_name, **arguments):
        result = await client.call_tool(tool_name, arguments)
        self.assertFalse(result.isError, result.content)
        self.assertIsInstance(result.structuredContent, dict)
        return result.structuredContent

    async def fail(self, client, tool_name, **arguments):
        result = await client.call_tool(tool_name, arguments)
        self.assertTrue(result.isError, result)
        return result

    async def start(self, client):
        return await self.call(client, "ui_design_start_run", theme_id="fixture")

    def resource_json(self, result):
        self.assertEqual(len(result.contents), 1)
        return json.loads(result.contents[0].text)

    def records(self):
        return list((self.repo / ".ui-design-studio/runtime/mcp").glob("*.json"))

    def run_cli(self, *arguments):
        return subprocess.run([sys.executable, "-c", CLI_ENTRY, *arguments],
                              cwd=self.temporary.name, env={**os.environ, **self.environment},
                              text=True, capture_output=True, timeout=20, check=False)

    def assert_closed(self, url):
        with self.assertRaises((OSError, http.client.HTTPException)):
            request(url)

    async def test_initialize_starts_landing_before_any_tool_without_a_run(self):
        async with self.connect() as (client, process):
            records = self.records()
            self.assertEqual(len(records), 1)
            record = json.loads(records[0].read_text(encoding="utf-8"))
            self.assertEqual(record["repo"], str(self.repo.resolve()))
            self.assertIsNone(record["run"])
            self.assertIsNone(record["selectedRun"])
            self.assertFalse(list(self.repo.rglob("run.json")))
            code, identity = request(record["localUrl"])
            self.assertEqual(code, 200)
            self.assertEqual(identity, {"instanceId": record["instanceId"], "repo": str(self.repo.resolve())})
            details = self.resource_json(await client.read_resource("ui-design://dashboard"))
            self.assertEqual(details["instanceId"], record["instanceId"])
            self.assertEqual(details["localUrl"], record["localUrl"])
            self.assertEqual(details["lanUrls"], [])
            self.assertEqual(request(details["localUrl"], "api/session")[0], 200)
            self.assertNotIn("localShutdown", json.dumps(details))
            self.assertEqual(process.returncode, None)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(self.records(), [])
        self.assert_closed(details["localUrl"])

    async def test_lists_exact_typed_tools_concrete_guides_and_workflow(self):
        async with self.connect() as (client, unused):
            listed = await client.list_tools()
            tools = {tool.name: tool for tool in listed.tools}
            expected = {"ui_design_" + name.replace("-", "_") for name in COMMANDS}
            expected.update({"ui_design_start_run", "ui_design_resume_run", "ui_design_dashboard_info", "ui_design_read_guide"})
            self.assertEqual(set(tools), expected)
            parser = studio.parser()
            parsers = next(action.choices for action in parser._actions if isinstance(action, argparse._SubParsersAction))
            pairs = [(command, "ui_design_" + command.replace("-", "_")) for command in COMMANDS]
            pairs.append(("init-run", "ui_design_start_run"))
            for command, name in pairs:
                excluded = {"help", "repo", "profile", "watch"}
                actions = [action for action in parsers[command]._actions if action.dest not in excluded]
                schema = tools[name].inputSchema
                with self.subTest(command=command):
                    self.assertEqual(set(schema.get("properties", {})), {action.dest for action in actions})
                    self.assertEqual(set(schema.get("required", [])), {action.dest for action in actions if action.required})
                    for action in actions:
                        field = schema["properties"][action.dest]
                        if not action.required:
                            self.assertEqual(field.get("default"), action.default)
                        if action.choices:
                            alternatives = field.get("anyOf", [field])
                            enum = next(item["enum"] for item in alternatives if "enum" in item)
                            self.assertEqual(set(enum), set(action.choices))
            self.assertFalse(tools["ui_design_status"].annotations.readOnlyHint)
            for name in ("doctor", "check_theme", "check_run", "decision_digest", "context_digest", "models_digest"):
                self.assertTrue(tools["ui_design_" + name].annotations.readOnlyHint)
            self.assertNotIn("ui_design_models_apply", tools)
            self.assertNotIn("ui_design_design_serve", tools)
            resources = {str(item.uri) for item in (await client.list_resources()).resources}
            name = "skills/ui-design-studio/SKILL.md"
            uri = "ui-design://guide/" + name
            self.assertIn(uri, resources)
            self.assertIn("ui-design://guide/agents/ui-page-designer.md", resources)
            self.assertEqual(sum(item.endswith("/SKILL.md") for item in resources), 9)
            templates = await client.list_resource_templates()
            self.assertIn("ui-design://status/{run}", {item.uriTemplate for item in templates.resourceTemplates})
            guide = await self.call(client, "ui_design_read_guide", name=name)
            resource = await client.read_resource(uri)
            self.assertEqual(resource.contents[0].text, guide["text"])
            self.assertIn("ui-design://guide/skills/ui-design-studio/references/workflow.md", guide["text"])
            self.assertIn("ui-design://guide/skills/ui-design-studio/references/project-context.md", guide["text"])
            self.assertEqual([item.name for item in (await client.list_prompts()).prompts], ["ui_design_workflow"])
            for intent in ("guided", "yolo", "assess-only"):
                prompt = await client.get_prompt("ui_design_workflow", {"intent": intent})
                text = prompt.messages[0].content.text
                self.assertTrue(text.startswith("# Use UI Design Studio through MCP"))
                self.assertIn("OMP-only", text)
                self.assertIn("Pi Tasks", text)
                self.assertIn("sequential role passes", text)
                self.assertIn("repository-relative", text)
            with self.assertRaises(McpError) as failure:
                await client.get_prompt("ui_design_workflow", {"intent": "resume"})
            self.assertIn("Resume intent requires run", str(failure.exception))
            self.assertFalse(list(self.repo.rglob("run.json")))
            denied = await self.fail(client, "ui_design_read_guide", name="../README.md")
            self.assertEqual(denied.structuredContent["error"], "Unknown guide: ../README.md")
            with self.assertRaises(McpError):
                await client.read_resource("ui-design://guide/skills/ui-design-studio/scripts/studio.py")

    async def test_start_resume_progress_artwork_and_review_preserve_pending_gates(self):
        async with self.connect() as (client, unused):
            started = await self.start(client)
            relative = started["run"]
            root = self.repo / relative
            self.assertFalse(Path(relative).is_absolute())
            document = json.loads((root / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "pending")
            self.assertEqual(document["phase"], "assessment")
            self.assertIsNone(document["projectContext"]["sha256"])
            self.assertEqual(document["evidence"], [])
            self.assertEqual(started["landing"]["run"], None)
            resumed = await self.call(client, "ui_design_resume_run", run=relative)
            self.assertEqual(resumed["run"], relative)
            self.assertEqual(resumed["dashboard"]["instanceId"], started["dashboard"]["instanceId"])
            self.assertEqual(len(list(self.repo.rglob("run.json"))), 1)
            progress = await self.call(client, "ui_design_progress", run=relative,
                                       next_action="Review the first concept", blocker=["Synthetic pending assessment"])
            self.assertEqual(progress["dashboard"]["instanceId"], started["dashboard"]["instanceId"])
            self.assertEqual(progress["landing"]["instanceId"], started["landing"]["instanceId"])
            worker = await self.call(client, "ui_design_worker", run=relative, id="concept",
                                     task="Render a synthetic concept", status="active", message="Fixture pass", model="fixture/model")
            self.assertEqual(worker["worker"]["model"], "fixture/model")
            (root / "tiny.png").write_bytes(PNG)
            artwork = await self.call(client, "ui_design_artwork", run=relative, file=relative + "/tiny.png",
                                      context="Synthetic retained image for protocol verification", title="Tiny fixture")
            self.assertEqual(artwork["artwork"]["path"], "tiny.png")
            (root / "plan.html").write_text("<!doctype html><title>Synthetic concept</title><h1>Fixture board</h1>", encoding="utf-8")
            write_json(root / "choices.json", [{"id": "accept", "label": "Accept fixture"},
                                               {"id": "revise", "label": "Revise fixture"}])
            review = await self.call(client, "ui_design_approval_request", run=relative, id="first-plan", stage="plan",
                                     title="Review fixture", context="Synthetic protocol review, not application acceptance",
                                     files=[relative + "/plan.html"], choices=relative + "/choices.json")
            self.assertEqual(review["request"]["status"], "pending")
            self.assertEqual(review["request"]["options"][0]["id"], "accept")
            self.assertIn("project-context.md", review["request"]["inputs"])
            self.assertEqual(json.loads((root / "decisions.json").read_text(encoding="utf-8"))["decisions"], [])
            code, snapshot = request(started["dashboard"]["localUrl"], "api/snapshot")
            self.assertEqual(code, 200)
            self.assertEqual(snapshot["nextAction"], "Review the first concept")
            self.assertEqual(snapshot["blockers"], ["Synthetic pending assessment"])
            retained = next(item for item in snapshot["artworks"] if item["path"] == "tiny.png")
            self.assertEqual(request(started["dashboard"]["localUrl"], retained["url"]), (200, PNG))
            status = await self.call(client, "ui_design_status", run=relative)
            self.assertEqual(status["nextAction"], "Review the first concept")
            self.assertEqual(status["dashboard"]["instanceId"], started["dashboard"]["instanceId"])
            resource = self.resource_json(await client.read_resource("ui-design://status/" + quote(relative, safe="")))
            self.assertEqual(resource["run"]["id"], document["id"])
            self.assertEqual(resource["nextAction"], "Review the first concept")
            prompt = await client.get_prompt("ui_design_workflow", {"intent": "resume", "run": relative})
            self.assertIn("ui-design://status/" + quote(relative, safe=""), prompt.messages[0].content.text)
            checked = await self.fail(client, "ui_design_check_run", path=relative)
            self.assertEqual(checked.structuredContent["status"], "BLOCKED")
            self.assertTrue(checked.structuredContent["pending"])
            locator = json.loads((root / ".design-server.json").read_text(encoding="utf-8"))
            published = json.dumps({"started": started, "resumed": resumed, "status": status})
            self.assertNotIn(locator["localShutdown"]["token"], published)
            self.assertNotIn(locator["tempDirectory"], published)
        self.assertEqual(self.records(), [])
        self.assert_closed(started["dashboard"]["localUrl"])
        self.assert_closed(started["landing"]["localUrl"])
        self.assertTrue((root / "run.json").exists())
        self.assertTrue((root / "artwork-library").is_dir())

    async def test_repository_relative_inputs_and_configured_directory_boundaries(self):
        async with self.connect() as (client, unused):
            started = await self.start(client)
            relative = started["run"]
            root = self.repo / relative
            (root / "plan.html").write_text("<h1>Synthetic plan</h1>", encoding="utf-8")
            (self.repo / "plan.html").write_text("Outside the selected run", encoding="utf-8")
            for bad in ("../outside", str(root), relative + "/../escape", "themes/fixture", "docs\\design\\runs"):
                with self.subTest(path=bad):
                    await self.fail(client, "ui_design_resume_run", run=bad)
            await self.fail(client, "ui_design_check_theme", path=relative)
            await self.fail(client, "ui_design_check_run", path="themes/fixture")
            short = await self.fail(client, "ui_design_decision_digest", path=relative, files=["plan.html"])
            self.assertEqual(short.structuredContent["error"], "Input file must be inside the selected run")
            await self.fail(client, "ui_design_approval_request", run=relative, id="bad-plan", stage="plan",
                            title="Invalid path", context="Reject a run-relative file argument", files=["plan.html"])
            await self.fail(client, "ui_design_approval_request", run=relative, id="bad-choices", stage="plan",
                            title="Invalid choices", context="Reject a foreign choices file",
                            files=[relative + "/plan.html"], choices="themes/fixture/theme.json")
            await self.fail(client, "ui_design_package", path="themes/fixture", output="../escape.zip")
            await self.fail(client, "ui_design_progress", run=relative)
            await self.fail(client, "ui_design_worker", run=relative, id="worker", task="Fixture", status="invented", message="Invalid enum")
            (self.repo / "outside.png").write_bytes(PNG)
            await self.fail(client, "ui_design_artwork", run=relative, file="outside.png", context="Reject unrelated project file")
            with tempfile.TemporaryDirectory(prefix="ui-design-mcp-outside-") as outside:
                escape = self.repo / "docs/design/runs/escape"
                escape.symlink_to(outside, target_is_directory=True)
                write_json(Path(outside) / "run.json", {"id": "foreign"})
                await self.fail(client, "ui_design_resume_run", run="docs/design/runs/escape")
                (root / "linked.html").symlink_to(self.repo / "plan.html")
                await self.fail(client, "ui_design_decision_digest", path=relative, files=[relative + "/linked.html"])
                (self.repo / "packages").symlink_to(outside, target_is_directory=True)
                await self.fail(client, "ui_design_package", path="themes/fixture", output="packages/theme.zip")
                self.assertEqual(list(Path(outside).glob("*.zip")), [])
            expected = studio.file_digest(root, ["plan.html"])
            digest = await self.call(client, "ui_design_decision_digest", path=relative, files=[relative + "/plan.html"])
            self.assertEqual(digest, {"status": "PASS", "inputs": [relative + "/plan.html"], "inputsDigest": expected})
            self.assertFalse((root / "approval-requests/bad-plan.json").exists())

    async def test_configured_run_and_theme_roots_replace_the_defaults(self):
        configured_theme = self.repo / "branding/themes/fixture"
        configured_theme.parent.mkdir(parents=True)
        self.theme.rename(configured_theme)
        write_json(self.repo / "ui-design-studio.json", {"paths": {"themes": "branding/themes", "runs": "design/runs"}})
        async with self.connect() as (client, unused):
            started = await self.start(client)
            self.assertTrue(started["run"].startswith("design/runs/"))
            checked = await self.call(client, "ui_design_check_theme", path="branding/themes/fixture")
            self.assertEqual(checked["themeId"], "fixture")
            created = await self.call(client, "ui_design_theme_new", id="configured", name="Configured fixture")
            self.assertEqual(Path(created["theme"]), self.repo / "branding/themes/configured")
            (self.repo / "themes/foreign").mkdir(parents=True)
            await self.fail(client, "ui_design_check_theme", path="themes/foreign")
            published = await self.call(client, "ui_design_artwork", run=started["run"],
                                        file="branding/themes/fixture/preview.html", context="Synthetic configured theme fixture")
            self.assertEqual(published["artwork"]["path"], "theme-artwork/fixture/preview.html")
            doctor = await self.call(client, "ui_design_doctor")
            self.assertEqual(doctor["themeDirectory"], str(self.repo / "branding/themes"))
            self.assertEqual(doctor["runDirectory"], str(self.repo / "design/runs"))

    async def test_engine_operations_keep_validation_defaults_and_cleanup_scope(self):
        async with self.connect() as (client, unused):
            started = await self.start(client)
            relative = started["run"]
            doctor = await self.call(client, "ui_design_doctor")
            self.assertEqual(doctor["runDirectory"], str(self.repo / "docs/design/runs"))
            new_theme = await self.call(client, "ui_design_theme_new", id="new-theme", name="Synthetic MCP theme")
            self.assertEqual(new_theme["status"], "PASS")
            built = await self.call(client, "ui_design_build_theme", path="themes/new-theme")
            checked = await self.call(client, "ui_design_check_theme", path="themes/new-theme")
            digest = await self.call(client, "ui_design_theme_digest", path="themes/new-theme")
            self.assertEqual(digest, {"status": "PASS", "themeId": "new-theme", "themeDigest": checked["themeDigest"]})
            self.assertEqual(built["status"], "PASS")
            package = await self.call(client, "ui_design_package", path="themes/new-theme", output="packages/new-theme.zip")
            self.assertTrue((self.repo / "packages/new-theme.zip").is_file())
            self.assertEqual(package["sha256"], studio.sha_file(self.repo / "packages/new-theme.zip"))
            await self.fail(client, "ui_design_package", path="themes/new-theme", output="packages/new-theme.zip")
            for name in ("context_digest", "models_digest"):
                result = await self.call(client, "ui_design_" + name, path=relative)
                self.assertEqual(result["status"], "PASS")
            registration = await self.fail(client, "ui_design_register", theme="fixture", run=relative)
            self.assertIn("Run is BLOCKED", registration.structuredContent["error"])
            self.assertFalse((self.repo / "themes/registry.json").exists())
            await self.fail(client, "ui_design_design_cleanup")
            await self.fail(client, "ui_design_design_cleanup", run=relative, all=True)
            cleaned = await self.call(client, "ui_design_design_cleanup", run=relative)
            self.assertTrue(cleaned["stopped"])
            self.assert_closed(started["dashboard"]["localUrl"])
            landing = await self.call(client, "ui_design_dashboard_info")
            self.assertEqual(landing["instanceId"], started["landing"]["instanceId"])
            self.assertEqual(request(landing["localUrl"])[0], 200)
            stopped = await self.fail(client, "ui_design_dashboard_info", run=relative)
            self.assertEqual(stopped.structuredContent["error"], "Dashboard is not running.")
            restarted = await self.call(client, "ui_design_resume_run", run=relative)
            self.assertNotEqual(restarted["dashboard"]["instanceId"], started["dashboard"]["instanceId"])
            all_cleaned = await self.call(client, "ui_design_design_cleanup", all=True)
            self.assertEqual(all_cleaned["status"], "PASS")
            self.assert_closed(restarted["dashboard"]["localUrl"])
            self.assertTrue((self.repo / relative / "run.json").exists())

    async def test_start_failure_keeps_created_relative_run_for_resume(self):
        adapter = server_module.create_server(self.repo, dashboard_host="127.0.0.1")
        with mock.patch.object(server_module.DashboardSession, "open_run", side_effect=ValueError("Synthetic dashboard opening failure")):
            result = await adapter.call_tool("ui_design_start_run", {"theme_id": "fixture"})
        self.assertIsInstance(result, CallToolResult)
        self.assertTrue(result.isError)
        self.assertEqual(result.structuredContent["error"], "Synthetic dashboard opening failure")
        relative = result.structuredContent["run"]
        self.assertFalse(Path(relative).is_absolute())
        self.assertTrue((self.repo / relative / "run.json").is_file())
        self.assertEqual(len(list(self.repo.rglob("run.json"))), 1)
        self.assertEqual(self.records(), [])
        async with self.connect() as (client, unused):
            resumed = await self.call(client, "ui_design_resume_run", run=relative)
            self.assertEqual(resumed["run"], relative)
            self.assertEqual(len(list(self.repo.rglob("run.json"))), 1)

    async def test_concurrent_clients_share_one_run_owner_and_borrower_does_not_stop_it(self):
        relative = Path(studio.init_run(self.repo, theme_id="fixture")["run"]).relative_to(self.repo).as_posix()
        open_gate = asyncio.Event()
        opened = [asyncio.Event(), asyncio.Event()]
        close_gates = [asyncio.Event(), asyncio.Event()]
        initialized = [asyncio.Event(), asyncio.Event()]
        state = [{}, {}]

        async def client_task(index):
            async with self.connect() as (client, process):
                state[index]["landing"] = await self.call(client, "ui_design_dashboard_info")
                state[index]["pid"] = process.pid
                initialized[index].set()
                await open_gate.wait()
                state[index]["opened"] = await self.call(client, "ui_design_resume_run", run=relative)
                opened[index].set()
                await close_gates[index].wait()

        tasks = [asyncio.create_task(client_task(index)) for index in range(2)]
        try:
            await asyncio.wait_for(asyncio.gather(*(event.wait() for event in initialized)), timeout=20)
            self.assertNotEqual(state[0]["landing"]["instanceId"], state[1]["landing"]["instanceId"])
            self.assertNotEqual(state[0]["landing"]["localUrl"], state[1]["landing"]["localUrl"])
            open_gate.set()
            await asyncio.wait_for(asyncio.gather(*(event.wait() for event in opened)), timeout=20)
            direct = [item["opened"]["dashboard"] for item in state]
            self.assertEqual(direct[0]["instanceId"], direct[1]["instanceId"])
            locator = json.loads((self.repo / relative / ".design-server.json").read_text(encoding="utf-8"))
            owner = next(index for index in range(2) if state[index]["pid"] == locator["pid"])
            borrower = 1 - owner
            close_gates[borrower].set()
            await asyncio.wait_for(tasks[borrower], timeout=10)
            self.assertEqual(request(direct[owner]["localUrl"])[0], 200)
            self.assertEqual(request(state[owner]["landing"]["localUrl"])[0], 200)
            self.assertEqual(len(self.records()), 1)
            close_gates[owner].set()
            await asyncio.wait_for(tasks[owner], timeout=10)
            self.assert_closed(direct[owner]["localUrl"])
        finally:
            open_gate.set()
            for gate in close_gates:
                gate.set()
            await asyncio.gather(*tasks, return_exceptions=True)
        self.assertEqual(self.records(), [])

    async def test_borrower_detects_owner_eof_and_can_explicitly_resume(self):
        ready = asyncio.Event()
        inspect_stopped = asyncio.Event()
        finished = asyncio.Event()
        state = {}

        async def borrower_task(relative):
            async with self.connect() as (client, unused):
                state["borrowed"] = await self.call(client, "ui_design_resume_run", run=relative)
                ready.set()
                await inspect_stopped.wait()
                stopped = await self.fail(client, "ui_design_dashboard_info", run=relative)
                self.assertEqual(stopped.structuredContent["error"], "Dashboard is not running.")
                self.assertEqual(request(state["borrowed"]["landing"]["localUrl"])[0], 200)
                state["reopened"] = await self.call(client, "ui_design_resume_run", run=relative)
                finished.set()

        borrower = None
        try:
            async with self.connect() as (owner, unused):
                started = await self.start(owner)
                borrower = asyncio.create_task(borrower_task(started["run"]))
                await asyncio.wait_for(ready.wait(), timeout=20)
                self.assertEqual(state["borrowed"]["dashboard"]["instanceId"], started["dashboard"]["instanceId"])
            self.assert_closed(started["dashboard"]["localUrl"])
            inspect_stopped.set()
            await asyncio.wait_for(finished.wait(), timeout=20)
            await asyncio.wait_for(borrower, timeout=10)
            self.assertNotEqual(state["reopened"]["dashboard"]["instanceId"], started["dashboard"]["instanceId"])
        finally:
            inspect_stopped.set()
            if borrower is not None:
                await asyncio.gather(borrower, return_exceptions=True)

    async def test_dashboard_info_cli_uses_verified_endpoints_and_requires_session_selection(self):
        async with self.connect() as (first, unused):
            started = await self.start(first)
            arguments = ["dashboard-info", "--repo", str(self.repo)]
            human = self.run_cli(*arguments)
            self.assertEqual(human.returncode, 0, human.stderr)
            lines = human.stdout.splitlines()
            self.assertEqual(lines[0], "[ok] Dashboard live → " + started["landing"]["localUrl"])
            self.assertEqual(lines[1], "[lan] unavailable")
            self.assertEqual(human.stderr, "")
            self.assertNotIn('"schemaVersion"', human.stdout)
            structured = self.run_cli(*arguments, "--json")
            self.assertEqual(structured.returncode, 0, structured.stderr)
            details = json.loads(structured.stdout)
            self.assertEqual(details["text"].rstrip("\n"), human.stdout.rstrip("\n"))
            self.assertEqual(details["localUrl"], started["landing"]["localUrl"])
            direct = self.run_cli(*arguments, "--run", started["run"], "--json")
            self.assertEqual(direct.returncode, 0, direct.stderr)
            self.assertEqual(json.loads(direct.stdout)["instanceId"], started["dashboard"]["instanceId"])
            async with self.connect() as (second, unused):
                other = await self.call(second, "ui_design_dashboard_info")
                ambiguous = self.run_cli(*arguments)
                self.assertEqual(ambiguous.returncode, 2)
                self.assertEqual(ambiguous.stdout, "")
                for item in (started["landing"], other):
                    command = f"ui-design dashboard-info --repo {shlex.quote(str(self.repo))} --session {item['instanceId']}"
                    self.assertIn(command, ambiguous.stderr)
                structured_error = self.run_cli(*arguments, "--json")
                self.assertEqual(structured_error.returncode, 2)
                self.assertEqual(set(json.loads(structured_error.stdout)["sessionIds"]),
                                 {started["landing"]["instanceId"], other["instanceId"]})
                self.assertEqual(structured_error.stderr, "")
                explicit = self.run_cli(*arguments, "--session", other["instanceId"], "--json")
                self.assertEqual(explicit.returncode, 0, explicit.stderr)
                self.assertEqual(json.loads(explicit.stdout)["instanceId"], other["instanceId"])
        dead = self.run_cli("dashboard-info", "--repo", str(self.repo))
        self.assertEqual(dead.returncode, 1)
        self.assertEqual(dead.stdout, "")
        self.assertEqual(dead.stderr, "[error] Dashboard is not running.\n")
        error = self.run_cli("dashboard-info", "--repo", str(self.repo), "--json")
        self.assertEqual(error.returncode, 1)
        self.assertEqual(json.loads(error.stdout)["error"], "Dashboard is not running.")
        self.assertEqual(error.stderr, "")
        self.assertEqual(self.records(), [])
        missing_run = self.run_cli("dashboard-info", "--repo", str(self.repo), "--run", "docs/design/runs/not-running")
        self.assertEqual(missing_run.returncode, 1)
        self.assertEqual(missing_run.stdout, "")
        self.assertEqual(missing_run.stderr, "[error] Dashboard is not running.\n")

    async def test_sigterm_unwinds_lifespan_with_stdin_open(self):
        async with self.connect() as (client, process):
            started = await self.start(client)
            self.assertEqual(len(self.records()), 1)
            process.send_signal(signal.SIGTERM)
            await asyncio.wait_for(process.wait(), timeout=10)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(self.records(), [])
            self.assert_closed(started["landing"]["localUrl"])
            self.assert_closed(started["dashboard"]["localUrl"])
            self.assertTrue((self.repo / started["run"] / "run.json").is_file())

    async def test_occupied_explicit_landing_port_fails_initialization_without_a_fake_run(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            with self.assertRaises(Exception):
                async with self.connect("--dashboard-port", str(port)):
                    pass
        self.assertFalse(list(self.repo.rglob("run.json")))
        self.assertEqual(self.records(), [])

    async def test_launchers_reject_invalid_configuration_and_keep_engine_cli(self):
        for arguments in (["--repo", "."], ["--repo", str(self.repo), "--dashboard-port", "65536"],
                          ["--repo", str(self.repo), "--dashboard-host", "192.0.2.1"],
                          ["--repo", str(self.repo), "--lan-address", "::1"]):
            result = subprocess.run([sys.executable, "-c", ENTRY, *arguments],
                                    cwd=self.temporary.name, env={**os.environ, **self.environment},
                                    capture_output=True, text=True, timeout=10, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("error:", result.stderr)
        for arguments in (["--repo", "."], ["--repo", str(self.repo), "--run", "run", "--session", "session"],
                          ["--repo", str(self.repo), "--unexpected", "\x1b[2J"]):
            error = self.run_cli("dashboard-info", *arguments, "--json")
            self.assertEqual(error.returncode, 2)
            self.assertEqual(json.loads(error.stdout)["status"], "FAIL")
            self.assertEqual(error.stderr, "")
            self.assertNotIn("\x1b", error.stdout)
        delegated = self.run_cli("theme-digest", str(self.theme))
        self.assertEqual(delegated.returncode, 0, delegated.stderr)
        self.assertEqual(json.loads(delegated.stdout)["themeId"], "fixture")
        self.assertEqual(self.records(), [])

    async def test_stdio_and_eof_work_without_unix_signal_registration(self):
        entry = "import ui_design_studio.cli as cli; cli.sys.platform = 'win32'; raise SystemExit(cli.mcp_main())"
        with mock.patch(__name__ + ".ENTRY", entry):
            async with self.connect() as (client, process):
                details = await self.call(client, "ui_design_dashboard_info")
                self.assertEqual(request(details["localUrl"])[0], 200)
            self.assertEqual(process.returncode, 0)
        self.assertEqual(self.records(), [])


if __name__ == "__main__":
    unittest.main()
