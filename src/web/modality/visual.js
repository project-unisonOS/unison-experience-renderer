import { fadeIn, fadeOut, waitMs } from "../motion.js";

export function createVisualAdapter({ field, glyph, logo, question, quietLabel }) {
  const present = () => {
    field.dataset.scene = "presence";
    field.dataset.motion = "none";
    question.textContent = "";
    quietLabel.textContent = "";
    quietLabel.style.opacity = "0";
    if (logo) {
      logo.removeAttribute("src");
      logo.classList.remove("on");
      logo.style.opacity = "0";
    }
    glyph.classList.remove("on");
    glyph.classList.remove("presence-cue");
  };

  const apply = async (scene, transition) => {
    if (!scene || typeof scene.type !== "string") return;
    const durationMs = transition && typeof transition.durationMs === "number" ? transition.durationMs : 0;
    field.dataset.motion = transition && typeof transition.kind === "string" ? transition.kind : "none";

    if (scene.type === "boot") {
      field.dataset.scene = "boot";
      glyph.classList.remove("presence-cue");
      await fadeOut(glyph, durationMs);
      await fadeOut(question, durationMs);
      if (logo) {
        const src = typeof scene.payload?.logoUrl === "string" ? scene.payload.logoUrl : "";
        if (src && logo.getAttribute("src") !== src) {
          logo.setAttribute("src", src);
        }
        logo.classList.add("on");
      }
      const stage = typeof scene.payload?.stageText === "string" ? scene.payload.stageText : "";
      if (stage) {
        quietLabel.textContent = stage;
        quietLabel.style.opacity = "0";
        await waitMs(20);
        quietLabel.style.opacity = "1";
      } else {
        quietLabel.textContent = "";
        quietLabel.style.opacity = "0";
      }
      return;
    }

    if (scene.type === "presence") {
      present();
      if (scene.payload && scene.payload.cue === true) {
        glyph.classList.add("presence-cue");
        await fadeIn(glyph, durationMs);
      }
      return;
    }

    if (scene.type === "onboarding") {
      field.dataset.scene = "onboarding";
      glyph.classList.remove("presence-cue");
      if (logo) {
        logo.classList.remove("on");
      }
      await fadeOut(glyph, durationMs);
      const title = typeof scene.payload?.title === "string" ? scene.payload.title.trim() : "";
      const body = typeof scene.payload?.body === "string" ? scene.payload.body.trim() : "";
      question.textContent = [title, body].filter(Boolean).join("\n\n");
      await fadeIn(question, durationMs);
      const detail = typeof scene.payload?.detail === "string" ? scene.payload.detail.trim() : "";
      quietLabel.textContent = detail;
      quietLabel.style.opacity = detail ? "1" : "0";
      return;
    }

    if (scene.type === "transcript") {
      field.dataset.scene = "transcript";
      glyph.classList.remove("presence-cue");
      if (logo) {
        logo.classList.remove("on");
      }
      await fadeOut(glyph, durationMs);
      question.textContent = typeof scene.payload?.text === "string" ? scene.payload.text : "";
      await fadeIn(question, durationMs);
      const hint = typeof scene.payload?.hint === "string" ? scene.payload.hint : "";
      if (hint) {
        quietLabel.textContent = hint;
        quietLabel.style.opacity = "1";
      } else {
        quietLabel.textContent = "";
        quietLabel.style.opacity = "0";
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
      const layout = typeof scene.payload?.layout === "string" ? scene.payload.layout : "quiet";
      const text = typeof scene.payload?.text === "string" ? scene.payload.text.trim() : "";
      if (layout === "center") {
        quietLabel.textContent = "";
        quietLabel.style.opacity = "0";
        question.textContent = text;
        await fadeIn(question, durationMs);
      } else if (text) {
        question.textContent = "";
        quietLabel.textContent = text;
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
      await fadeOut(question, durationMs);
      await fadeOut(glyph, durationMs);
      return;
    }
  };

  return { present, apply };
}
