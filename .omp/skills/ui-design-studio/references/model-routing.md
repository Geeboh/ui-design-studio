# Model selection and routing

## Contents

1. Policy and scope
2. Discover the real environment
3. Select an automatic assignment
4. Use the current model throughout
5. Apply and verify native routing
6. Record, resume and restore
7. Limits and sources

## 1. Policy and scope

Resolve the policy from the explicit invocation, then the existing run when resuming, then `ui-design-studio.json` → `modelPolicy`, then `auto-models`. Accept `models=auto-models` and `models=current-model` as skill instructions. Bare `auto-models` and `current-model` are equivalent when unambiguous. These are not native OMP command-line flags. Do not confuse the helper's `--models` policy option with OMP's own `--models` model-list flag.

| Policy | Behaviour |
| --- | --- |
| `auto-models` (default) | Choose suitable available models and reasoning levels for the seven specialist roles. Respect existing operator routing, provider restrictions, budgets and actual task difficulty. Use the active model when it is suitable or no better eligible alternative is established. |
| `current-model` | Observe the active session's exact provider/model and effective thinking setting; assign that same model and setting to all seven specialists. Recheck the snapshot when resuming or after a deliberate session model change. |

The main session remains the director on its currently selected model. This skill does not silently switch the main session, sign in to providers, install models, purchase capacity or change approval settings. The user can choose the main model with OMP's `/model` interface. Model policy controls specialist routing; guided/yolo controls design decisions; `/goal` controls continuation. Keep those choices independent.

This policy covers the seven UI specialists' main task requests. It does not claim to control OMP's separate compaction, title, embedding, search, image-generation or advisor calls. One model can perform every role in separate tasks; reviewer independence does not require a second model brand.

## 2. Discover the real environment

Do this before dispatching the first specialist, in the actual target project and the same OMP environment as the active session:

1. Read the active session's provider/model, thinking setting, task tool schema and available agent roster. Do not infer the active model from a saved default.
2. Inspect `omp --version`, `omp models --help` and `omp models --json` when the CLI is available. Current OMP exposes provider, ID, selector, limits, reasoning/thinking metadata, declared input and cost. Catalog membership alone does not prove usable credentials, live capacity, permission or effective image support. The native selector and an actual task response establish those facts more directly.
3. Inspect only relevant settings, using read-only operations such as `omp config get modelRoles --json`, `omp config get task.agentModelOverrides --json`, `omp config get task.agentPrewalk --json`, and the live runtime's restrictions. Avoid dumping provider credentials or the entire settings store into the run dossier.
4. Account for session-only selections, launch overlays, model restrictions, account pools, fallback, prewalk and extension hooks. A fresh CLI subprocess cannot observe every live session override. If a command/key differs in the installed version, inspect its help/live schema instead of guessing or changing the installation.
5. Record the observed candidates and constraints in `model-routing.md`. Keep a concise redacted catalog excerpt if useful. State when price, capacity or capabilities are unknown. Do not use catalog price zero as evidence that a route is free.

Native task resolution normally gives an existing `task.agentModelOverrides[agentName]` priority over agent frontmatter, followed by the parent's active/default model. Per-call model selection has its own operator-controlled gate. Inspect the current task schema and use it only if already available and authorized. Never enable `task.perCallModel`, broaden a model allowlist, rename a specialist to evade an override, or edit a permission policy merely to make a chosen route work.

## 3. Select an automatic assignment

Choose from currently usable, permitted routes; do not ship or invent a fixed vendor/model list. Prefer the user's explicit preferences and established role mappings when they satisfy the task. Evaluate capability first, then expected total cost and latency, including retries and review. Explain each assignment briefly.

| Specialist | Selection criteria |
| --- | --- |
| `ui-ux-researcher` | Strong task reasoning, source discipline and human-interaction judgement; effective image input when inspecting captures. |
| `ui-art-director` | Strong visual judgement, reference interpretation, coherent concept development and critical comparison. |
| `ui-page-designer` | Reliable layout and component reasoning, screenshot understanding where needed, and accurate implementation-ready mockups. |
| `ui-theme-engineer` | Strong frontend/native-stack engineering, token architecture, accessibility and integration reasoning. |
| `ui-implementer` | Reliable coding and tool use for the actual stack; use stronger reasoning for structural or risky integration, lighter effort for bounded repeated edits. |
| `ui-quality-reviewer` | Independent critical judgement, interaction/accessibility review and evidence checking. Do not choose a weak reviewer solely to save tokens. |
| `ui-performance-reviewer` | Reliable measurement, debugging, dependency/payload reasoning and offline/runtime verification. |

Use the smallest capable model for genuinely mechanical assignments when it reduces total work. Use a capable design/review model for ambiguous decisions. If metadata is insufficient to rank alternatives, retain the known-working current model and record that fallback; do not invent benchmark rankings. A one-model environment is supported.

When reference images or rendered results matter, confirm the route actually receives images. A model's declared `input` field may differ from its transport's effective behaviour. If no permitted model can inspect a required visual, record that limitation; do not claim visual acceptance from a text-only read.

Select supported reasoning levels. Different model families expose different effort ladders. `provider-default` means no explicit thinking override for a model without a relevant controllable setting; it is not a claim that hidden reasoning is disabled. Do not use a coarse task `effort` hint that changes an already-recorded exact thinking selection without updating and verifying the assignment.

## 4. Use the current model throughout

Snapshot the active main session at the start/resumption of the run. Write its exact provider/model identity into `modelRouting.sessionModel` and its effective thinking setting into `sessionThinking`. Use that identity and setting in every assignment.

Do not substitute a cheaper worker, another provider serving a similarly named model, a role alias with an unknown resolution, or a fallback model without reporting the mismatch. Existing operator restrictions still apply. A conflicting native override is a routing blocker, not permission to rewrite global settings or to mislabel another model as current.

If OMP changes a worker's model or effort through an automatic fallback, prewalk or extension, stop treating that worker as a compliant current-model execution. Preserve its output for inspection, record what happened, and resolve the route before counting it as accepted evidence. Do not silently change the run to auto-models. Continue independent work that remains valid.

On a new session/resume, `current-model` means the model currently active there. Refresh the snapshot and routing, record the change, and invalidate the previous final approval. Retain useful design decisions and artifacts unless their inputs or scope changed.

## 5. Apply and verify native routing

Model selection is work performed by the director, not a request for the user to hand-edit seven files. Populate all assignments in `run.json`, retain `modelRouting.status: "pending"`, then use one supported route:

1. If the runtime already resolves the exact intended identities/efforts, use its existing routing and record the source. Do not rewrite matching configuration.
2. If authorized per-call selection is actually advertised, pass exact selectors using that live schema. Do not send an unavailable tool field.
3. Otherwise use the included local helper to apply the assignments to this package's seven native agent definitions:

   ```bash
   tools/ui-design models-apply --repo . --run docs/design/runs/RUN_ID
   ```

   Replace `RUN_ID` with the actual initialized directory. This helper backs up the original agent files and modes, updates only their model/thinking frontmatter, and journals the applied hashes. It leaves global configuration and project `.omp/config.yml` alone. It checks relevant native agent overrides through the CLI and conservatively refuses any nonempty override for a UI specialist, including an alias or an apparently matching value. Use existing routing when it already implements the intended assignments; otherwise report the specific routing conflict. A CLI failure is reported, not interpreted as “no overrides”.

Use the seven existing agent names. Do not create aliases to escape a higher-priority override. Keep one routing owner per project; do not run competing model policies over the same seven files concurrently. Restore a prior run's temporary assignments before applying a different run.

Inspect the live task agent discovery/resolved metadata after routing changes. Current OMP refreshes agent definitions at task preflight, but session-only state and extensions can still alter the result. Verify actual model/effort in each task's metadata or other authoritative runtime evidence. Do not treat a worker's prose claim as equivalent to native metadata. A successful `models-apply` proves files were changed; it does not prove provider execution.

Use one naturally required task for the initial observation rather than launching seven costly dummy tasks. Record unused roles as configured but unused. Before a later role is first dispatched, verify its actual route as well. Keep planned and observed assignments distinguishable in `model-routing.md`, with task identifiers where available. If the runtime cannot reveal the actual route, say so and leave the routing status pending rather than claim verified compliance.

## 6. Record, resume and restore

The required record is:

```json
{
  "modelPolicy": "auto-models",
  "modelRouting": {
    "status": "pending",
    "path": "model-routing.md",
    "sha256": null,
    "sessionModel": null,
    "sessionThinking": null,
    "assignments": []
  }
}
```

Each assignment has `agent`, `model`, `thinking` and `rationale`. Include exactly the seven names listed above. Store concrete provider/model identities, not unresolved `@role` aliases. Fill the record from observed information; the template above is intentionally incomplete.

Keep `model-routing.md` as the readable audit trail: policy, main-session snapshot, eligible candidates, routing source, reasons, actual task observations, unused roles, fallbacks, unresolved conflicts, and temporary configuration state. After the routing is genuinely resolved and all executed task observations agree, set status to `resolved` and obtain the file digest:

```bash
tools/ui-design models-digest docs/design/runs/RUN_ID
```

Copy the returned hash into `modelRouting.sha256`. `check-run` requires resolved routing with a fresh digest; current-model also requires every recorded model/thinking pair to match the session snapshot. These are record checks, not an API audit. The director must supply truthful observations. Model policy, assignments and report bytes are bound into final acceptance.

When pausing for the user, handing over, or before upgrading the package, finish/park active workers and restore temporary agent files:

```bash
tools/ui-design models-restore --repo . --run docs/design/runs/RUN_ID
```

Restore refuses to overwrite later edits to those files. Resolve a real conflict by inspecting it, not by deleting the journal or resetting the project. On resume, re-read context and native routing, update the assignment record, and reapply only as needed. Keep the backups and journal as recovery evidence. Do not restore while workers still depend on the temporary routing for nested tasks.

At finalization, restore first, record restoration and any limitations in `model-routing.md`, refresh its hash, and then compute the final review digest. Updating the report after final approval makes that approval stale. A package update during an active model assignment may report managed-agent edits; restore the assignment and retry the update.

## 7. Limits and sources

This package is a skill workflow plus local configuration helpers. It is not a new OMP scheduler or a provider gateway. It cannot manufacture access to a model, guarantee a remote provider's internal model identity, or prevent an existing extension from changing live routing. State the observable scope of verification.

Primary OMP references, checked 12 November 2026:

- Model catalog, effective image input and selectors: https://github.com/can1357/oh-my-pi/blob/main/docs/models.md
- Native agent fields, model precedence, task preflight and per-call gates: https://github.com/can1357/oh-my-pi/blob/main/docs/task-agent-discovery.md
- Effective config reads and global/project write behaviour: https://github.com/can1357/oh-my-pi/blob/main/docs/settings.md
- CLI flags and live help: https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md

The installed runtime is authoritative when its interfaces differ from these references. Discover and adapt supported mechanics; do not weaken the user's permissions or claim unverified compatibility.
