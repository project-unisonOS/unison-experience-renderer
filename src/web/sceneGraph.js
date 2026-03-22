export const SceneTypes = Object.freeze({
  BOOT: "boot",
  ONBOARDING: "onboarding",
  PRESENCE: "presence",
  TRANSCRIPT: "transcript",
  INTENT_RECOGNIZED: "intent.recognized",
  INTENT_CLARIFY: "intent.clarify",
  OUTCOME_REFLECTED: "outcome.reflected",
});

export const TransitionKinds = Object.freeze({
  FADE: "fade",
  DRIFT: "drift",
  FOCUS_SHIFT: "focusShift",
  DEPTH_EMERGENCE: "depthEmergence",
});

export function createScene(type, payload = {}) {
  return { type, payload: payload && typeof payload === "object" ? payload : {} };
}

export function createTransition(kind, durationMs) {
  return { kind, durationMs: typeof durationMs === "number" ? durationMs : 0 };
}
