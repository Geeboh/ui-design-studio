---
name: ui-design-studio
description: Direct a complete UI and UX redesign with usability assessment, guided or autonomous yolo choices, specialist agents, coherent visual concepts, complete screen and dialog mockups, implementation, independent review, and reusable themes. Use to assess, beautify, redesign, theme, or improve interfaces in any web, desktop, or mobile project, using its host toolkit and available verification tools.
---

# UI Design Studio

Direct the requested UI work. Preserve application behavior, project instructions,
approval provenance, accessibility, offline requirements, routing, Git policy and
release gates. The bundled validator covers only the web CSS/SVG theme adapter.
Native targets require their own adapter and platform checks.

## Director hot path

1. Read the current request, applicable project `AGENTS.md` files, `.omp/RULES.md`,
   requirements, `ui-design-studio.json`, existing runs and Git status.
2. Read [project context](references/project-context.md) and [workflow](references/workflow.md).
   Resolve scope, host, offline requirement, model policy and required evidence before
   changing application files. Do not use `profile=` to select requirements.
3. Reuse or resume a run when possible. Otherwise initialize one with `init-run`.
   Record source-labelled context, scope rationale, selected theme action and resolved
   model assignments. The run record is a checkpoint, not completion evidence.
4. Load only the phase skill and references named by the selected phase. Read original
   project instructions again in every worker packet. Do not load the full reference
   tree by default.
5. Keep one owner for shared tokens, adapters, registries and default-theme changes.
   Use non-overlapping worker paths and a different reviewer. Record actual commands,
   artifact digests, blockers and next actions.
6. Run authoritative checks through the bundled engine. Dashboard and MCP are
   projections of the same evidence rules. Never fabricate approvals, screenshots,
   runtime observations or user research.

## Intent and phase routing

| Intent | Phase skill | Minimum input | Output | Gate |
| --- | --- | --- | --- | --- |
| assessment or `assess-only` | `ui-assess` | context, inventory target, run | findings, inventory, baselines | reconciled findings |
| concepts | `ui-plan` | assessment, brief, constraints | comparable concepts, selection | guided user or `agent-yolo` decision |
| mockups or `design-only` | `ui-design` | selected direction, coverage | contract, mockups, interaction specs | applicable coverage and approval |
| implementation | `ui-produce` | approved design, contract, host | bounded code, adapter, integration evidence | actual host checks |
| independent review | `ui-review` | artifact revision, requirements, evidence | findings with severity, repro and fix criterion | independent review |
| theme operation | `ui-theme` | theme contract, host adapter, rollback | versioned theme and validation | adapter-specific checks |
| finalization | `ui-finalize` | current approvals, fresh evidence, package | registered/package result, rollback | full release gates |
| autonomous lifecycle | `ui-yolo` | explicit yolo authorization | agent-owned decisions and full lifecycle | no human approval impersonation |

`component`, `single-flow`, `fix` and `reference-adaptation` use the smallest
applicable phase sequence. `full-redesign` uses Assess, Plan, Design, Produce,
Review and Finalize. Scope completion never sets a full-theme run to passed and
never permits registration without full-theme gates.

## Reference loading

- Read [assessment.md](references/assessment.md) for findings and baselines.
- Read [visual-system.md](references/visual-system.md) for visual decisions.
- Read [decisions.md](references/decisions.md) for approvals and theme lifecycle.
- Read [multi-agent.md](references/multi-agent.md) for ownership and packets.
- Read [theme-module.md](references/theme-module.md) for adapter boundaries.
- Read [quality-gates.md](references/quality-gates.md) for evidence requirements.
- Read [run-records.md](references/run-records.md) for records and dashboard state.
- Read [model-routing.md](references/model-routing.md) for resolved assignments.

Load `workflow.md` for phase artifact and continuation rules. Load `project-context.md`
before requirements-sensitive work. The MCP host reads guides through
`ui_design_read_guide`; OMP uses the bundled files directly. Host-specific operation
belongs in the MCP adapter and dashboard docs, not in worker task contracts.

## Quality and stop conditions

Use native host components, semantic markup, declarative styles and local vector
assets. Cover applicable states, viewports, focus, keyboard, labels, contrast,
reduced motion, long content, errors, recovery, offline and performance checks.
Treat scanner output as evidence, not conformance. Annotate reference-image
observations as rule, applicability and deliberate exclusions.

In guided mode, pause only for real user choices. In yolo mode use `agent-yolo`.
Continue safe work through ordinary failures; stop only for missing access, unsafe
destructive action or an unsatisfied mandatory gate. A missing browser/device or
provider is `BLOCKED_AUTOMATION`, never a pass. Human visual preference, usability
study, physical-device acceptance and release sign-off remain `DEFERRED_UAT`.

Keep status concise:

```text
UI Design: <theme> | <phase> | guided/yolo | active/blocked/complete
Coverage: <completed>/<required> cases | Gates: <passed>/<required>
Next: <specific action> | Blocked: <exact blockers or none>
```

Before handoff, restore temporary routing, refresh its digest, run package and
rollback checks, clean up owned dashboard processes, and report exact preview,
package, verification and rollback paths. Completion means engineering gates pass;
it does not mean user acceptance or deployment.
