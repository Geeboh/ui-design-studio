"""Typed stdio operations over the bundled, authoritative Studio engine."""
from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from functools import partial, wraps
import json
from pathlib import Path
import posixpath
import re
from typing import Annotated, Any, Literal
from types import SimpleNamespace
from urllib.parse import quote, unquote, urlsplit

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from . import __version__
from .dashboard import DashboardSession, DashboardUnavailable
from .runtime import PACKAGE, PAYLOAD, backend, studio


Mode = Literal["guided", "yolo"]
ThemeAction = Literal["auto", "modify-default", "new"]
ModelPolicy = Literal["auto-models", "current-model"]
WorkerStatus = Literal["active", "blocked", "done", "failed", "pending"]
ReviewStage = Literal["plan", "design"]
WorkflowIntent = Literal["guided", "yolo", "assess-only", "resume"]
Scope = Literal["fix", "component", "single-flow", "reference-adaptation", "full-redesign", "assess-only", "design-only"]
Role = Literal["ui-art-director", "ui-implementer", "ui-page-designer", "ui-performance-reviewer",
               "ui-quality-reviewer", "ui-theme-engineer", "ui-ux-researcher"]
StatusCollection = Literal["artworks", "evidence"]
FileList = Annotated[list[str], Field(min_length=1)]
SKILLS = (
    "ui-design-studio", "ui-assess", "ui-plan", "ui-design", "ui-produce",
    "ui-review", "ui-finalize", "ui-theme", "ui-yolo",
)
ROLES = (
    "ui-art-director", "ui-implementer", "ui-page-designer",
    "ui-performance-reviewer", "ui-quality-reviewer", "ui-theme-engineer",
    "ui-ux-researcher",
)


def _reply(data: dict[str, Any], *, is_error: bool = False) -> CallToolResult:
    is_error = is_error or data.get("status") in ("FAIL", "BLOCKED")
    if isinstance(data.get("text"), str):
        text = data["text"]
    else:
        text = json.dumps({key: value for key, value in data.items()
                           if key not in ("dashboard", "landing")}, indent=2, ensure_ascii=False)
        for key in ("dashboard", "landing"):
            details = data.get(key)
            if isinstance(details, dict):
                url = details.get("localUrl") or next(iter(details.get("lanUrls", [])), None) or details.get("qrUrl")
                text += f"\n{key.title()}: {url}" if url else f"\n{key.title()}: unavailable"
    return CallToolResult(content=[TextContent(type="text", text=text)],
                          structuredContent=data, isError=is_error)


class _Guides:
    def __init__(self, engine):
        self.engine = engine
        names = set()
        for skill in SKILLS:
            names.add(f"skills/{skill}/SKILL.md")
            directory = PAYLOAD / "skills" / skill / "references"
            if directory.is_dir():
                names.update(path.relative_to(PAYLOAD).as_posix() for path in directory.rglob("*.md")
                             if path.is_file() and not path.is_symlink())
        names.update(f"agents/{role}.md" for role in ROLES)
        self.names = frozenset(names)

    def read(self, name: str) -> str:
        self.engine.require(name in self.names, f"Unknown guide: {name}")
        path = self.engine.safe_path(PAYLOAD, name)
        text = path.read_text(encoding="utf-8")

        def link(match):
            label, target = match.groups()
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                return match.group(0)
            candidate = (parsed.path.removeprefix(".omp/") if parsed.path.startswith(".omp/")
                         else posixpath.normpath(posixpath.join(posixpath.dirname(name), parsed.path)))
            if candidate not in self.names:
                return match.group(0)
            fragment = "#" + parsed.fragment if parsed.fragment else ""
            return f"[{label}](ui-design://guide/{candidate}{fragment})"

        text = re.sub(r"\[([^\]\n]+)\]\(([^\s)]+)\)", link, text)
        if name == "skills/ui-design-studio/SKILL.md":
            text = (PACKAGE / "mcp-guide.md").read_text(encoding="utf-8") + "\n\n" + text
        return text


def create_server(repo: Path | str, dashboard_host: str = "0.0.0.0", dashboard_port: int = 0,
                  lan_address: str | None = None) -> FastMCP:
    """Create one local MCP connection. Its lifespan owns its dashboard listeners."""
    root = Path(repo)
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("--repo must be an absolute existing repository directory")
    root = root.resolve()
    engine = studio()
    design = backend()
    guides = _Guides(engine)
    session = DashboardSession(root, host=dashboard_host, port=dashboard_port, lan_address=lan_address)

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[DashboardSession]:
        try:
            await anyio.to_thread.run_sync(session.start)
            yield session
        finally:
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(session.close)

    mcp = FastMCP(
        "UI Design Studio",
        instructions=("Read ui_design_workflow or ui_design_read_guide(name='skills/ui-design-studio/SKILL.md') before design work. "
                      "All paths, including file lists and choices, are repository-relative. "
                      "The dashboard resource is available before a run exists. "
                      "Guided human approval occurs only in the authenticated browser dashboard."),
        lifespan=lifespan,
    )
    # FastMCP 1.30 has no version argument and otherwise advertises the SDK version.
    mcp._mcp_server.version = __version__

    def tool(*, read_only: bool = False, destructive: bool = False, idempotent: bool = False):
        def register(function: Callable):
            @wraps(function)
            async def invoke(**arguments) -> CallToolResult:
                try:
                    engine.safe_path(root, "ui-design-studio.json", must_exist=False)
                    result = await anyio.to_thread.run_sync(partial(function, **arguments))
                    return result if isinstance(result, CallToolResult) else _reply(result)
                except Exception as exc:
                    return _reply({"status": "FAIL", "error": str(exc)}, is_error=True)

            mcp.add_tool(invoke, structured_output=False, annotations=ToolAnnotations(
                readOnlyHint=read_only, destructiveHint=destructive,
                idempotentHint=read_only or idempotent, openWorldHint=False,
            ))
            return function
        return register

    def path_in(relative: str, kind: Literal["run", "theme"]) -> Path:
        path = engine.safe_path(root, relative, allow_dir=True)
        engine.require(path.is_dir(), f"{kind.title()} path must be a directory")
        engine.safe_path(root, "ui-design-studio.json", must_exist=False)
        _, themes, runs = engine.config_paths(root)
        directory = runs if kind == "run" else themes
        engine.require(path != directory and path.is_relative_to(directory),
                       f"{kind.title()} must be under the configured {kind}s directory")
        if kind == "run":
            engine.safe_path(path, "run.json")
        return path

    def run_file(run_root: Path, relative: str) -> str:
        path = engine.safe_path(root, relative)
        engine.require(path.is_relative_to(run_root), "Input file must be inside the selected run")
        return path.relative_to(run_root).as_posix()

    def run_files(run_root: Path, files: list[str]) -> list[str]:
        return [run_file(run_root, file) for file in files]

    def connection_details(run: str) -> dict[str, Any]:
        try:
            details = session.info(run)
        except DashboardUnavailable:
            details = {"state": "stopped", "run": run, "error": "Dashboard is not running."}
        return {"dashboard": details, "landing": session.info()}

    def status_result(run: str, interval: float = 1.0) -> dict[str, Any]:
        run_root = path_in(run, "run")
        engine.require(interval > 0, "Status interval must be positive")
        result = design.command(design.studio, SimpleNamespace(
            command="status", run=str(run_root), watch=False, interval=interval,
        ))
        result.update(connection_details(run_root.relative_to(root).as_posix()))
        return result

    def compact_status_result(run: str, interval: float = 1.0) -> dict[str, Any]:
        result = status_result(run, interval)
        compact = design.compact_status(result)
        compact.update(connection_details(run))
        return compact

    def status_page_result(run: str, collection: StatusCollection, page_size: int = 50,
                           cursor: str | None = None, interval: float = 1.0) -> dict[str, Any]:
        result = status_result(run, interval)
        page = design.status_page(result, collection, page_size, cursor)
        page.update({"run": result["run"], "observedAt": result["observedAt"]})
        page.update(connection_details(run))
        return page

    @tool()
    def ui_design_start_run(theme_id: str, mode: Mode = "guided", theme_action: ThemeAction = "auto",
                            models: ModelPolicy | None = None, scope: Scope | None = None) -> dict[str, Any] | CallToolResult:
        """Create a pending run and select its dashboard. Resume the returned run after an opening failure."""
        result = engine.init_run(root, mode=mode, action=theme_action, theme_id=theme_id, model_policy=models, scope=scope)
        relative = Path(result["run"]).relative_to(root).as_posix()
        result["run"] = relative
        try:
            path_in(relative, "run")
            result["dashboard"] = session.open_run(relative)
            result["landing"] = session.info()
        except Exception as exc:
            return _reply({**result, "status": "FAIL", "error": str(exc),
                           "message": "Run was created. Resume this run instead of initializing another."}, is_error=True)
        return result

    @tool()
    def ui_design_resume_run(run: str) -> dict[str, Any]:
        """Open an existing repository-relative run without creating a dossier or granting approval."""
        run_root = path_in(run, "run")
        relative = run_root.relative_to(root).as_posix()
        return {"status": "PASS", "run": relative, "dashboard": session.open_run(relative),
                "landing": session.info()}

    @tool(read_only=True)
    def ui_design_doctor() -> dict[str, Any]:
        """Inspect local capabilities for the configured repository without running application gates."""
        return engine.doctor(root)

    @tool()
    def ui_design_theme_new(id: str, name: str) -> dict[str, Any]:
        """Scaffold an unregistered theme under the configured themes directory."""
        engine.validate_slug(id)
        _, themes, _ = engine.config_paths(root)
        engine.safe_path(root, (themes / id).relative_to(root).as_posix(), must_exist=False, allow_dir=True)
        return engine.theme_new(root, id, name)

    @tool(destructive=True, idempotent=True)
    def ui_design_build_theme(path: str) -> dict[str, Any]:
        """Compile a repository-relative theme under the configured themes directory."""
        return engine.build_theme(path_in(path, "theme"))

    @tool(read_only=True)
    def ui_design_check_theme(path: str) -> dict[str, Any]:
        """Validate a repository-relative theme without certifying application integration."""
        return engine.check_theme(path_in(path, "theme"))

    @tool(read_only=True)
    def ui_design_theme_digest(path: str) -> dict[str, Any]:
        """Return the validated status, theme ID and theme digest."""
        result = engine.check_theme(path_in(path, "theme"))
        return {key: result[key] for key in ("status", "themeId", "themeDigest")}

    @tool(read_only=True)
    def ui_design_check_run(path: str) -> dict[str, Any]:
        """Check the selected run's evidence, coverage, freshness and approvals without weakening gates."""
        return engine.check_run(path_in(path, "run"))

    @tool(destructive=True, idempotent=True)
    def ui_design_scope_complete(path: str, target: str, artifacts: FileList,
                                 blocker: list[str] | None = None, next: str | None = None) -> dict[str, Any]:
        """Record bounded scope closure without granting full-theme release."""
        return engine.complete_scope(path_in(path, "run"), target, run_files(path_in(path, "run"), artifacts), blocker, next)
    @tool(read_only=True)
    def ui_design_resume_check(path: str) -> dict[str, Any]:
        """Check changed run dependencies and transitive stale nodes without rerunning unchanged work."""
        return engine.resume_check(path_in(path, "run"))

    @tool(read_only=True)
    def ui_design_worker_packet(path: str, role: Role, objective: str, owned: FileList,
                                instruction: list[str] | None = None,
                                artifact: list[str] | None = None,
                                allow: list[str] | None = None) -> dict[str, Any]:
        """Generate a bounded role packet with original instructions and exact artifact hashes."""
        run_root = path_in(path, "run")
        if instruction is not None:
            for item in instruction:
                if not (run_root / item).exists():
                    engine.safe_path(root, item)
        return engine.worker_packet(run_root, role, objective, run_files(run_root, owned),
                                    instruction, run_files(run_root, artifact) if artifact else None, allow)

    @tool(read_only=True)
    def ui_design_context_digest(path: str) -> dict[str, Any]:
        """Hash recorded project context. This does not resolve requirements."""
        return engine.context_digest(path_in(path, "run"))

    @tool(read_only=True)
    def ui_design_models_digest(path: str) -> dict[str, Any]:
        """Hash recorded routing evidence without choosing or configuring models."""
        return engine.models_digest(path_in(path, "run"))

    @tool(read_only=True)
    def ui_design_decision_digest(path: str, files: FileList) -> dict[str, Any]:
        """Hash selected-run files. Both path and every file are repository-relative, not run-relative."""
        run_root = path_in(path, "run")
        inputs = run_files(run_root, files)
        return {"status": "PASS", "inputs": files, "inputsDigest": engine.file_digest(run_root, inputs)}

    @tool()
    def ui_design_package(path: str, output: str) -> dict[str, Any]:
        """Package a configured theme into a new repository-relative ZIP destination."""
        theme = path_in(path, "theme")
        destination = engine.safe_path(root, output, must_exist=False)
        return engine.package_theme(theme, destination)

    @tool(destructive=True, idempotent=True)
    def ui_design_register(theme: str, run: str, make_default: bool = False) -> dict[str, Any]:
        """Register a verified theme ID using its existing run and unchanged default-theme gates."""
        engine.validate_slug(theme)
        _, themes, _ = engine.config_paths(root)
        path_in((themes / theme).relative_to(root).as_posix(), "theme")
        return engine.register_theme(root, theme, path_in(run, "run"), make_default)

    @tool()
    def ui_design_status(run: str, interval: float = 1.0) -> dict[str, Any]:
        """Read one status snapshot plus verified dashboard details. Never start a watch loop."""
        return status_result(run, interval)

    @tool(read_only=True)
    def ui_design_status_compact(run: str, interval: float = 1.0) -> dict[str, Any]:
        """Read bounded status metadata. Use status-page for artwork or evidence listings."""
        return compact_status_result(run, interval)

    @tool(read_only=True)
    def ui_design_status_page(run: str, collection: StatusCollection, page_size: int = 50,
                              cursor: str | None = None, interval: float = 1.0) -> dict[str, Any]:
        """Read one revision-bound page of artwork or evidence metadata."""
        return status_page_result(run, collection, page_size, cursor, interval)

    @tool(destructive=True, idempotent=True)
    def ui_design_progress(run: str, next_action: str | None = None,
                           blocker: list[str] | None = None) -> dict[str, Any]:
        """Publish the director's actual next action or blocker list and return connection details."""
        run_root = path_in(run, "run")
        engine.require(next_action is not None or blocker is not None, "Publish --next or --blocker")
        result = design.publish_progress(design.studio, run_root, next_action, blocker)
        result.update(connection_details(run_root.relative_to(root).as_posix()))
        return result

    @tool(destructive=True, idempotent=True)
    def ui_design_worker(run: str, id: str, task: str, status: WorkerStatus,
                         message: str, model: str | None = None) -> dict[str, Any]:
        """Publish a worker's reported state. A record does not prove process liveness."""
        return design.publish_worker(design.studio, path_in(run, "run"), id, task, status, message, model)

    @tool()
    def ui_design_artwork(run: str, file: str, context: str, title: str | None = None) -> dict[str, Any]:
        """Retain artwork. file is repository-relative, inside the selected run or its active configured theme."""
        run_root = path_in(run, "run")
        source = engine.safe_path(root, file)
        if source.is_relative_to(run_root):
            return design.publish_artwork(design.studio, run_root, source.relative_to(run_root).as_posix(), context, title)
        document = engine.read_json(engine.safe_path(run_root, "run.json"))
        engine.validate_slug(document["themeId"])
        _, themes, _ = engine.config_paths(root)
        active = engine.safe_path(root, (themes / document["themeId"]).relative_to(root).as_posix(), allow_dir=True)
        engine.require(source.is_relative_to(active), "Explicit project publication is limited to the active theme directory")
        return design.publish_artwork(design.studio, run_root, file, context, title, str(root))

    @tool()
    def ui_design_approval_request(run: str, id: str, stage: ReviewStage, title: str, context: str,
                                   files: FileList, choices: str | None = None) -> dict[str, Any]:
        """Publish a guided review, never an approval. files and choices are repository-relative selected-run files."""
        run_root = path_in(run, "run")
        inputs = run_files(run_root, files)
        options = engine.read_json(engine.safe_path(run_root, run_file(run_root, choices))) if choices is not None else None
        return design.publish_request(design.studio, run_root, id, stage, title, context, inputs, options)

    @tool(destructive=True, idempotent=True)
    def ui_design_design_cleanup(run: str | None = None, all: bool = False) -> dict[str, Any]:
        """Stop a selected run or all run servers in this repository. Preserve evidence and foreign processes."""
        engine.require((all and run is None) or (run is not None and not all),
                       "Use design-cleanup RUN or design-cleanup --all --repo PATH")
        if all:
            engine.config_paths(root)
            return design.cleanup_all(design.studio, root)
        return design.cleanup(design.studio, path_in(run, "run"))

    @tool(read_only=True)
    def ui_design_dashboard_info(run: str | None = None) -> dict[str, Any]:
        """Return verified landing details or an explicit run's live details without starting a listener."""
        if run is not None:
            run = path_in(run, "run").relative_to(root).as_posix()
        return session.info(run)

    @tool(read_only=True)
    def ui_design_read_guide(name: str) -> dict[str, Any]:
        """Read a bundled guide. Begin with skills/ui-design-studio/SKILL.md for portable workflow instructions and guide links."""
        return {"status": "PASS", "name": name, "uri": f"ui-design://guide/{name}", "text": guides.read(name)}

    @mcp.resource("ui-design://dashboard", name="dashboard", mime_type="application/json")
    async def dashboard_resource() -> str:
        details = await anyio.to_thread.run_sync(session.info)
        return json.dumps(details, ensure_ascii=False)

    @mcp.resource("ui-design://status/{run}", name="status", mime_type="application/json",
                  description="One status snapshot. Percent-encode the entire repository-relative run as one URI segment.")
    async def status_resource(run: str) -> str:
        result = await anyio.to_thread.run_sync(partial(status_result, unquote(run, errors="strict")))
        return json.dumps(result, ensure_ascii=False)

    for name in sorted(guides.names):
        mcp.resource(f"ui-design://guide/{name}", name=name, mime_type="text/markdown",
                     description="Authoritative bundled design instructions. MCP host exclusions are in the workflow prompt.")(
            partial(guides.read, name))

    @mcp.prompt(name="ui_design_workflow")
    def workflow(intent: WorkflowIntent, run: str | None = None) -> str:
        """Read portable workflow instructions without starting a run. Resume requires an existing relative run."""
        engine.require(intent != "resume" or run is not None, "Resume intent requires run")
        selected = None
        if run is not None:
            selected = path_in(run, "run").relative_to(root).as_posix()
        names = ["skills/ui-design-studio/references/workflow.md",
                 "skills/ui-design-studio/references/multi-agent.md"]
        if intent in ("yolo", "assess-only"):
            names.append(f"skills/{'ui-yolo' if intent == 'yolo' else 'ui-assess'}/SKILL.md")
        text = guides.read("skills/ui-design-studio/SKILL.md")
        text += f"\n\nRequested workflow intent: {intent}.\n"
        if selected is not None:
            text += f"Existing run: {selected}.\nStatus resource: ui-design://status/{quote(selected, safe='')}\n"
        return text + "\n\n" + "\n\n".join(f"## {name}\n\n{guides.read(name)}" for name in names)

    return mcp
