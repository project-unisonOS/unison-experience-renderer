const STORAGE_KEY = "unison.renderer.preferences.v1";

export function loadPreferences() {
  const defaults = {
    presenceCueVisual: false,
    presenceCueAudio: false,
    hapticCues: false,
    reduceMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
  };

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaults;
    const parsed = JSON.parse(raw);
    return { ...defaults, ...(parsed && typeof parsed === "object" ? parsed : {}) };
  } catch (_) {
    return defaults;
  }
}
