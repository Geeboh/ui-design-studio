# Visual system and complete mockups

Use this reference during `ui-plan`, `ui-design` and `ui-theme`. Develop a distinctive, coherent system that serves the project's tasks. Work within the director's theme contract; this reference does not replace its schema or lifecycle rules.

## Translate references into decisions

Inspect supplied pictures and existing brand material. Describe their hierarchy, geometry, spacing rhythm, type characteristics, contrast relationships, density, texture and atmosphere. Separate transferable principles from literal imagery or brand marks. Ask which attributes matter in guided mode; make and record that judgment in yolo mode.

Reconstruct interface structure using the host's native controls, declarative styles and vector resources; use semantic HTML, CSS and SVG for web targets. Do not add a web rendering layer to a native project merely to reuse this package's web sample. A browser-rendered board can communicate a native concept, but native production behaviour must be verified in the actual toolkit. Use raster assets only where the content or a justified visual requirement calls for them. Do not turn a screenshot into a background image, bake labels into graphics or require external image generation for a code-native design. Record the provenance and applicable licenses of incorporated assets.

## Build comparable concepts

Have concept workers use the same brief, representative page, realistic content and storyboard scenarios. Produce two or three meaningfully different directions with consistent comparison conditions. Each direction needs a rendered board, palette, typography and spacing specimens, navigation, representative forms/data, status states, icon language and a small task storyboard.

Every storyboard frame must show context, the user's action, the system response and the next decision. Include failure and recovery. Sample graphics should clarify behavior rather than become a gallery of unrelated decorations.

Explain each direction's strengths, limitations, likely implementation cost and relationship to assessment findings. In guided mode, present the actual boards before requesting selection. If the user combines aspects, the director reconciles them into one consistent system and renders the result before freezing it.

## Colour, typography and space

Build primitive values, semantic roles and component decisions separately. Use semantic roles such as canvas, surface, text, muted text, border, accent, focus, success, warning and error. Do not let a palette colour's name become its sole meaning. Assess actual foreground/background pairs in every supported colour mode and interaction state.

Use colour temperature, saturation and lightness deliberately to establish hierarchy. Keep attention-demanding colours scarce and consistent. Status must also use text, shape or icons. Avoid universal claims that a particular hue causes a particular emotion; audience and context matter. Check colour-vision differences and grayscale legibility where relevant.

Prefer the established system font stack or a justified, locally available font. Define a compact type scale, readable line heights, clear weight distinctions and sensible line lengths. Preserve browser text resizing. Use tabular numerals where aligning measurements improves comparison; avoid tiny labels and all-caps paragraphs.

Use spacing to show relationships: smaller within a group, larger between groups. Align recurring content edges and control dimensions. Define layout grids and density variants intentionally. Let content determine breakpoints; do not treat a single desktop screenshot as a responsive specification. Use logical CSS properties where practical and examine long or translated text.

## Components, icons and motion

Create shared primitives before page-specific decoration. Include default, hover, focus-visible, pressed, selected, disabled, loading and invalid states where applicable. Specify labels, helper text, errors and success feedback. Distinguish selection from keyboard focus. Prefer native controls unless a custom pattern has a demonstrable need and a complete interaction contract.

Use one coherent icon family with consistent view boxes, stroke/weight, optical sizing and corner treatment. Subset existing licensed SVG assets or create simple vectors. Decorative SVGs are hidden from assistive technology; meaningful icons have an appropriate accessible name. Icon-only actions need discoverable labels. Avoid bundling an entire icon library for a handful of symbols.

Use motion to explain change and continuity, with short and consistent timing. Honour reduced-motion preferences. Avoid motion that delays tasks, distracts from data or creates continuous CPU/GPU work. Evaluate large shadows, filters, blur and complex SVGs on the target class of device; vector assets are not automatically cheap.

## Complete every page and dialog

Use the assessment inventory as the design checklist. Allocate page families to workers after shared tokens and primitives are frozen. Produce complete, realistic layouts for every discovered screen/window and dialog, including the applicable window/device sizes and materially different states. For desktop/mobile targets, include orientation, display scaling, safe areas, on-screen keyboards and input variants when they change the design. Show full content flow, not only attractive above-the-fold areas.

Specify responsive rearrangement, overflow, long content, loading/error handling, keyboard navigation, focus entry/return and destructive-action behavior. Keep a linked coverage index under `docs/design/runs/<id>/`. A generic sample component or a note saying “similar to another page” does not cover a unique screen.

Place the final theme in `themes/<slug>/` using the director's package contract. Keep the editable tokens as the source of truth and generate the supported CSS representation deterministically. [DTCG Format 2025.10](https://www.designtokens.org/TR/2025.10/format/) provides typed token interchange; it is a Community Group specification, not a W3C Standard or an application theme packaging standard. Follow the helper's documented supported token subset rather than assuming it implements every DTCG feature.
