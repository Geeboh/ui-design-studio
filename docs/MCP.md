# Connect UI Design Studio through local MCP

Use the Python package when your local coding client supports MCP stdio. The package bundles the existing engine, nine skill guides, seven role briefs, dashboard assets, schemas, and specimen theme. No project-local OMP installation is required.

## Install the adapter

Require Python 3.10 or later. From the distribution directory, run these commands.

```bash
python3 -m venv /absolute/path/to/ui-design-env
/absolute/path/to/ui-design-env/bin/python -m pip install .
```

The adapter requires `mcp==1.30.0`, `segno>=1.6,<2`, and `psutil>=7,<8`. The existing `install.sh` OMP installer and `tools/ui-design` wrapper remain standard-library-only.

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

## Print a verified address and QR code

```bash
/absolute/path/to/ui-design-env/bin/ui-design dashboard-info --repo /absolute/path/to/project
/absolute/path/to/ui-design-env/bin/ui-design dashboard-info --repo /absolute/path/to/project --session INSTANCE_ID
/absolute/path/to/ui-design-env/bin/ui-design dashboard-info --repo /absolute/path/to/project --run docs/design/runs/RUN_ID --json
```

The command is read-only. It verifies identity through a bounded authenticated loopback probe before printing `[ok]`. With several live connections, select one explicitly. The output contains the real loopback URL, each available LAN URL, and a locally generated Unicode half-block QR code. The QR encodes the first LAN URL, or loopback when LAN is unavailable. Keep the `#token=` fragment. No URL is sent to an external QR service.

## Choose network exposure

The default `--dashboard-host 0.0.0.0` permits trusted-LAN access. HTTP does not encrypt bearer credentials or project content. Use only trusted networks. To disable LAN exposure, add `--dashboard-host 127.0.0.1` to the server arguments.

`--dashboard-port` accepts 0 through 65535 and defaults to an ephemeral port. An occupied explicit port fails. `--lan-address ADDRESS` selects an IPv4 address from an active local interface. The adapter never guesses an address, opens a tunnel, or edits a firewall. Address changes refresh advertised URLs and allowed origins. Existing CLI servers keep their owner's configured exposure when reused.

The landing page lists recorded runs and opens the existing direct run dashboard. Guided approvals remain browser actions bound to reviewed input digests. No MCP tool submits human approval.

## Understand ownership and cleanup

Each connection has its own landing instance and private record under `.ui-design-studio/runtime/mcp/`. Records are private capabilities, not evidence. Do not commit them. Dead records are ignored after identity probes and never treated as proof of liveness.

Connections reuse a live run server only after its run and instance identity match. Disconnecting closes only owned run servers and that connection's landing listener. Borrowed run servers belong to their original owner. A stopped run stays in the dossier list without a live link. Resume explicitly to start it again. Evidence directories and coordination locks remain intact.

On Unix, SIGTERM requests lifespan cleanup. On Windows, close stdio normally for graceful cleanup. Python's Windows event loop does not provide Unix signal handlers. Native Windows execution remains unverified.

OMP installations retain `/ui-design-progress RUN` and their Pi Tasks ownership checks. `/ui-design-dashboard [SESSION_ID]` selects a connection, pins its addresses, and prints full verified output with the QR. Waiting connections never receive Pi Tasks exports. Other clients receive links through tools and resources, not an invented pinned-widget protocol.

## Read workflow guides

Fetch `ui_design_workflow` with `intent` equal to `guided`, `yolo`, `assess-only`, or `resume`. Resume requires `run`. Prompt retrieval does not start work. A tool-only client can call `ui_design_read_guide` with `skills/ui-design-studio/SKILL.md`, a bundled skill reference path, or an `agents/ui-*.md` role name.

OMP slash commands, `/goal`, `/vibe`, Pi Tasks events, and model-routing apply/restore helpers remain OMP-only. The MCP adapter guide maps engine command examples to typed tools while preserving the original design phases and evidence requirements.

Only local stdio MCP is supported. There is no remote HTTP MCP service. Client-specific configuration, other native MCP clients, and other operating systems require their own verification.
