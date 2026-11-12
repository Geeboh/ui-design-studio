# Start a goal-managed autonomous redesign

Use in an OMP session with goal mode available and no conflicting active/paused plan or vibe mode. Paste the entire text block as one message. The `/goal` command starts the objective; its text tells the agent to read the skill directly.

Replace `models=auto-models` with `models=current-model` if you want the active provider/model and reasoning selection used for every specialist. The director remains your active OMP session model in either case.

```text
/goal Read .omp/skills/ui-design-studio/SKILL.md and use the installed UI Design Studio workflow with mode=yolo and models=auto-models for this project.

Complete the entire existing UI scope through Assess, Plan, Design, Produce and Finalize, including every discovered page, dialog and applicable state. Read the project's existing instructions, requirements, architecture decisions, design system and implementation. Record the source-backed context; no profile selection is needed. Preserve project workflow, Git/release policy and unrelated work.

Use specialist task agents with clear ownership and independent reviewers. Discover eligible configured models, resolve the chosen model policy and verify the assignments actually used. Assess usability and performance, develop and compare coherent graphical concepts, choose or reconcile a direction, verify complete mockups, and choose an appropriate theme name. I delegate the aesthetic choices and Plan/Design appraisals to you; record them as agent decisions.

Implement the selected direction through the host's existing architecture, with a versatile theme interface and a documented theme module/adapter. Prefer code-native presentation and vectors, minimize dependencies and runtime requests, and preserve all product, accessibility, offline and recovery requirements established by the project. Run the actual required checks and fix review findings.

Follow the default-theme lifecycle: the first successfully finalized module becomes the default with prior styling recoverable; later unspecified runs create a new named module and retain the default. Respect already stated theme choices and existing individual preferences.

Maintain the original objective across turns and compaction. Persist context, model assignments, decisions, coverage, evidence, progress and blockers so the work can resume. Continue ordinary decisions and reversible work without aesthetic checkpoints. Finish independent work before asking for a genuine missing input or access requirement.

Mark the goal complete only after all required deliverables and checks for the full agreed scope have current evidence, independent review and a documented package/handover. An interrupted turn, budget limit, draft archive or unresolved gate does not count as completion. Hand over the actual theme/version, package, preview, assessment, verification, default status, known limitations, customization instructions and rollback procedure.
```

For a paused existing goal, resume it instead of creating another one. See `RESUME-GOAL.md`. If goal mode is unavailable, use `START-YOLO.md`; the design workflow still works in normal mode.
