import { createComposer } from "./composer.js";
import { createVisualAdapter } from "./modality/visual.js";
import { createAudioAdapter } from "./modality/audio.js";
import { createHapticAdapter } from "./modality/haptic.js";
import { createEventStream } from "./events.js";
import { loadPreferences } from "./preferences.js";

const field = document.getElementById("field");
const glyph = document.getElementById("glyph");
const question = document.getElementById("question");
const quietLabel = document.getElementById("quietLabel");

const preferences = loadPreferences();
const modalities = {
  visual: createVisualAdapter({ field, glyph, question, quietLabel }),
  audio: createAudioAdapter(preferences),
  haptic: createHapticAdapter(preferences),
};

const composer = createComposer({ preferences });

modalities.visual.present();
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

