# Connect UI Design Studio through local MCP

Use the Python package when your local coding client supports MCP stdio. The package bundles the existing engine, nine skill guides, seven role briefs, dashboard assets, schemas, and specimen theme. No project-local OMP installation is required.

## Install the adapter

Require Python 3.10 or later. From the distribution directory, run these commands.

```bash
python3 -m venv /absolute/path/to/ui-design-env
/absolute/path/to/ui-design-env/bin/python -m pip install .
```

The adapter requires `mcp==1.30.0`, `segno>=1.6,<2`, and `psutil>=7,<8`. The default project-local OMP installer and `tools/ui-design` wrapper remain standard-library-only.

### Install once for all projects

From the distribution directory, install the optional user-global runtime.

```bash
bash ./install.sh --mcp-global
```

This creates an isolated environment at `~/.local/share/ui-design-studio/mcp` and exposes `ui-design` and `ui-design-mcp` in `~/.local/bin`. Add `~/.local/bin` to your shell's `PATH` if needed. OMP also checks the fixed environment path, so shell PATH changes are not required for automatic startup.

The global option installs only the MCP runtime. Install the OMP skills and extension into each target project with the normal `--project` command. No system Python packages, client configuration, or OS service is installed. Package installation requires access to its Python dependencies.

Use the same global `ui-design-mcp` executable for every project, with a separate explicit `--repo /absolute/project/path` for each connection. Project records and permissions stay separate.

## Configure a connection

Add this executable and argument contract to your client's MCP configuration.

```json
{
  "command": "/absolute/path/to/ui-design-env/bin/ui-design-mcp",
  "args": ["--repo", "/absolute/path/to/project"]
}
```

This object is a server entry, not a universal top-level client configuration format. The adapter never edits your client configuration. Give every process one explicit absolute project path. It never infers the project from a GUI client's working directory.

Initialization starts an authenticated landing dashboard before any design run exists. It does not open a browser or create a pending dossier. Read `ui-design://dashboard` or call `ui_design_dashboard_info` for the connection URLs. Call `ui_design_start_run` to create a run. Call `ui_design_resume_run` to open an existing repository-relative run path.

The server supplies deterministic operations and instructions, not an autonomous design model. Your client supplies authorized file editing, browsers, models, and subagents. Without subagents, record sequential role passes. Missing model identity or required evidence remains a blocker. Existing evidence and registration gates do not change.

`ui_design_status` remains the full compatibility snapshot. Use `ui_design_status_compact` for bounded gate, count, worker and blocker metadata. Use `ui_design_status_page` with `collection="artworks"` or `"evidence"`, a page size from 1 to 100, and the returned revision-bound cursor for detail. Full detail remains reachable; compact status does not include artwork bodies or evidence records.

`ui_design_resume_check` reports changed manifest dependencies and transitive stale nodes. A missing manifest blocks conservatively. `ui_design_worker_packet` generates one selected-role packet with exact owned-file hashes, original instructions, scope, acceptance gates and reviewer independence. These tools do not execute workers or claim model observation.

## Print a verified address and QR code

```bash
/absolute/path/to/ui-design-env/bin/ui-design dashboard-info --repo /absolute/path/to/project
/absolute/path/to/ui-design-env/bin/ui-design dashboard-info --repo /absolute/path/to/project --session INSTANCE_ID
/absolute/path/to/ui-design-env/bin/ui-design dashboard-info --repo /absolute/path/to/project --run docs/design/runs/RUN_ID --json
```

The command is read-only. It verifies identity through a bounded authenticated loopback probe before printing `[ok]`. With several live connections, select one explicitly. The output contains the real loopback URL, each available LAN URL, and a locally generated Unicode half-block QR code. The QR encodes the first LAN URL, or loopback when LAN is unavailable. Keep the `#token=` fragment. No URL is sent to an external QR service.

## Start a dashboard without an MCP connection

The global runtime provides a foreground dashboard command.

```bash
ui-design dashboard-serve --repo /absolute/path/to/project
```

It starts before a design run exists, discovers actual LAN addresses, and prints labelled URLs followed by a real QR code. The first line ends with `(Ctrl-C to stop)`. Keep that terminal open. Add `--dashboard-host 127.0.0.1` for loopback-only access.

This command differs from the low-level project wrapper's `design-serve RUN`, which requires an existing run and prints JSON readiness.

## Use automatic startup in OMP

Install the global runtime once, then install or update the project's OMP extension. A main OMP session starts its own dashboard automatically and prints verified links and the QR before work. No MCP connection or manual server command is required.

The extension keeps its child alive through work and guided approval pauses. Unexpected child exits trigger automatic recovery. It closes its owned child on session shutdown or project change. It does not install a daemon that runs after OMP exits.

Use these commands in OMP.

```text
/ui-design-dashboard
/ui-design-dashboard stop
/ui-design-dashboard start
```

The first command prints the live links again. An explicit stop inhibits automatic restart until you request start. OMP's banner names `/ui-design-dashboard stop` rather than promising that an OMP Ctrl-C stops only the dashboard. URLs retain the authentication fragment; do not shorten them before sharing with an authorized reviewer.

## Choose network exposure

The default `--dashboard-host 0.0.0.0` permits trusted-LAN access. HTTP does not encrypt bearer credentials or project content. Use only trusted networks. To disable LAN exposure, add `--dashboard-host 127.0.0.1` to the server arguments.

`--dashboard-port` accepts 0 through 65535 and defaults to an ephemeral port. An occupied explicit port fails. `--lan-address ADDRESS` selects an IPv4 address from an active local interface. The adapter never guesses an address, opens a tunnel, or edits a firewall. Address changes refresh advertised URLs and allowed origins. Existing CLI servers keep their owner's configured exposure when reused.

The landing page lists recorded runs and opens the existing direct run dashboard. Guided approvals remain browser actions bound to reviewed input digests. No MCP tool submits human approval.

## Understand ownership and cleanup

Each connection has its own landing instance and private record under `.ui-design-studio/runtime/mcp/`. Records are private capabilities, not evidence. Do not commit them. Dead records are ignored after identity probes and never treated as proof of liveness.

Connections reuse a live run server only after its run and instance identity match. Disconnecting closes only owned run servers and that connection's landing listener. Borrowed run servers belong to their original owner. A stopped run stays in the dossier list without a live link. Resume explicitly to start it again. Evidence directories and coordination locks remain intact.

On Unix, SIGTERM requests lifespan cleanup. On Windows, close stdio normally for graceful cleanup. Python's Windows event loop does not provide Unix signal handlers. Native Windows execution remains unverified.

OMP installations retain `/ui-design-progress RUN` and their Pi Tasks ownership checks. `/ui-design-dashboard SESSION_ID` can still select an existing MCP connection. Waiting connections never receive Pi Tasks exports. Other clients receive links through tools and resources, not an invented pinned-widget protocol.

## Read workflow guides

Fetch `ui_design_workflow` with `intent` equal to `guided`, `yolo`, `assess-only`, or `resume`. Resume requires `run`. Prompt retrieval does not start work. A tool-only client can call `ui_design_read_guide` with `skills/ui-design-studio/SKILL.md`, a bundled skill reference path, or an `agents/ui-*.md` role name.

OMP slash commands, `/goal`, `/vibe`, Pi Tasks events, and model-routing apply/restore helpers remain OMP-only. The MCP adapter guide maps engine command examples to typed tools while preserving the original design phases and evidence requirements.

Only local stdio MCP is supported. There is no remote HTTP MCP service. Client-specific configuration, other native MCP clients, and other operating systems require their own verification.
