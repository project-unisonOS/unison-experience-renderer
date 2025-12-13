# Current Renderer Anti-Pattern Map

This document inventories renderer behaviors that violate the canonical experience doctrine and renderer design language in the repo root:

- `../unison-experience-doctrine-canonical`
- `../RENDERER_DESIGN_LANGUAGE.md`

The intent is to make drift visible and removable.

## Forbidden patterns found

### Dashboard + persistent layout

- Files: `src/main.py`
- Surfaces:
  - `GET /dashboard` proxies a dashboard model from `unison-context`.
  - `POST /experiences` persists a “dashboard cards” shape back into context.
  - The root HTML uses a persistent grid layout (`.canvas`) with fixed regions.
- Why it violates canon:
  - A dashboard implies a persistent surface with navigable structure, which conflicts with “experience is generated, not navigated” and “presence before information”.
  - A persistent grid layout implies panels/frames rather than a single perceptual field.

### Cards as a primary content primitive

- Files: `src/main.py`, `README.md`, `tests/test_dashboard_proxy_and_prefs.py`
- Surfaces:
  - The HTML renderer constructs `.card` nodes and renders lists of “cards”.
  - Gesture input is modeled as selecting a card (`POST /gesture/select`).
- Why it violates canon:
  - Cards are explicitly disallowed (“no windows, no panels, no cards”).
  - Card selection implies app-like affordances and UI ownership.

### Panels / framed regions

- Files: `src/main.py`
- Surfaces:
  - `.panel` containers with borders, shadows, headings, and scrollable interiors.
  - A “HUD” cluster anchored to the corner.
- Why it violates canon:
  - Panels and HUD chrome create a windowed/tooling metaphor and persistent structure.
  - Anchored UI implies a layout that competes with presence.

### App-like navigation cues and interaction prompts

- Files: `src/main.py`
- Surfaces:
  - Visible labeled sections (chat, tools, dashboard) that read like an application UI.
  - Periodic refresh loops to “fill” the surface (`setInterval(..., 15000)`).
- Why it violates canon:
  - The renderer should not demand interaction or continuously “busy” itself.
  - Progressive disclosure should be intent-led and transient, not periodic polling to populate regions.

### Mechanical loading / activity indicators

- Files: `src/main.py`
- Surfaces:
  - Status strings such as “transcribing…” and other activity text in persistent UI regions.
- Why it violates canon:
  - The design language discourages spinners/progress metaphors; feedback should be semantic and minimal.

## External surfaces discovered (not refactored here)

- Files: `../unison-shell/renderer/index.html`
- Observations:
  - Uses repeated `.card` sections and a framed “developer mode” layout.
- Note:
  - This document focuses on `unison-experience-renderer`. If `unison-shell/renderer` is intended to be a canonical experiential surface, it should be refactored under the same constraints.

