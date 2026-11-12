# Start a guided UI redesign

Paste the following into OMP from the target project root. Replace `models=auto-models` with `models=current-model` if you want all specialists to use the active model and reasoning selection.

```text
Read .omp/skills/ui-design-studio/SKILL.md and act as the UI Design Studio director for this repository.

Run mode=guided with models=auto-models. Scope: the complete existing user interface, including every discovered page, dialog and applicable state.

Read the project's applicable instructions, README, requirements, architecture decisions, existing design system, implementation and prior design records. Derive the constraints from those sources and record them in project-context.md. Do not ask me to choose a profile or import another project's assumptions. Preserve the existing task/gate workflow, Git policy and unrelated work. Resolve and record the actual worker model assignments before relying on them.

Produce an evidence-labelled usability report, a complete surface/state inventory and prioritized recommendations. Assess task clarity, cognitive load, consistency, feedback and recovery, hierarchy, typography, colour, layout, whitespace, accessibility, responsive behaviour and measured performance. Establish offline requirements from project evidence.

After inspecting the project, ask a compact batch of only unanswered design questions. Use any reference images or directions I supply to derive a coherent visual specification.

Use specialist agents to produce comparable unified concepts with rendered boards, palettes, storyboards, icons and components. Present the actual alternatives and a recommendation for my selection. Then create complete page/dialog mockups for the agreed inventory, with relevant layouts, states and interaction details. Present the full mockup index for approval.

After those choices, continue through implementation, independent review, repairs, packaging and documentation without pausing after routine stages. Give coding workers clear ownership and a shared token/component contract. Implement a versatile theme interface through the host's existing architecture. Prefer code-native styling and vector assets, using the supplied CSS/SVG contract for compatible web projects and an explicitly verified adapter for other UI stacks.

Follow the default-theme lifecycle. On the first successfully finalized Studio run, make the resulting module the default with the prior design recoverable. On later runs, ask whether to modify the default or create a new theme unless already specified.

Record decisions, context, model routing, coverage, current evidence and blockers so work can resume. Use real counts for progress. Complete all safe, unblocked work and identify a precise genuine blocker when my input is required. Hand over the theme, preview, usability report, verification evidence, customization documentation and rollback instructions.
```
