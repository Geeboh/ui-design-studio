#!/usr/bin/env python3
"""Run one PRISM command through the CLI, MCP, and authenticated HTTP adapters."""
from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ui_design_studio.runtime import backend, studio


ENTRY = "from ui_design_studio.cli import mcp_main; raise SystemExit(mcp_main())"


def envelope(source_root: Path, operation_id: str) -> dict:
    return {
        "command": "project.initialize",
        "operationId": operation_id,
        "idempotencyKey": "adapter-parity-1",
        "actor": {"principal": "parity", "kind": "human", "mode": "guided"},
        "scope": {"projectId": "parity-project"},
        "expectedVersions": [],
        "payload": {"projectId": "parity-project", "sourceRoot": str(source_root), "stateRoot": str(source_root)},
    }


def cli_result(repo: Path, state: Path, command: dict) -> dict:
    input_path = repo / "cli-envelope.json"
    input_path.write_text(json.dumps(command), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "ui_design_studio.cli", "command", "--state", str(state), "--input", str(input_path), "--json"],
        cwd=repo,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


async def mcp_result(repo: Path, command: dict) -> dict:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-c", ENTRY, "--repo", str(repo), "--dashboard-host", "127.0.0.1"],
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"), "PYTHONUNBUFFERED": "1"},
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as client:
            await client.initialize()
            result = await client.call_tool("ui_design_command", {"envelope": command})
            if result.isError:
                raise RuntimeError(result.content)
            return result.structuredContent


def http_result(repo: Path, command: dict) -> dict:
    root = Path(studio().init_run(repo, theme_id="fixture")["run"])
    server = backend().DesignServer(studio(), root, host="127.0.0.1", interval=60, repo=repo).start()
    try:
        port = server.http.server_port
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            connection.request(
                "POST",
                "/api/command",
                json.dumps(command),
                headers={
                    "Authorization": "Bearer " + server.token,
                    "Content-Type": "application/json",
                    "Origin": f"http://127.0.0.1:{port}",
                    "Host": f"127.0.0.1:{port}",
                },
            )
            response = connection.getresponse()
            body = json.loads(response.read())
            if response.status != 200:
                raise RuntimeError(body)
            return body
        finally:
            connection.close()
    finally:
        server.close()


def comparable(value: dict) -> tuple:
    receipt = value["receipt"]
    return value["status"], receipt["command"], receipt["status"], receipt["requestFingerprint"], json.dumps(receipt["result"], sort_keys=True)


async def main() -> None:
    with tempfile.TemporaryDirectory(prefix="prism-adapter-parity-") as temporary:
        root = Path(temporary)
        cli_repo, mcp_repo, http_repo = (root / name for name in ("cli", "mcp", "http"))
        for repo in (cli_repo, mcp_repo, http_repo):
            repo.mkdir()
        source_root = root / "source"
        source_root.mkdir()
        cli = cli_result(cli_repo, root / "cli.sqlite3", envelope(source_root, "op-cli"))
        mcp = await mcp_result(mcp_repo, envelope(source_root, "op-mcp"))
        http = http_result(http_repo, envelope(source_root, "op-http"))
        values = {"cli": comparable(cli), "mcp": comparable(mcp), "http": comparable(http)}
        assert len(set(values.values())) == 1, values
        payload = {"status": "PASS", "adapters": values}
        print(json.dumps(payload, sort_keys=True))
        receipt = ROOT / ".prism-state" / "m1-adapter-parity.txt"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(f"status: PASS\nobservedAt: {datetime.now(timezone.utc).isoformat()}\nadapters: {json.dumps(values, sort_keys=True)}\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
