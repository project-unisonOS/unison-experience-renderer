export function createAudioAdapter(preferences) {
  const cuesEnabled = preferences && preferences.presenceCueAudio === true;
  let audioContext = null;
  let earconAudio = null;
  let ttsAudio = null;

  const ensure = () => {
    if (!cuesEnabled) return null;
    if (audioContext) return audioContext;
    const Ctx = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (!Ctx) return null;
    audioContext = new Ctx();
    return audioContext;
  };

  const playTone = (hz, ms, gain = 0.05) => {
    const ctx = ensure();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = hz;
    amp.gain.setValueAtTime(0.0001, now);
    amp.gain.exponentialRampToValueAtTime(gain, now + 0.02);
    amp.gain.exponentialRampToValueAtTime(0.0001, now + ms / 1000);
    osc.connect(amp);
    amp.connect(ctx.destination);
    osc.start(now);
    osc.stop(now + ms / 1000 + 0.02);
  };

  const presence = () => {
    if (!cuesEnabled) return;
    // Audio contexts may require a gesture; fail silently.
    playTone(174.6, 120, 0.03);
    setTimeout(() => playTone(261.6, 140, 0.022), 70);
  };

  const apply = (plan) => {
    if (!plan || typeof plan.kind !== "string") return;
    if (plan.kind === "earcon") {
      if (!cuesEnabled) return;
      const url = typeof plan.url === "string" ? plan.url : "";
      if (url) {
        try {
          if (earconAudio) {
            earconAudio.pause();
            earconAudio.currentTime = 0;
          }
          earconAudio = new Audio(url);
          earconAudio.volume = 0.6;
          earconAudio.play().catch(() => {});
          return;
        } catch (_) {}
      }
      playTone(174.6, 120, 0.03);
      setTimeout(() => playTone(261.6, 140, 0.022), 70);
      return;
    }
    if (plan.kind === "ack") {
      if (!cuesEnabled) return;
      playTone(233.1, 80, 0.022);
      return;
    }
    if (plan.kind === "question") {
      if (!cuesEnabled) return;
      playTone(196.0, 90, 0.02);
      setTimeout(() => playTone(246.9, 110, 0.02), 65);
      return;
    }
    if (plan.kind === "complete") {
      if (!cuesEnabled) return;
      playTone(293.7, 90, 0.02);
      setTimeout(() => playTone(220.0, 140, 0.02), 75);
      return;
    }
    if (plan.kind === "tts_play") {
      const url = typeof plan.url === "string" ? plan.url : "";
      if (!url) return;
      try {
        if (ttsAudio) {
          ttsAudio.pause();
          ttsAudio.currentTime = 0;
        }
        ttsAudio = new Audio(url);
        ttsAudio.volume = 0.9;
        ttsAudio.play().catch(() => {});
      } catch (_) {}
      return;
    }
    if (plan.kind === "tts_stop") {
      try {
        if (ttsAudio) {
          ttsAudio.pause();
          ttsAudio.currentTime = 0;
        }
      } catch (_) {}
      return;
    }
  };

  return { presence, apply };
}
