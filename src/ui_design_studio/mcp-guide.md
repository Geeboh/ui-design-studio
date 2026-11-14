# Use UI Design Studio through MCP

The MCP server supplies workflow instructions, an authenticated dashboard, and deterministic engine operations. It does not supply a design model, native file editing, browser access, models, or subagents. Use your coding client's authorized capabilities for those tasks.

## Start and resume

Read `ui-design://dashboard` or call `ui_design_dashboard_info` for this connection's landing dashboard. Connecting starts that listener without creating a design run. Call `ui_design_start_run(theme_id=..., mode="guided", theme_action="auto", models=None)` to create a pending dossier. Call `ui_design_resume_run(run="docs/design/runs/...")` to resume an existing dossier. All tool paths are repository-relative. The server's explicit `--repo` fixes the project boundary.

If initialization creates a run but dashboard opening fails, keep the returned run path. Resume that run instead of creating another dossier.

## Map CLI examples to tools

Replace `tools/ui-design <command>` with `ui_design_<command_with_underscores>`. Omit `--repo`; the connection supplies it. Use named arguments and repository-relative paths. `init-run` maps to `ui_design_start_run`. `design-serve` maps to `ui_design_resume_run`. `status` is one-shot. `progress` uses `next_action` and `blocker`. `worker` keeps `id`, `task`, `status`, `message`, and optional `model`. `artwork` keeps `run`, `file`, `context`, and optional `title`. `approval-request` publishes a review request; it never grants a human approval.
Use `ui_design_status_compact` for bounded metadata and `ui_design_status_page` for revision-bound artwork/evidence detail. Use `ui_design_resume_check(path=...)` before continuing work. Use `ui_design_worker_packet(path=..., role=..., objective=..., owned=[...])` to generate a bounded role context; it requires original instructions and never claims worker execution.

All nested path arguments are also repository-relative. For `approval-request`, prefix each `files` entry and `choices` with the run path. For `artwork`, supply a file under that run or its verified active theme. The adapter validates those paths and converts them to the engine's internal relative form.

The separate installed CLI prints verified URLs and a local terminal QR code with `ui-design dashboard-info --repo /absolute/project`. When several connections exist, choose `--session INSTANCE_ID`. Use `--run docs/design/runs/RUN_ID` for a particular run. The command does not start a listener.

## Read authoritative guides

Call `ui_design_read_guide(name="skills/ui-design-studio/SKILL.md")` or read `ui-design://guide/skills/ui-design-studio/SKILL.md`. Relative skill links map to their payload-relative guide names. For example, `references/workflow.md` in the studio skill becomes `skills/ui-design-studio/references/workflow.md`. Role briefs use `agents/<role>.md`. Only the nine bundled skills, their reference files, and seven role briefs are available.

The original guides remain authoritative for design phases, coverage, approvals, evidence, and registration gates. Their OMP host operations are not portable. OMP slash commands, `/goal`, `/vibe`, Pi Tasks events, `models-apply`, `models-restore`, and native model routing are OMP-only. Do not execute them in another client or claim that MCP installs them.

## Preserve evidence and human decisions

A client without subagents performs and records separate sequential role passes. Record actual available model identities and thinking settings. Missing identity or required evidence remains a blocker. Never fabricate model routing, independent review, approval, progress percentages, or a passing `check-run` result.

Guided approval occurs in the authenticated browser dashboard. No MCP tool submits approval. Native editing and browser verification remain client responsibilities. Prompt retrieval only returns instructions and never starts a run.

## Connection and network boundaries

Each MCP process owns its landing dashboard and only the run servers it starts. Reused run servers belong to another connection. Disconnecting never stops a borrowed server. Run URLs may change after their owner exits. Explicit resume can start a stopped run.

The default dashboard host is `0.0.0.0` for trusted-LAN access. Bearer fragments protect access, not network confidentiality. HTTP exposes credentials and content to network observers. Use `--dashboard-host 127.0.0.1` to opt out of LAN exposure. Do not share tokenized URLs beyond trusted recipients. MCP itself uses local stdio only.
