# Motion Guide

Canonical reference: `../RENDERER_DESIGN_LANGUAGE.md`

Motion in this renderer is semantic: it communicates recognition, focus change, causality, and completion. If a motion does not carry meaning, it does not belong.

## Allowed transitions

Implemented in `src/web/sceneGraph.js` and applied via `src/web/modality/visual.js`:

- `fade`
  - Meaning: appear/disappear without demanding attention.
  - Use: return to presence; de-emphasize after an ephemeral moment.
- `drift`
  - Meaning: completion or gentle resolution; the field settles.
  - Use: outcome reflection; de-escalation from a focused moment.
- `focusShift`
  - Meaning: attention moves to a single centered element (usually a clarifying question).
  - Use: clarifying question scene.
- `depthEmergence`
  - Meaning: recognition or meaningful arrival; a state becomes “present”.
  - Use: intent recognition acknowledgement.

## Forbidden transitions

- Bounce, elastic, springy overshoot.
- Gamified easing, attention-grabbing loops, or pulse spam.
- Spinner/progress metaphors as a default.
- Any motion whose goal is reassurance through activity rather than meaning.

## Mapping examples

- `intent.recognized` → `depthEmergence` + short hold → return to presence.
- `intent.clarify` → `focusShift` with centered question (text only when required).
- `outcome.reflected` → `drift` + optional minimal periphery text → fade to quiet.

