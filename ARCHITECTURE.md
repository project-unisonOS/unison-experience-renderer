# Renderer Architecture

Canonical references (repo root):
- `../unison-experience-doctrine-canonical`
- `../RENDERER_DESIGN_LANGUAGE.md`

## Purpose

`unison-experience-renderer` is a presence-first translation surface that turns intent and state envelopes into a perceptual field. It does not implement application UI structure.

## Invariants

- Default state is presence; empty/quiet/black is valid.
- Single perceptual field; no persistent layout regions.
- No cards, dashboards, panels, windows, sidebars, or docked regions.
- Progressive disclosure is intent-led and transient; there is no navigation surface.
- Motion communicates meaning (recognition, focus, completion) and is never decorative.
- Modality independence: visual is optional; audio/haptic are optional and off by default.
- Low latency: no continuous render loop; transitions are event-driven.

## Data Flow

1. **Envelope ingress (server)**
   - `POST /events` (alias `POST /experiences`) accepts an envelope.
   - Envelopes are queued to `GET /events/stream` (alias `GET /experiences/stream`) via SSE.

2. **Composition (client)**
   - `src/web/composer.js` maps an incoming envelope to a `(scene, transition)` plan.
   - The composer can accept legacy shapes and apply a best-effort mapping.

3. **Render + modality dispatch (client)**
   - `src/web/modality/visual.js` applies the scene to the single field.
   - `src/web/modality/audio.js` emits optional cues when enabled.
   - `src/web/modality/haptic.js` is a stub adapter and stays off by default.

## Scene Graph (Minimal)

This renderer uses a minimal scene description rather than a window tree:

- `src/web/sceneGraph.js`
  - `SceneTypes`: presence, intent recognition, clarifying question, outcome reflection.
  - `TransitionKinds`: fade, drift, focus shift, depth emergence.

A scene is a full-field perceptual state. Elements are ephemeral and semantic (glyphs and minimal text only when required).

## Files of Note

- `src/main.py`: FastAPI service, envelope ingress, SSE stream, static surface hosting.
- `src/web/index.html`: the single-field surface skeleton (presence-first).
- `src/web/app.js`: wiring (event stream → composer → modality adapters).
- `src/web/composer.js`: intent/event → scene composition.
- `src/web/modality/*`: modality adapters.

## Adding a New Scene (Without Drift)

1. Add a new scene type constant in `src/web/sceneGraph.js`.
2. Extend `src/web/composer.js` to produce that scene only in response to a specific envelope `type`.
3. Implement the minimal visual behavior in `src/web/modality/visual.js` using existing motion primitives and transition kinds.
4. If audio/haptic cues are needed, add them as optional plans; keep them off by default.
5. Update guardrail tests so the new scene cannot introduce forbidden metaphors.

If a proposed change requires persistent containers, nav affordances, or framed regions, it is out of bounds for this renderer.

