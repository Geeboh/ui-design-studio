# PRISM Studio 2.0.1

PRISM Studio 2.0.1 fixes project installation on filesystems where per-file metadata synchronization stalls and adds safe cleanup for projects that use only the universal MCP runtime.

## Changes

- Project installer uses data-only synchronization where supported, avoiding unnecessary metadata sync cost for every file.
- `ui-design cleanup-project` removes installer-owned project payload, venv and install state while preserving MCP runtime data, design runs, evidence, themes and project policy.
- Global dashboard LAN policy is enabled by default with automatic interface discovery. Installer switches and `/ui-design-dashboard lan ...` controls change the global setting.
- Installation and MCP documentation now describe universal-MCP-only cleanup.

## Usage

```bash
ui-design cleanup-project --repo /absolute/path/to/project --dry-run
ui-design cleanup-project --repo /absolute/path/to/project --yes
```

The command does not stop or remove the universal runtime under `~/.local/share/ui-design-studio/mcp`.
