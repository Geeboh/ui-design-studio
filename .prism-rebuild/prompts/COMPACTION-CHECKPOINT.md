# Preserve a compact PRISM continuation record

Before compaction or deliberate handover, update on-disk progress, decisions, work orders, blockers and operation receipts. Record only information needed to continue correctly:

- Repository/worktree/branch and source fingerprint.
- Current milestone, completed acceptance IDs and evidence paths.
- Active worker ownership, dependencies and integration state.
- Exact accepted design/artifact versions and relevant constraints.
- Effective model policy and observed assignments.
- Design reservations, uncertain provider outcomes and reconciliation actions.
- Unresolved findings, failed commands and exact next actions.
- Publication authority and any user scope changes.

Preserve full relevant logs privately and summarize their findings. Do not paste whole books, source files or tool transcripts into the checkpoint. On resume, compare relevant current inputs before relying on recorded applicability; unrelated progress is not a reason to repeat all work.
