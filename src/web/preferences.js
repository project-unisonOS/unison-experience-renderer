export function defaultPreferences() {
  return {
    presenceCueVisual: false,
    presenceCueAudio: false,
    hapticCues: false,
    reduceMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
  };
}

export async function fetchPreferences({ personId } = {}) {
  const defaults = defaultPreferences();
  const params = personId ? `?person_id=${encodeURIComponent(personId)}` : "";
  try {
    const res = await fetch(`/preferences${params}`, { method: "GET" });
    if (!res.ok) return defaults;
    const body = await res.json();
    const prefs = body && typeof body === "object" ? body.preferences : null;
    if (!prefs || typeof prefs !== "object") return defaults;
    return { ...defaults, ...prefs };
  } catch (_) {
    return defaults;
  }
}
