# Ready-to-use prompts

Use these prompts in OMP while working in the target project. They read the installed skill directly, so they are also useful when slash-command discovery has not refreshed.

| File | Use |
| --- | --- |
| [START-GUIDED.md](START-GUIDED.md) | Full redesign with your concept and mockup choices |
| [START-YOLO.md](START-YOLO.md) | Autonomous full redesign in normal mode |
| [START-GOAL-YOLO.md](START-GOAL-YOLO.md) | Autonomous full redesign managed by OMP `/goal` |
| [ASSESS-ONLY.md](ASSESS-ONLY.md) | Usability assessment and recommendations without application edits |
| [DESIGN-ONLY.md](DESIGN-ONLY.md) | Assessment, concepts and complete mockups; stop before implementation |
| [RESUME.md](RESUME.md) | Continue the relevant recorded run |
| [RESUME-GOAL.md](RESUME-GOAL.md) | Resume goal-managed work without duplicating the design dossier |

Copy the contents of the fenced text block, not the surrounding documentation. Keep the prompt as one OMP message. The goal prompts begin with `/goal` because they activate a native OMP command; the other prompts are ordinary messages.

Default worker policy is `models=auto-models`. Replace that instruction with `models=current-model` when you want the active provider/model and reasoning selection used throughout the team. The director remains the active OMP session model in both modes. The project context is read automatically; no profile is needed.

These prompts use the full existing UI as their default scope. State a narrower scope explicitly when that is what you want. See `docs/ui-design-studio/RUN-TYPES.md` after installation, or `docs/RUN-TYPES.md` in the archive, for variations and stop conditions.
