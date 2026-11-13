"""Exercise wheel payloads outside the source checkout."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class WheelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="ui-design-wheel-test-")
        cls.base = Path(cls.temporary.name)
        supplied = os.environ.get("UI_DESIGN_TEST_WHEEL")
        if supplied:
            cls.wheel = Path(supplied)
        else:
            subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(cls.base / "dist")], cwd=ROOT, check=True, capture_output=True, text=True)
            cls.wheel, = (cls.base / "dist").glob("*.whl")
        cls.installed = cls.base / "installed"
        with zipfile.ZipFile(cls.wheel) as archive:
            cls.names = archive.namelist()
            archive.extractall(cls.installed)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_wheel_contains_authored_assets_and_no_runtime_secrets(self):
        for name in ("ui_design_studio/mcp-guide.md", "ui_design_studio/payload/skills/ui-design-studio/scripts/studio.py", "ui_design_studio/payload/skills/ui-design-studio/dashboard/landing.html", "ui_design_studio/payload/skills/ui-design-studio/dashboard/landing.js", "ui_design_studio/payload/skills/ui-design-studio/dashboard/dashboard.css", "ui_design_studio/payload/agents/ui-art-director.md"):
            self.assertIn(name, self.names)
        self.assertFalse(any("__pycache__" in name or ".design-server.json" in name or ".ui-design-studio" in name or name.endswith((".pyc", ".pyo")) for name in self.names))
        metadata = next(name for name in self.names if name.endswith(".dist-info/METADATA"))
        with zipfile.ZipFile(self.wheel) as archive:
            self.assertIn("Version: 1.4.0", archive.read(metadata).decode())
            self.assertEqual(archive.read("ui_design_studio/payload/skills/ui-design-studio/scripts/studio.py"), (ROOT / ".omp/skills/ui-design-studio/scripts/studio.py").read_bytes())

    def test_installed_cli_and_mcp_work_without_project_omp_install(self):
        outside = self.base / "outside"
        outside.mkdir(exist_ok=True)
        project = outside / "project"
        project.mkdir(exist_ok=True)
        script = '''
import asyncio, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ui_design_studio.runtime import PAYLOAD, studio
installed, repo = sys.argv[1:]
assert PAYLOAD.is_relative_to(Path(installed))
assert studio().VERSION == '1.4.0'
command = "import sys; sys.path.insert(0, " + repr(installed) + "); from ui_design_studio.cli import mcp_main; mcp_main()"
async def main():
    params = StdioServerParameters(command=sys.executable, args=['-I', '-c', command, '--repo', repo, '--dashboard-host', '127.0.0.1'])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as client:
            initialized = await client.initialize()
            assert initialized.serverInfo.name == 'UI Design Studio'
            assert initialized.serverInfo.version == '1.4.0'
            guide = await client.call_tool('ui_design_read_guide', {'name':'skills/ui-design-studio/SKILL.md'})
            assert not guide.isError, guide
            assert 'UI Design Studio' in str(guide)
            start = await client.call_tool('ui_design_start_run', {'theme_id':'installed-smoke'})
            assert not start.isError, start
            data = start.structuredContent
            run = data['run']
            resume = await client.call_tool('ui_design_resume_run', {'run':run})
            assert not resume.isError, resume
            assert resume.structuredContent['dashboard']['instanceId'] == data['dashboard']['instanceId']
            cli = "import sys; sys.path.insert(0, " + repr(installed) + "); from ui_design_studio.cli import main; raise SystemExit(main())"
            result = subprocess.run([sys.executable, '-I', '-c', cli, 'dashboard-info', '--repo', repo, '--run', run, '--json'], capture_output=True, text=True, check=True)
            details = json.loads(result.stdout)
            assert details['instanceId'] == data['dashboard']['instanceId']
            assert details['localUrl'].startswith('http://127.0.0.1:')
            assert '#token=' in details['localUrl']
            assert not (Path(repo)/'.omp').exists()
            import urllib.request
            url = details['localUrl'].split('#')[0]
            assert b'Design workspace' in urllib.request.urlopen(url, timeout=2).read()
            print(json.dumps({'run':run, 'bundledPayload':str(PAYLOAD), 'status':'PASS'}))
asyncio.run(main())
'''
        result = subprocess.run([sys.executable, "-I", "-c", script, str(self.installed), str(project)], cwd=outside, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "PASS")
        self.assertFalse((project / ".omp").exists())
        self.assertEqual(list((project / ".ui-design-studio/runtime/mcp").glob("*.json")), [])

    def test_installed_console_dashboard_serves_before_any_run(self):
        prefix = self.base / "console-prefix"
        subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-index",
                        "--no-deps", "--no-compile", "--ignore-installed", "--prefix", str(prefix), str(self.wheel)],
                       check=True, capture_output=True, text=True)
        executable = prefix / ("Scripts/ui-design.exe" if os.name == "nt" else "bin/ui-design")
        library = sysconfig.get_path("purelib", vars={"base": str(prefix), "platbase": str(prefix)})
        project = self.base / "console-project"
        project.mkdir()
        script = '''
import asyncio, http.client, json, os, socket, sys
from pathlib import Path
from urllib.parse import urlsplit
executable, library, repo = sys.argv[1:]
async def main():
    process = await asyncio.create_subprocess_exec(
        executable, 'dashboard-serve', '--repo', repo, '--dashboard-host', '127.0.0.1', '--parent-stdio', '--json',
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        cwd=repo, env=dict(os.environ, PYTHONPATH=library))
    try:
        line = await asyncio.wait_for(process.stdout.readline(), timeout=10)
        details = json.loads(line)
        assert details['repo'] == repo
        assert details['run'] is None
        assert details['state'] == 'live'
        assert details['text'].splitlines()[0] == '[ok] Dashboard live → ' + details['localUrl'] + ' (/ui-design-dashboard stop to stop)'
        assert not list(Path(repo).rglob('run.json'))
        assert not (Path(repo)/'.omp').exists()
        record, = (Path(repo)/'.ui-design-studio/runtime/mcp').glob('*.json')
        cached = json.loads(record.read_text())
        assert cached['instanceId'] == details['instanceId']
        assert cached['localUrl'] == details['localUrl']
        address = urlsplit(details['localUrl'])
        connection = http.client.HTTPConnection(address.hostname, address.port, timeout=3)
        try:
            connection.request('GET', '/api/identity', headers={'Authorization':'Bearer ' + address.fragment.removeprefix('token=')})
            response = connection.getresponse()
            assert response.status == 200
            assert json.loads(response.read()) == {'instanceId':details['instanceId'], 'repo':repo}
        finally:
            connection.close()
        process.stdin.close()
        await asyncio.wait_for(process.wait(), timeout=10)
        assert process.returncode == 0
        assert await asyncio.wait_for(process.stdout.read(), timeout=3) == b''
        assert await asyncio.wait_for(process.stderr.read(), timeout=3) == b''
        assert not record.exists()
        assert not list(Path(repo).rglob('run.json'))
        try:
            socket.create_connection((address.hostname, address.port), timeout=0.2).close()
        except OSError:
            pass
        else:
            raise AssertionError('The installed foreground listener must close on parent EOF.')
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
asyncio.run(main())
print(json.dumps({'status':'PASS'}))
'''
        result = subprocess.run([sys.executable, "-I", "-c", script, str(executable), library, str(project)],
                                cwd=self.base, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), {"status": "PASS"})

    def test_build_rejects_symlinked_payload_and_metadata(self):
        for target in ("src/ui_design_studio/private-link", "README.md", "LICENSE.txt"):
            with self.subTest(target=target):
                copied = self.base / ("unsafe-" + Path(target).name)
                copied.mkdir(exist_ok=True)
                for name in ("pyproject.toml", "hatch_build.py", "README.md", "LICENSE.txt"):
                    shutil.copyfile(ROOT / name, copied / name)
                for name in ("src", ".omp/skills", ".omp/agents"):
                    shutil.copytree(ROOT / name, copied / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
                link = copied / target
                link.unlink(missing_ok=True)
                link.symlink_to(ROOT / "README.md")
                result = subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(copied / "dist")], cwd=copied, capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Symlink is not distributable", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
