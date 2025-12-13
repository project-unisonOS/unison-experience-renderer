# Migration Notes

This renderer was refactored to conform to the canonical experience doctrine and renderer design language in the repo root.

## What was removed

- Dashboard proxying and dashboard persistence into context.
- Card-based rendering and card selection gesture forwarding.
- Persistent framed layout regions and “HUD” chrome.
- Periodic refresh loops designed to keep regions populated.

## What replaced it

- A single-field surface (`src/web/index.html`) with presence as the default state.
- A minimal scene model (`src/web/sceneGraph.js`) and an experience composer (`src/web/composer.js`).
- Event-driven transitions with semantic motion, no continuous render loop.
- Modality adapters (`src/web/modality/*`) with optional cues off by default.

## API changes

- Added: `POST /events`, `GET /events`, `GET /events/stream`
- Kept as aliases for compatibility:
  - `POST /experiences` → same as `POST /events`
  - `GET /experiences` → same as `GET /events`
  - `GET /experiences/stream` → same as `GET /events/stream`
- Removed:
  - `GET /dashboard`
  - `POST /gesture/select`

## Extending safely

Follow `ARCHITECTURE.md` and keep these invariants:

- No persistent containers or navigational structure.
- Scenes are ephemeral and semantic.
- Motion communicates meaning and respects reduced motion.

