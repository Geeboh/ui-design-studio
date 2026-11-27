# PRISM Studio 2.0.2

PRISM Studio 2.0.2 adds global dashboard LAN policy and OMP controls.

## Changes

- Global LAN access is enabled by default with automatic active-interface IPv4 discovery.
- `bash install.sh --mcp-global --no-lan` selects loopback-only operation.
- `--lan-address auto|IPv4` selects automatic or explicit advertised interface selection.
- `/ui-design-dashboard lan status|on|off|auto|IPv4` changes the global setting from OMP.
- Global settings live at `${XDG_CONFIG_HOME:-~/.config}/ui-design-studio/config.json`.
- Malformed global settings fail closed instead of silently exposing LAN access.
- LAN changes restart only dashboards owned by the current OMP session.

LAN mode exposes bearer-token HTTP URLs and project content. Use it only on a trusted network. MCP transport remains local stdio.
