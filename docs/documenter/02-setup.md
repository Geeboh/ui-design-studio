# Setup

## Requirements

The source establishes Python 3.10 or newer. The shell installer also requires python3 with the venv module. Installation is designed to work from the extracted release without changing OMP global configuration.

## Project-local installation

Run from the extracted package:

    bash install.sh --project /absolute/path/to/project

The bootstrap creates a temporary venv without pip. scripts/install.py installs managed skills, agents, commands, the optional extension, documentation, prompts, the wrapper, and a default ui-design-studio.json when absent.

The installer refuses package paths inside the target project, symlinked managed paths, incomplete project venvs, edited managed files, and conflicting unmanaged files. It writes changes atomically, records a backup manifest, and can restore a completed installation.

Useful forms:

    bash install.sh --project /absolute/path/to/project --dry-run
    bash install.sh --project /absolute/path/to/project --update
    bash install.sh --project /absolute/path/to/project --restore BACKUP_ID

## User-global MCP installation

    bash install.sh --mcp-global

The global installer owns ~/.local/share/ui-design-studio/mcp and links ui-design and ui-design-mcp into ~/.local/bin. It validates the ownership marker and refuses unrelated executables or symlinked environment paths. It does not modify project files or MCP client configuration.

Select a project explicitly:

    ui-design-mcp --repo /absolute/path/to/project

The project installer prints the next checks: ./tools/ui-design doctor --repo ., OMP plugin reload, and /skill:ui-design-studio mode=guided. This review did not execute them.

Sources: install.sh:1-24, scripts/install.py:141-153,243-307,339-452,455-563, scripts/install_mcp.py:75-151, docs/INSTALLATION.md, docs/MCP.md.
