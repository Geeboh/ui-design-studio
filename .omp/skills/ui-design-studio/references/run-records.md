# Run records and executable checks

## Contents

1. Command reference
2. Run and evidence
3. Coverage
4. Approvals and invalidation
5. Finalization sequence
6. Limits and exit codes

Run all helpers through `tools/ui-design`, which selects the installed virtual environment. The Python helper needs Python 3.10 or later and only its standard library. The JSON records support resuming and checking evidence; they do not independently conduct user studies or operate the UI. The supplied theme build/check/register/package commands target the web CSS/SVG module contract. Native projects need an explicit native adapter, packaging/tooling extension where necessary, and native acceptance checks; a web helper PASS is not native validation.

## 1. Command reference

```bash
tools/ui-design doctor --repo .
tools/ui-design init-run --repo . --mode guided --theme-action auto --theme-id working-title
tools/ui-design context-digest docs/design/runs/RUN_ID
tools/ui-design models-digest docs/design/runs/RUN_ID
tools/ui-design theme-new --repo . --id fieldstone --name "Fieldstone"
tools/ui-design build-theme themes/fieldstone
tools/ui-design check-theme themes/fieldstone
tools/ui-design theme-digest themes/fieldstone
tools/ui-design decision-digest docs/design/runs/RUN_ID --files plan/selection.md
tools/ui-design check-run docs/design/runs/RUN_ID
tools/ui-design register --repo . --theme fieldstone --run docs/design/runs/RUN_ID
tools/ui-design package themes/fieldstone --output dist/fieldstone-1.0.0.zip
```

Replace `RUN_ID` with the exact directory returned by `init-run`; do not type the placeholder literally. `--theme-action auto` on a later guided run deliberately requires a choice. Use `--theme-action modify-default` with the current default's ID, or `--theme-action new` with a new ID. Yolo selects new by default on later runs. An explicit approved later default change uses `register ... --make-default`.

`init-run` takes `--models auto-models` or `--models current-model`; omission uses the project `modelPolicy` preference or `auto-models` when unset. No `--profile` is required. A deprecated profile option from an old script is ignored for new context discovery. `context-digest` and `models-digest` hash the actual context/routing documents; they do not read project requirements, choose models or verify native OMP routing themselves.

`doctor` is read-only framework/capability discovery. It reports uninspected browser and OMP capabilities. `theme-new` copies the specimen, compiles it and checks it; it does not integrate, register or activate it. Verify and update copied name/description/author/preview text before release. `package` validates a portable archive even for a draft, so successful packaging is not final run acceptance.

## 2. Run and evidence

`run.json` starts with this structure and remains pending until real work is complete:

```json
{
  "schemaVersion": "1.1",
  "id": "EXACT_GENERATED_RUN_ID",
  "mode": "guided",
  "modelPolicy": "auto-models",
  "projectContext": {
    "status": "pending",
    "path": "project-context.md",
    "sha256": null,
    "offline": "unknown",
    "sources": []
  },
  "modelRouting": {
    "status": "pending",
    "path": "model-routing.md",
    "sha256": null,
    "sessionModel": null,
    "sessionThinking": null,
    "assignments": []
  },
  "themeAction": "new",
  "themeId": "working-title",
  "phase": "assessment",
  "status": "pending",
  "themeDigest": null,
  "implementer": null,
  "evidence": []
}
```

Resolve the actual project requirements using [project-context.md](project-context.md), then record its source labels, resolved offline applicability and current context-file hash. Resolve models through [model-routing.md](model-routing.md), record the exact active provider/model and thinking setting, and record verified `agent`, `model`, `thinking` and `rationale` entries for each of the seven shipped specialists. `provider-default` is an explicit thinking value where no controllable effort exists. Under `current-model`, every assignment must match both the session model and thinking snapshot. Set each context/routing status to `resolved` only after the corresponding work is complete, and record its actual document hash. Pending or unknown records block complete finalization; model names written into a record do not configure or prove OMP routing.

`coverage.json` and `decisions.json` continue to use schema version `1.0`. Existing v1.0 `run.json` files remain readable under their legacy contract. `models-apply` and the new context/routing records require run schema 1.1. Preserve completed legacy dossiers; for incomplete legacy work create the linked 1.1 continuation described in [workflow.md](workflow.md#7-continue-a-legacy-10-run). The director performs that procedure; the user need not hand-edit a schema. Do not rewrite old records merely to make a check pass, or drop required evidence during an upgrade.

Set `implementer` to the actual integrator/team identity, not a made-up external person. Finalization needs passed evidence of kinds `integration`, `visual`, `accessibility`, `offline`, `performance`, and `review`. A result file should name the command/procedure, source revision, tested scope, viewport/device/browser/cache/network conditions, observed outcome, reviewer, limitations and relevant screenshots/logs. Distinguish lab performance from field performance and expert review from user research.

Each passed evidence record uses:

```json
{
  "id": "visual-01",
  "kind": "visual",
  "path": "evidence/visual-review.md",
  "sha256": "ACTUAL_SHA256_OF_THAT_FILE",
  "status": "passed",
  "reviewer": "ACTUAL_REVIEWER_OR_AGENT_ID",
  "recordedAt": "ACTUAL_ISO_TIMESTAMP"
}
```

These placeholders are instructions, not valid evidence. Do not copy them into a completed record. Evidence paths are relative to the run and must stay within it. Use `sha256sum` or Python's standard-library `hashlib` in the venv to hash real artifacts. Keep screenshot/log filenames stable and reference their hashes inside the result file where required. An evidence hash proves file identity, not the truth of its contents.

Unrun checks remain `pending`/`unverified` and block completion. A `failed` check fails it. Only a resolved new-run context with `offline: "not-required"` can mark `offline` evidence `not-applicable`, with a specific reason grounded in project requirements. Unknown applicability is not a waiver. Legacy v1.0 runs retain their original rule: only a generic run may waive offline with a reason; a TADA run cannot. Independent review must name a reviewer distinct from the implementer. The director must verify actual role independence; a different string alone proves nothing.

Record baseline and application revision/diff in evidence. The theme digest binds module bytes, not every application source file; the director must rerun affected application checks if host code changes after verification.

## 3. Coverage

Populate `coverage.json` from discovery, not from the subset a designer happened to implement:

```json
{
  "schemaVersion": "1.0",
  "inventoryComplete": false,
  "surfaces": [
    {
      "id": "module-library",
      "kind": "page",
      "route": "REPLACE_WITH_OBSERVED_ROUTE",
      "states": ["populated", "empty", "error"],
      "viewports": ["desktop-1440", "narrow-390"],
      "cases": []
    }
  ]
}
```

Kinds are `page` or `dialog`; use `page` for a native full screen/window and `dialog` for a native sheet or modal surface. `route` identifies the actual navigation path or trigger, including native navigation when relevant. Viewport labels may name required device/window sizes, orientations and scaling conditions. Keep native-toolkit resources and checks explicit in the evidence; this coverage mapping does not make the web theme compiler validate a native package. Keep optional provenance/applicability explanations as additional fields or in the report. For each declared state × viewport combination add:

```json
{
  "state": "populated",
  "viewport": "narrow-390",
  "mockup": "design/module-library-populated-390.html",
  "implementation": "evidence/module-library-populated-390.md",
  "qaEvidence": ["visual-01", "accessibility-01"]
}
```

The implementation reference is a report linking actual source paths, rendered application evidence and tests. It is not a mockup relabelled implementation. Reconcile router definitions, feature/role states, overlays, navigation and runtime exploration before setting `inventoryComplete: true`. The validator detects missing declared cases; it cannot discover an omitted route by reading a hand-written inventory.

## 4. Approvals and invalidation

`decisions.json` has `schemaVersion: "1.0"` and a `decisions` array. The latest entry for each of `plan`, `design`, `finalize` applies. Outcomes are `approved`, `rejected`, `pending` or `superseded`. Preserve prior decisions for traceability.

Plan and Design decisions carry a nonempty `inputs` list and the returned `inputsDigest` from `decision-digest`. Design's input list must include all approved Plan input paths plus the contract and all approved mockup files. Use exact files, not only an index that links mutable pages. This binds a changed concept to downstream review instead of letting an old approval silently survive.

```json
{
  "stage": "design",
  "actor": "user",
  "outcome": "approved",
  "rationale": "RECORD_THE_ACTUAL_APPROVAL_AND_SCOPE",
  "inputs": ["plan/selection.md", "design/contract.md", "design/REAL_MOCKUP.html"],
  "inputsDigest": "ACTUAL_DIGEST_FROM_DECISION_DIGEST"
}
```

Guided Plan/Design use `actor: "user"`; record only an actual user decision. Guided Finalize can use `actor: "director"` after independent review, so no redundant final user checkpoint is required. Yolo uses `actor: "agent-yolo"`. Neither an autonomous choice nor an AI critic is a human approval.

Changed approved inputs invalidate the recorded digest. Re-review and append the new decision. Changed evidence, coverage, theme bytes, project-context bytes/fields, model-routing bytes/assignments or relevant run context invalidate final approval. Changing the source requirements, brief or scope must also invalidate affected decisions even if a validator cannot infer the semantic relationship. A context-document hash cannot prove that upstream requirements have not changed; recheck those sources on resume.

## 5. Finalization sequence

The supplied command sequence below applies to the web theme adapter. For a native target, establish the native contract, tooling and platform checks described in `theme-module.md`; do not label a web-only check as native acceptance.

1. Verify resolved project context and actual model assignments remain current. Complete actual application integration, all required tests and independent reviews. Address unresolved findings. Retain exact source revision/diff and measurement conditions.
2. Run `build-theme`, then `check-theme`. Run `theme-digest` and record its returned digest in `run.json` only after the final theme files are ready.
3. Finish or park workers that depend on temporary model assignments. If `models-apply` was used, run `tools/ui-design models-restore --repo . --run <run-directory>`, record restoration in the routing document and refresh its hash with `models-digest`. Resolve later-file-edit conflicts without overwriting them. Record real evidence and hashes, complete coverage, and current Plan/Design approvals. Set `run.phase` to `finalize` and `run.status` to `passed` only after substantive acceptance. These fields do not themselves create a pass.
4. Run `check-run`. It returns `reviewDigest` when the record is structurally readable, even while waiting for final approval. Resolve every other blocker/failure before approving.
5. Append a Finalize decision with actual actor, outcome, rationale, and `inputsDigest` equal to the current `reviewDigest`. The final digest binds current theme/evidence/coverage, resolved project/model context and prior approvals; do not compute it from arbitrary text.
6. Run `check-run` again. It must return `PASS` before `register`. Register checks theme identity/current bytes and project byte limits as well as run status. Registry updates are serialized and backed up; never delete a live finalization lock to force a second writer through.
7. Confirm that the host adapter uses the registry, verify default selection/persistence/fallback and rollback, then package. Update the report with actual default state and artifact hashes. If this verification changes code or required evidence, refresh the affected acceptance records before claiming completion.

Avoid a circular gate: implement and verify the adapter/default logic in the development environment before finalization, then observe the final registry selection as a release smoke check. A broken smoke check invalidates final acceptance and must be fixed; restore the prior default while doing so.

## 6. Limits and exit codes

`0` means the invoked operation passed; `1` means failed/invalid; `2` means blocked/incomplete. State the scope of a pass. `doctor PASS` is successful discovery, `check-theme PASS` is module-format validation, and `check-run PASS` is a complete/fresh recorded dossier. None is a substitute for executing and examining the real application checks.

Do not edit checks merely to obtain green status. A deliberate contract change requires a documented need, updated schema/docs and meaningful regression checks. The helper's tests use synthetic fixtures; never copy those fixtures as if they were real project evidence.

## 7. Live progress and Design Server

With the optional user-global runtime and current OMP extension installed, the main OMP session automatically starts and supervises a dashboard before work. The console prints verified loopback and LAN URLs followed by a locally generated QR. It stays live through guided pauses and recovers after an unexpected child exit. Use `/ui-design-dashboard` to display its links, `/ui-design-dashboard stop` to intentionally stop it, and `/ui-design-dashboard start` to resume it. Explicit stop prevents background recovery until start. OMP shutdown closes its owned child, not other clients' borrowed servers.

For standalone operation without OMP, use `ui-design dashboard-serve --repo /absolute/project` from the global runtime and retain the foreground terminal. This mode prints `(Ctrl-C to stop)`. OMP uses its explicit stop command instead.

The lower-level standard-library run server remains available when the global runtime is not installed. After `init-run`, retain this foreground service:

```bash
tools/ui-design design-serve docs/design/runs/RUN_ID --host 0.0.0.0 --port 0 --public-url http://YOUR_LAN_IP
```

Replace `RUN_ID` and `YOUR_LAN_IP` with the actual run directory and reachable host address. Port zero chooses a free port. Readiness prints the complete address with the actual port and a secret fragment. Pin that exact address in progress reports. The address grants its holder access to the run and guided approvals. Do not put it in committed evidence or public logs. The default listener is loopback when `--host` is omitted.

An explicit LAN listener does not create a public tunnel, configure a firewall or prove reachability from another computer. Use SSH forwarding or an existing HTTPS reverse proxy on untrusted networks. Plain HTTP does not encrypt artwork or approvals. Do not expose this session server directly to the public internet.

The installed `.omp/extensions/ui-design-progress.ts` reads the server's status and pins a separate widget below OMP's editor. It preserves the existing Pi Tasks widget and built-in footer. Reload extensions after installation.

Automatic footer observation does not claim Pi Tasks ownership. Select the intended project-relative run with `/ui-design-progress docs/design/runs/RUN_ID` to pin it and designate this OMP session as the run's Pi Tasks director. Selecting the run from another session explicitly hands off that role. Each session retains its own observation file; unrelated sessions cannot replace the director's tasks. `/ui-design-progress auto` restores read-only task observation. Missing dashboard-runtime failures must produce an actionable installation message, not a fabricated live address.

Without a compatible host UI, use a separate terminal:

```bash
tools/ui-design status docs/design/runs/RUN_ID --watch
```

The fallback emits regular status blocks without injecting terminal control sequences into another application's console. The director also emits status after worker results, phase changes and at least once per working minute. Both displays use observed gate and coverage counts, not guessed percentages. An incomplete inventory is not overall completion.

### Publish current activity and artwork

The director owns next actions, blockers and task reconciliation. Each worker owns its activity record:

```bash
tools/ui-design progress docs/design/runs/RUN_ID --next "Review the narrow mockups" --blocker "none"
tools/ui-design worker docs/design/runs/RUN_ID --id page-library --task "Library mockups" --status active --message "Rendering empty states"
tools/ui-design artwork docs/design/runs/RUN_ID --file design/library-empty.html --title "Library empty state" --context "This mockup defines the first-run library experience."
tools/ui-design worker docs/design/runs/RUN_ID --id page-library --task "Library mockups" --status done --message "Mockups published for review"
```

Publish every generated version before replacing its source file. Automatic discovery scans browser artwork and mockups inside the run, including HTML, SVG, raster images and PDF. It cannot recover versions overwritten between scans. Keep generated art and local dependencies inside the run. Publication adds the precise one-sentence purpose; automatically discovered files receive a path-based description rather than invented intent.

The server also imports visual files and local dependencies from the active theme when it can verify the project and configured run directory. Use `design-serve RUN --repo /absolute/project` when project selection is ambiguous. Explicit theme publication is confined to that run's active theme:

```bash
tools/ui-design artwork docs/design/runs/RUN_ID --repo . --file themes/THEME_ID/preview.html --title "Theme preview" --context "This preview shows the active theme's shared components."
```

Imported copies appear under `theme-artwork/THEME_ID/` in the run. Use those run-relative paths for approval inputs. Original theme files remain untouched.

The Working feed updates as art appears. The Library retains earlier versions and supports browsing and search. Image thumbnails use the actual image. HTML mockups use a scaled sandboxed preview; selecting a thumbnail opens the full-size viewer. Previews disable scripts and external requests. A script-driven mockup needs a rendered static screenshot for visual review; use the real application separately for interaction QA.

The dashboard shows reported workers and real task observations, not inferred process liveness. The explicitly selected OMP director mirrors available `pi-tasks:state` events without changing task state. Automatic observers remain read-only. Missing model-cost or token data stays absent. Gate acceptance and evidence freshness remain governed by the existing checks.

### Present guided artistic choices

Publish a request against the actual artifacts:

```bash
tools/ui-design approval-request docs/design/runs/RUN_ID --id plan-choice --stage plan --title "Select the visual direction" --context "Review the concept boards before choosing a direction." --files plan/concept-a.html plan/concept-b.html
```

Pass `--choices plan/choices.json` to supply named concepts or palettes. The run-relative file contains an array of `{ "id": "concept-a", "label": "Concept A", "artworkIds": ["ID_RETURNED_BY_ARTWORK_PUBLICATION"] }` records. Use actual current artwork IDs, not that placeholder. Each option references only this request's reviewed artifacts. Request IDs are immutable; publish a new ID when the offer changes.

The dashboard presents the artifacts and rationale field. Only a submitted guided choice appends an `actor: "user"` decision. Approving a listed existing concept records that selection. To request a combination that has not been rendered, submit Request changes with the desired elements in the rationale, then review a new request for the reconciled artifacts. Approval binds current input bytes and local dependencies; changed inputs require a new review. Design requests include all approved Plan inputs, the shared contract and the complete mockup set. Yolo displays actual autonomous decisions and never waits for a human artistic form.

### Clean up owned server resources

```bash
tools/ui-design design-cleanup docs/design/runs/RUN_ID
tools/ui-design design-cleanup --all --repo .
```

Cleanup asks the authenticated owner to stop. It never kills a process solely from a stored PID. It removes the listener, owned runtime locator, status cache and temporary server files. It preserves the original run, decisions, evidence, generated art and accumulated artwork library. Repeating cleanup is safe.

Inert `.design-server.lock` and `.design-records.lock` coordination files remain so concurrent operations keep a stable lock identity. Their OS locks are released; no listener or active server resource remains. Do not delete a live lock to force a second owner.

A yolo server watches for current final acceptance and cleans itself up on success. Successful yolo registration also requests cleanup. At completed yolo handover, run `design-cleanup` and verify shutdown even if the automatic path already ran. Blocked work is not completion. Guided review pauses retain their server; explicitly clean up when cancelling or finishing.

Run cleanup does not stop OMP's waiting dashboard. That dashboard stays available for the next run until `/ui-design-dashboard stop` or OMP session shutdown. A completed or explicitly cleaned run must not be reopened merely by polling.
