# Overview

## Purpose

UI Design Studio is an OMP workflow package for UI assessment, planning, design, production, review, finalization, and theme work. It includes OMP skills, specialist agent contracts, commands, a progress extension, a Python runtime, dashboard assets, documentation, and release tooling.

The package metadata names distribution ui-design-studio-mcp, version 1.4.3, Python >=3.10, and MIT licensing. Runtime dependencies are declared in pyproject.toml: mcp==1.30.0, segno>=1.6,<2, and psutil>=7,<8.

## Package surfaces

| Surface | Responsibility |
| --- | --- |
| OMP skills | Phase behavior, gates, prompts, and lifecycle routing. |
| Agents and commands | Specialist ownership plus guided and autonomous entrypoints. |
| Python runtime | CLI, MCP server, design server, run records, status, and validation. |
| Dashboard | Local/browser progress, artwork, evidence, approvals, and run selection. |
| Extension | Session-aware dashboard supervision and Pi Tasks export. |
| Theme module | Web CSS/SVG packaging contract and native adapter boundary. |
| Release tools | Offline installation, checksums, reproducible ZIP creation, and restore. |

## Declared entrypoints

- ui-design-mcp calls ui_design_studio.cli:mcp_main.
- ui-design calls ui_design_studio.cli:main.
- tools/ui-design selects the project-local venv and runs studio.py.
- install.sh bootstraps a temporary venv, then dispatches project or global MCP installation.

The repository supplies workflow and tooling contracts. It does not contain the recipient application's UI. Native rendering requires an application-specific adapter, and browser/device validation requires a reachable runtime.

Sources: pyproject.toml:1-80, release.json, README.md, .omp/skills/ui-design-studio/SKILL.md, tools/ui-design:1-13.
