# Model routing

Status: `PENDING_OBSERVATION` for specialist execution; no model override was applied.

## Runtime discovery

- OMP: `18.20.3`.
- `modelRoles`: `smol=openai-codex/gpt-5.6-luna:auto`, `plan=openai-codex/gpt-6-astra:auto`, `vision=openai-codex/gpt-5.6-luna:auto`, `designer=litellm-local/designer`, `task=openai-codex/gpt-6-luna:auto`, `slow=openai-codex/gpt-6-luna:auto`, `commit=openai-codex/gpt-5.6-luna:off`, `default=openai-codex/gpt-5.6-luna`.
- `task.agentModelOverrides`: `{}`.
- `task.agentPrewalk`: `{}`.
- Catalog exposed usable selectors for `openai-codex/gpt-5.6-luna`, `openai-codex/gpt-5.6-sol`, `openai-codex/gpt-6-astra`, and local specialist aliases. Catalog availability does not prove credentials or live capacity.

## Actual work

- Parent session model: `openai-codex/gpt-5.6-luna` from the active runtime context. Effective thinking setting was not exposed by a read-only runtime command.
- Four bounded read-only `scout` audits were dispatched: core integrity, package/security, browser behavior, and evidence. Their resolved provider/model identities were not returned by the task interface, so no model compliance claim is made.
- No `models-apply`, global configuration edit, provider call, or temporary agent-file mutation occurred.

## Limitation

This record is not a resolved per-worker routing record. A future Studio run must populate its own `run.json` and `model-routing.md` from observed task metadata, then digest the record before final acceptance.
