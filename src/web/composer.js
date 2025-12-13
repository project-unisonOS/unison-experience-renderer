import { clamp } from "./util.js";
import { SceneTypes, TransitionKinds, createScene, createTransition } from "./sceneGraph.js";

export function createComposer({ preferences }) {
  const reduceMotion = preferences.reduceMotion === true;

  const compose = (envelope) => {
    const normalized = normalizeEnvelope(envelope);
    if (!normalized) return null;

    const { type, payload, urgency } = normalized;
    const durationMs = reduceMotion ? 0 : chooseDurationMs(urgency);

    if (type === "presence") {
      return {
        scene: createScene(SceneTypes.PRESENCE, { cue: preferences.presenceCueVisual === true }),
        transition: createTransition(TransitionKinds.FADE, durationMs),
        audio: null,
        haptic: null,
      };
    }

    if (type === "intent.recognized") {
      return {
        scene: createScene(SceneTypes.INTENT_RECOGNIZED, { holdMs: reduceMotion ? 0 : 520 }),
        transition: createTransition(TransitionKinds.DEPTH_EMERGENCE, durationMs),
        audio: { kind: "ack" },
        haptic: { kind: "ack" },
      };
    }

    if (type === "intent.clarify") {
      const text = typeof payload.text === "string" ? payload.text.trim() : "";
      if (!text) return null;
      return {
        scene: createScene(SceneTypes.INTENT_CLARIFY, { text }),
        transition: createTransition(TransitionKinds.FOCUS_SHIFT, durationMs),
        audio: { kind: "question" },
        haptic: null,
      };
    }

    if (type === "outcome.reflected") {
      const text = typeof payload.text === "string" ? payload.text.trim() : "";
      return {
        scene: createScene(SceneTypes.OUTCOME_REFLECTED, { text: text || null, holdMs: reduceMotion ? 0 : 780 }),
        transition: createTransition(TransitionKinds.DRIFT, durationMs),
        audio: { kind: "complete" },
        haptic: { kind: "complete" },
      };
    }

    return null;
  };

  return { compose };
}

function chooseDurationMs(urgency) {
  const base = urgency === "high" ? 200 : urgency === "low" ? 520 : 360;
  return clamp(base, 120, 900);
}

function normalizeEnvelope(envelope) {
  if (!envelope || typeof envelope !== "object") return null;

  const type = typeof envelope.type === "string" ? envelope.type : null;
  const payload = envelope.payload && typeof envelope.payload === "object" ? envelope.payload : {};
  const urgency = normalizeUrgency(envelope.urgency);

  if (type) {
    return { type, payload, urgency };
  }

  const legacy = normalizeLegacyExperience(envelope);
  if (legacy) return legacy;

  return null;
}

function normalizeUrgency(value) {
  if (value === "high" || value === "low" || value === "normal") return value;
  return "normal";
}

function normalizeLegacyExperience(envelope) {
  const title = typeof envelope.title === "string" ? envelope.title.trim() : "";
  const body = typeof envelope.body === "string" ? envelope.body.trim() : "";
  const text = typeof envelope.text === "string" ? envelope.text.trim() : "";

  const content = text || body || title;
  if (!content) return null;

  if (looksLikeQuestion(content)) {
    return { type: "intent.clarify", payload: { text: content }, urgency: "normal" };
  }

  return { type: "outcome.reflected", payload: { text: content }, urgency: "normal" };
}

function looksLikeQuestion(text) {
  return /\\?$/.test(text) || /^what\\b|^which\\b|^would\\b|^do\\b|^can\\b/i.test(text);
}
