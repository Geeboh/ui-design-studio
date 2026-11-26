# PRISM Studio rebuild pack conventions

Pack version: 1.0.0. Target product: UI Design Studio 2.0.0, working name PRISM Studio.
Prepared: 2026-11-26 (Australia/Hobart). Reviewed baseline: `60307ef31fd6e2bad1d39620fc507b0b822e281a`, UI Design Studio 1.4.3.

This pack is an implementation handoff, not a rebuilt application. Pack integrity, implementation tests, host integration, and human validation are separate claims. Human participant testing is deferred by project policy; automated interaction/accessibility verification remains required for the web release.

## Architecture decisions

- Preserve one authoritative Python engine and transport adapters for CLI, MCP and the authenticated dashboard. Retain existing public package/CLI/skill aliases through a documented transition. Avoid a new frontend framework without a measured reason.
- Use a transactional SQLite state store on a documented local single-host state path, with immutable content-addressed artifact blobs and portable JSON export. Do not put WAL on a network filesystem. Migration is copy-first, backed up, repeatable and reversible; never silently manufacture approvals or budget records from incomplete legacy data.
- Use a small domain core, shared command handlers, typed contracts, expected revisions, dependency-scoped approvals, idempotent operations, outbox/event receipts and rebuildable read projections. No Kafka/microservices prerequisite.
- Monetary budget applies to DESIGN work (concepts, mockups, artwork, design revisions, critique when configured); implementation/pack-building spend is separately tracked and excluded by default. Currency is explicit. Unknown cost is unknown, never zero. Hard enforcement requires controlled dispatch and a bounded charge; otherwise label advisory enforcement.
- Model policy precedence: explicit invocation override; persisted run settings on resume; project defaults; personal defaults; capability/cost-based auto selection. Preserve current-model mode and report actual observed assignments. Do not hardcode price tables or assume new model IDs exist.
- Guided design decisions require the relevant user decision; YOLO may record agent design decisions within scope and budget. Neither mode expands tool permissions or publication authority. Continue routine authorized work autonomously. Human research is deferred, not fabricated as passed.
- Focused revision pins the exact base artifact and annotations. Decompose-and-re-request creates stable component IDs, a dependency graph and batch decisions; preserve accepted independent components.
- Installation, local MCP, OMP discovery, theme lifecycle, package parity, upgrade/restore and current security boundaries remain first-class product capabilities.

## Pack interfaces

- `tools/verify-pack.py --root PATH`: verify this handoff's hashes, references, schemas and traceability. Its PASS never means the product is complete.
- `tools/prepare-worktree.py --repo PATH --dest PATH [--base REF] [--branch NAME]`: create an isolated branch/worktree and copy this pack to `.prism-rebuild`. Never reset/stash/clean the source checkout. Defaults: base HEAD; branch `overhaul/prism-v2`.
- `tools/install-rebuild-context.py --repo PATH`: install/restore a narrowly scoped rebuild context with an auditable receipt, preserve existing instructions and reject overwrite conflicts.
- `tools/preflight.py --repo PATH [--json]`: report Git, Python, Node, OMP/tool capability and browser prerequisites without installing anything or exposing secrets.
- `tools/run-gates.py --repo PATH --plan PATH --profile NAME`: execute reviewed gate command arrays and record observations under `.prism-state/evidence/`; missing commands or required gates do not pass.
- `tools/status.py --repo PATH`: report milestone/acceptance state from `.prism-state/`, distinguish unknown/deferred/failed/passed.
- `tools/build-pack.py --root PATH --output PATH`: build a deterministic source archive excluding scratch, private state and uploaded source books.

## Naming and references

- Requirements: `REQ-<FAMILY>-NNN`; acceptance cases: `AC-<FAMILY>-NNN`; milestones: M0–M8; gates: G0–G8.
- Families: CORE, APPROVAL, REVISION, BUDGET, MODEL, WORKER, UX, A11Y, PERF, INSTALL, SECURITY, DOCS, MIGRATION, KNOWLEDGE, THEME, EVIDENCE.
- QA author owns `contracts/requirements.json`, `contracts/acceptance-cases.json`, `contracts/milestones.json`, `contracts/gates.json` and `config/verification-plan.example.json`.
- Architecture author owns `contracts/domain.schema.json`, `contracts/command-catalog.json`, domain/architecture/migration docs.
- Product author owns product/UX/accessibility/skills docs, original knowledge rules/source catalog, project-owned `.md.in` skill blueprints. These are external OMP templates, not personal ChatGPT skill installations.
- Root owns scripts, README/START-HERE/AGENTS, prompts, model/tool guidance, baseline findings, validation receipts and packaging.
- All documents are original synthesis. Cite source title/edition/PDF page or stable URL. Do not include the supplied PDFs, copied chapter text, or large website extracts. State factual uncertainty and distinguish source advice, project policy, and proposed behavior.
- Paths in documents are relative to the pack unless clearly marked as target repository paths. Use portable Markdown links. Use JSON for machine contracts; runtime configuration examples are proposed and must not be mistaken for existing OMP syntax.
- Shared manifests/hashes are generated only after authors finish. Do not modify other authors' files without coordination.
