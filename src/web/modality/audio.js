export function createAudioAdapter(preferences) {
  const enabled = preferences && preferences.presenceCueAudio === true;
  let audioContext = null;

  const ensure = () => {
    if (!enabled) return null;
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
    if (!enabled) return;
    playTone(174.6, 120, 0.03);
    setTimeout(() => playTone(261.6, 140, 0.022), 70);
  };

  const apply = (plan) => {
    if (!enabled) return;
    if (!plan || typeof plan.kind !== "string") return;
    if (plan.kind === "ack") {
      playTone(233.1, 80, 0.022);
      return;
    }
    if (plan.kind === "question") {
      playTone(196.0, 90, 0.02);
      setTimeout(() => playTone(246.9, 110, 0.02), 65);
      return;
    }
    if (plan.kind === "complete") {
      playTone(293.7, 90, 0.02);
      setTimeout(() => playTone(220.0, 140, 0.02), 75);
      return;
    }
  };

  return { presence, apply };
}

