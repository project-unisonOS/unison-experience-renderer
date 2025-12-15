# Renderer Anti-Pattern Map (Historical + Guardrails)

This document tracks renderer behaviors that violate the canonical experience doctrine and renderer design language in the workspace root:

- `../unison-experience-doctrine-canonical`
- `../RENDERER_DESIGN_LANGUAGE.md`

The intent is to make drift visible and removable.

## Truth-finding status (what’s actually deployed)

The devstack builds and runs the **top-level** renderer from:

- `unison-experience-renderer/` (this repo)

Evidence:

- Devstack build context: `unison-workspace/unison-devstack/docker-compose.yml` → `services.experience-renderer.build.context: ../../unison-experience-renderer`
- Running service exposes build metadata at `GET /meta` and returns `404` for legacy dashboard routes like `GET /dashboard`.

## Historical forbidden patterns (legacy implementation)

The patterns below existed in an older renderer implementation that still appears in this workspace at:

- `unison-workspace/unison-experience-renderer/src/main.py`

They are **not** present in the current top-level renderer (`unison-experience-renderer/src/`).

### Dashboard + persistent layout

- Legacy files: `unison-workspace/unison-experience-renderer/src/main.py`
- Surfaces:
  - `GET /dashboard` proxies a dashboard model from `unison-context`.
  - `POST /experiences` persists a “dashboard cards” shape back into context.
  - The root HTML uses a persistent grid layout (`.canvas`) with fixed regions.
- Why it violates canon:
  - A dashboard implies a persistent surface with navigable structure, which conflicts with “experience is generated, not navigated” and “presence before information”.
  - A persistent grid layout implies panels/frames rather than a single perceptual field.

### Cards as a primary content primitive

- Legacy files: `unison-workspace/unison-experience-renderer/src/main.py`, `unison-workspace/unison-experience-renderer/tests/test_dashboard_proxy_and_prefs.py`
- Surfaces:
  - The HTML renderer constructs `.card` nodes and renders lists of “cards”.
  - Gesture input is modeled as selecting a card (`POST /gesture/select`).
- Why it violates canon:
  - Cards are explicitly disallowed (“no windows, no panels, no cards”).
  - Card selection implies app-like affordances and UI ownership.

### Panels / framed regions

- Legacy files: `unison-workspace/unison-experience-renderer/src/main.py`
- Surfaces:
  - `.panel` containers with borders, shadows, headings, and scrollable interiors.
  - A “HUD” cluster anchored to the corner.
- Why it violates canon:
  - Panels and HUD chrome create a windowed/tooling metaphor and persistent structure.
  - Anchored UI implies a layout that competes with presence.

### App-like navigation cues and interaction prompts

- Legacy files: `unison-workspace/unison-experience-renderer/src/main.py`
- Surfaces:
  - Visible labeled sections (chat, tools, dashboard) that read like an application UI.
  - Periodic refresh loops to “fill” the surface (`setInterval(..., 15000)`).
- Why it violates canon:
  - The renderer should not demand interaction or continuously “busy” itself.
  - Progressive disclosure should be intent-led and transient, not periodic polling to populate regions.

### Mechanical loading / activity indicators

- Legacy files: `unison-workspace/unison-experience-renderer/src/main.py`
- Surfaces:
  - Status strings such as “transcribing…” and other activity text in persistent UI regions.
- Why it violates canon:
  - The design language discourages spinners/progress metaphors; feedback should be semantic and minimal.

## Current renderer guardrails

The current renderer includes explicit guardrails to prevent reintroducing these metaphors:

- `unison-experience-renderer/tests/test_guardrails_no_legacy_metaphors.py`
