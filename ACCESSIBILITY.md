# Accessibility and Modality Independence

Canonical reference: `../unison-experience-doctrine-canonical`

This renderer assumes modality loss as normal: the screen may disappear; audio may be unavailable; haptics may not exist. Experiences must degrade gracefully.

## Principles

- Presence-first: silence and darkness can be correct.
- No primary modality: visual, audio, and haptic are peers.
- Low sensory load: avoid persistent text and avoid attention-demanding motion.
- Respect reduced-motion preferences.

## Preferences model (current)

Client-side preferences live in local storage:

- Key: `unison.renderer.preferences.v1`
- Fields:
  - `presenceCueVisual` (default `false`)
  - `presenceCueAudio` (default `false`)
  - `hapticCues` (default `false`)
  - `reduceMotion` defaults from `prefers-reduced-motion`

Audio and haptic cues are off by default and require explicit enabling.

## Screenless flows

When there is no display, the service still functions as an envelope ingress + stream:

- Envelopes arrive via `POST /events`.
- Consumers can subscribe via `GET /events/stream`.

The current built-in audio adapter is intentionally minimal and optional; it is not a voice experience and does not speak by default.

## Testing

- Guardrail tests ensure forbidden UI metaphors do not reappear.
- Reduced-motion is respected via the `prefers-reduced-motion` media query and the `reduceMotion` preference.

