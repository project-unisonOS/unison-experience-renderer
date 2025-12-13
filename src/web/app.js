import { createComposer } from "./composer.js";
import { createVisualAdapter } from "./modality/visual.js";
import { createAudioAdapter } from "./modality/audio.js";
import { createHapticAdapter } from "./modality/haptic.js";
import { createEventStream } from "./events.js";
import { fetchPreferences } from "./preferences.js";
import { SceneTypes, createScene, TransitionKinds, createTransition } from "./sceneGraph.js";

const field = document.getElementById("field");
const glyph = document.getElementById("glyph");
const question = document.getElementById("question");
const quietLabel = document.getElementById("quietLabel");

const modalities = {
  visual: createVisualAdapter({ field, glyph, question, quietLabel }),
  audio: null,
  haptic: null,
};

modalities.visual.present();

async function boot() {
  const personId = new URLSearchParams(window.location.search).get("person_id") || null;
  const preferences = await fetchPreferences({ personId });
  modalities.audio = createAudioAdapter(preferences);
  modalities.haptic = createHapticAdapter(preferences);
  const composer = createComposer({ preferences });

  await modalities.visual.apply(
    createScene(SceneTypes.PRESENCE, { cue: preferences.presenceCueVisual === true }),
    createTransition(TransitionKinds.FADE, preferences.reduceMotion === true ? 0 : 220),
  );

  if (preferences.presenceCueAudio === true) {
    modalities.audio.presence();
  }

  const stream = createEventStream({
    url: "/events/stream",
    onEvent: async (eventEnvelope) => {
      const plan = composer.compose(eventEnvelope);
      if (!plan) return;
      await modalities.visual.apply(plan.scene, plan.transition);
      modalities.audio.apply(plan.audio);
      modalities.haptic.apply(plan.haptic);
    },
  });

  stream.start();
}

boot();
