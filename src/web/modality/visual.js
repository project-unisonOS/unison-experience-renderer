import { fadeIn, fadeOut, waitMs } from "../motion.js";

export function createVisualAdapter({ field, glyph, question, quietLabel }) {
  const present = () => {
    field.dataset.scene = "presence";
    field.dataset.motion = "none";
    question.textContent = "";
    quietLabel.textContent = "";
    quietLabel.style.opacity = "0";
    glyph.classList.remove("on");
    glyph.classList.remove("presence-cue");
  };

  const apply = async (scene, transition) => {
    if (!scene || typeof scene.type !== "string") return;
    const durationMs = transition && typeof transition.durationMs === "number" ? transition.durationMs : 0;
    field.dataset.motion = transition && typeof transition.kind === "string" ? transition.kind : "none";

    if (scene.type === "presence") {
      present();
      if (scene.payload && scene.payload.cue === true) {
        glyph.classList.add("presence-cue");
        await fadeIn(glyph, durationMs);
      }
      return;
    }

    if (scene.type === "intent.recognized") {
      field.dataset.scene = "intent.recognized";
      question.textContent = "";
      await fadeOut(question, durationMs);
      glyph.classList.remove("presence-cue");
      await fadeIn(glyph, durationMs);
      const holdMs = typeof scene.payload?.holdMs === "number" ? scene.payload.holdMs : 520;
      if (holdMs > 0) await waitMs(holdMs);
      await fadeOut(glyph, durationMs);
      return;
    }

    if (scene.type === "intent.clarify") {
      field.dataset.scene = "intent.clarify";
      glyph.classList.remove("presence-cue");
      await fadeOut(glyph, durationMs);
      question.textContent = scene.payload?.text || "";
      await fadeIn(question, durationMs);
      return;
    }

    if (scene.type === "outcome.reflected") {
      field.dataset.scene = "outcome.reflected";
      glyph.classList.remove("presence-cue");
      await fadeOut(question, durationMs);
      await fadeIn(glyph, durationMs);
      if (typeof scene.payload?.text === "string" && scene.payload.text.trim()) {
        quietLabel.textContent = scene.payload.text.trim();
        quietLabel.style.opacity = "0";
        await waitMs(20);
        quietLabel.style.opacity = "1";
      } else {
        quietLabel.textContent = "";
        quietLabel.style.opacity = "0";
      }
      const holdMs = typeof scene.payload?.holdMs === "number" ? scene.payload.holdMs : 780;
      if (holdMs > 0) await waitMs(holdMs);
      quietLabel.style.opacity = "0";
      await fadeOut(glyph, durationMs);
      return;
    }
  };

  return { present, apply };
}

