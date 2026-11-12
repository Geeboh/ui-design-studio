# Multi-agent direction and review

Use this reference throughout `ui-design-studio`. The director maintains one brief, inventory, theme contract, decision log and run state under `docs/design/runs/<id>/`. The specialist skills are `ui-assess`, `ui-plan`, `ui-design`, `ui-produce`, `ui-review`, `ui-finalize`, `ui-theme` and `ui-yolo`.

## Assign the right owner

| Native agent | Primary assignment |
| --- | --- |
| `ui-ux-researcher` | Evidence-based assessment, task journeys, inventory and user questions. |
| `ui-art-director` | Comparable concept directions, visual coherence and design critique. |
| `ui-page-designer` | Complete page/dialog mockups using the frozen system. |
| `ui-theme-engineer` | Tokens, theme contract, adapter and shared primitives. |
| `ui-implementer` | Bounded page/component implementation and local checks. |
| `ui-quality-reviewer` | Independent interaction, accessibility, coverage and visual review. |
| `ui-performance-reviewer` | Payload, runtime and offline verification with reproducible conditions. |

Discover available agent tools, execution modes and capacity. Resolve the run's `auto-models` (default) or `current-model` policy through [model-routing.md](model-routing.md); verify each specialist's effective assignment rather than assuming it inherited the director's model. Keep reviewer independence even when author and reviewer use the same model; independence comes from a separate task and assessment, not a different model label. Use independent workers concurrently when supported. Default to a small number of active lanes appropriate to the environment; more workers are not automatically faster. If subagents are unavailable, perform roles sequentially and disclose the reduced independence. Do not claim that separate agents reviewed work when they did not.

Keep one owner of orchestration. Preserve existing extension settings; an already enabled pstack may provide an additional focused quality check, but is not a Studio dependency. Do not duplicate Studio's concept/design/review stages with a second agent pipeline or automatically enable the full Poteto workflow.

## Send complete task contracts

OMP workers do not inherit the director's complete context or `AGENTS.md` automatically. Every assignment must explicitly provide:

- Objective and phase; relevant user choices and yolo/guided mode.
- Repository/worktree and exact instructions files to read, with essential constraints summarized.
- Source-labelled project context, brief, inventory IDs, approved tokens/components and design-contract revision.
- Model policy and verified assignment, with any availability or routing limitations.
- Owned output paths and files; shared files the worker must not edit.
- Required artifacts, acceptance checks, evidence format and completion condition.
- Applicable project restrictions, offline/performance budgets and known uncertainties.
- Dependencies, integration owner and what to report if blocked.

Have the worker report changed paths, design decisions, checks actually run, evidence, unresolved issues and integration needs. Workers may propose shared-contract changes; only the designated owner applies them.

## Sequence the collaboration

During assessment, parallelize task/interaction review and technical accessibility/performance discovery. Merge duplicate findings and reconcile disagreements against evidence.

During Plan, assign distinct visual directions using identical representative content. Have a critic compare them with the agreed rubric. The director selects or synthesizes one direction after guided input or a recorded yolo decision.

During Design, freeze the shared system, then split page families. Review cross-page consistency and complete coverage before implementation. A new shared pattern returns to the theme owner; it should not become an uncoordinated local invention.

During Produce, establish tokens, adapter and common components first. Allocate non-overlapping files or isolated worktrees. Integrate in dependency order and run checks on the combined result. Never let multiple workers overwrite the same stylesheet, registry or router.

During review, assign an agent who did not author the relevant work. Give the reviewer the requirement, raw artifact/diff and evidence; avoid supplying the author's desired verdict. Resolve disagreements through reproduction, specification and user intent. The director owns final acceptance and cannot substitute confidence for a failed required check.

## Continue and recover

Checkpoint decisions, artifact paths, ownership and next actions after each phase or substantial integration. If temporary model routing was applied with `models-apply`, finish or park dependent workers and run `models-restore` before user handover, a guided pause or a package update. Follow `model-routing.md` for conflict handling, resume/reapply and refreshing evidence before final acceptance. Approval records identify `user` versus `agent-yolo`, the selected artifact/revision and rationale. Changed inputs invalidate affected downstream approval and evidence.

A polling timeout is not evidence that a worker failed. Check its status, recent progress and artifacts before restarting it. Avoid duplicate workers writing the same outputs. If a lane is blocked, continue independent work and record the precise missing input. Do not repeatedly solicit human confirmation for routine work already authorized.

Use `tools/ui-design` according to its documented commands to inspect/check package state. The helper is not an agent scheduler and does not replace project tests. Finish with one integrated report; do not hand the user a collection of conflicting worker summaries.
