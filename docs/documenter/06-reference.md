# Reference

## Console entrypoints

| Command | Source target |
| --- | --- |
| ui-design-mcp | ui_design_studio.cli:mcp_main |
| ui-design | ui_design_studio.cli:main |
| tools/ui-design | Project-local .venv-ui-design/bin/python plus studio.py |
| install.sh | Temporary bootstrap venv plus installer dispatch |

The Python CLI and MCP command accept an explicit project boundary. Existing MCP documentation describes local stdio operation and trusted-LAN dashboard access; it does not authorize production exposure.

## OMP commands

- /ui-design starts the guided lifecycle.
- /ui-yolo starts autonomous design mode.
- /ui-design-progress [RUN|auto] pins or discovers a design run.
- /ui-design-dashboard [start|stop|SESSION_ID] manages or selects a verified dashboard connection.

## Source interfaces

The Python source contains CLI dispatch, configuration loading, run record/status validation, evidence hashing, design-server HTTP handlers, MCP resources/tools, and theme handling. The TypeScript extension contains host-context validation, dashboard supervision, connection verification, path confinement, status rendering, and Pi Tasks export.

The repository declares seven specialist agent roles and nine UI skills. Agent contracts define ownership and review expectations; they are not evidence that an agent or provider was run.

## Run artifacts

Run directories may contain run.json, locator and status files, evidence records, artwork, approvals, logs, locks, and theme sources. The exact accepted schema is implemented by the runtime and documented by references/run-records.md.

Sources: pyproject.toml, .omp/commands/, .omp/extensions/ui-design-progress.ts, src/ui_design_studio/, references/run-records.md, release.json.
