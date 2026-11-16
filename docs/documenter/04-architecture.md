# Architecture

## Component relationships

OMP host loads skills, agents, commands, and the progress extension. The extension supervises the Python runtime. The runtime owns the design server, MCP server, run directory, status, evidence, artwork, approvals, and dashboard connection. Theme modules feed the runtime's theme validation and packaging paths.

## Runtime path

A normal project installation creates a project-local .venv-ui-design and installs managed package files. tools/ui-design executes studio.py through that venv. CLI commands select a project boundary, create or resume a run, and write records under configured paths. The dashboard reads a verified local connection and run data.

## Extension path

ui-design-progress.ts binds only to documented host contexts. It tracks one non-sub-agent session, confines run selection to paths.runs, probes dashboard identity with bearer authentication, rejects mismatched instances, limits readiness output, redacts diagnostics, caps recovery, and exports Pi Tasks data only when session, project, run, and director identity match.

## Theme path

Web themes are packageable CSS/SVG modules. Native surfaces require an application-specific adapter and equivalent token mapping. The theme reference forbids remote assets and unsafe path/symlink behavior.

Sources: .omp/skills/ui-design-studio/SKILL.md, .omp/extensions/ui-design-progress.ts:521-1229, .omp/skills/ui-design-studio/scripts/studio.py, design_server.py, references/theme-module.md.
