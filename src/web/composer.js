import { clamp } from "./util.js";
import { SceneTypes, TransitionKinds, createScene, createTransition } from "./sceneGraph.js";

export function createComposer({ preferences }) {
  const reduceMotion = preferences.reduceMotion === true;

  const compose = (envelope) => {
    const normalized = normalizeEnvelope(envelope);
    if (!normalized) return null;

    const { type, payload, urgency } = normalized;
    const durationMs = reduceMotion ? 0 : chooseDurationMs(urgency);

    if (
      type === "BOOT_START" ||
      type === "MANIFEST_LOADED" ||
      type === "IO_DISCOVERED" ||
      type === "RENDERER_READY" ||
      type === "SPEECH_READY" ||
      type === "SPEECH_UNAVAILABLE"
    ) {
      const logoUrl = typeof payload.logo === "string" ? payload.logo : typeof payload.logo_url === "string" ? payload.logo_url : null;
      const stageText =
        typeof payload.stage === "string"
          ? payload.stage
          : type === "BOOT_START"
            ? "Starting…"
            : type === "MANIFEST_LOADED"
              ? "Loading manifest…"
              : type === "IO_DISCOVERED"
                ? "Discovering IO…"
                : type === "RENDERER_READY"
                  ? "Renderer ready"
                  : type === "SPEECH_READY"
                    ? "Speech ready"
                    : type === "SPEECH_UNAVAILABLE"
                      ? "Speech unavailable"
                      : "Booting…";

      const earconUrl = typeof payload.startup_earcon === "string" ? payload.startup_earcon : null;

      return {
        scene: createScene(SceneTypes.BOOT, { logoUrl, stageText }),
        transition: createTransition(TransitionKinds.FADE, durationMs),
        audio: type === "MANIFEST_LOADED" ? { kind: "earcon", url: earconUrl } : null,
        haptic: null,
      };
    }

    if (type === "READY_LISTENING") {
      return {
        scene: createScene(SceneTypes.PRESENCE, { cue: preferences.presenceCueVisual === true }),
        transition: createTransition(TransitionKinds.FADE, durationMs),
        audio: null,
        haptic: null,
      };
    }

    if (type === "speech.partial") {
      const text = typeof payload.text === "string" ? payload.text.trim() : "";
      if (!text) return null;
      return {
        scene: createScene(SceneTypes.TRANSCRIPT, { text, hint: "Listening…" }),
        transition: createTransition(TransitionKinds.FOCUS_SHIFT, durationMs),
        audio: null,
        haptic: null,
      };
    }

    if (type === "tts.play") {
      const audioUrl = typeof payload.audio_url === "string" ? payload.audio_url : "";
      if (!audioUrl) return null;
      return { scene: null, transition: null, audio: { kind: "tts_play", url: audioUrl }, haptic: null };
    }

    if (type === "tts.stop") {
      return { scene: null, transition: null, audio: { kind: "tts_stop" }, haptic: null };
    }

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

    if (type === "actuation") {
      const lifecycle = payload && typeof payload.lifecycle === "string" ? payload.lifecycle : "";
      const action = payload && typeof payload.action === "string" ? payload.action : "";
      const status = payload && typeof payload.status === "string" ? payload.status : "";
      const text = [action, lifecycle || status].filter(Boolean).join(" · ");
      if (!text) return null;
      return {
        scene: createScene(SceneTypes.OUTCOME_REFLECTED, { text, holdMs: reduceMotion ? 0 : 780 }),
        transition: createTransition(TransitionKinds.DRIFT, durationMs),
        audio: null,
        haptic: null,
      };
    }

    if (type === "rom.render") {
      const romPayload = payload && typeof payload === "object" ? payload : {};
      const blocks = Array.isArray(romPayload.blocks) ? romPayload.blocks : [];
      const textBlock = blocks.find((b) => b && typeof b === "object" && b.type === "text" && typeof b.text === "string");
      const text = textBlock ? textBlock.text.trim() : "";
      if (text) {
        const directives =
          romPayload.meta && typeof romPayload.meta === "object" && romPayload.meta.renderer_directives && typeof romPayload.meta.renderer_directives === "object"
            ? romPayload.meta.renderer_directives
            : {};
        const visualDensity =
          typeof directives.visual_density === "string" && ["sparse", "balanced", "dense"].includes(directives.visual_density)
            ? directives.visual_density
            : "balanced";
        const layout = visualDensity === "dense" ? "center" : "quiet";
        return {
          scene: createScene(SceneTypes.OUTCOME_REFLECTED, { text, holdMs: reduceMotion ? 0 : 780, layout }),
          transition: createTransition(TransitionKinds.DRIFT, durationMs),
          audio: { kind: "complete" },
          haptic: { kind: "complete" },
        };
      }
      return null;
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
