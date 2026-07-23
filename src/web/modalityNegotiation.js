const SUPPORTED = new Set([
  "visual",
  "speech",
  "captions",
  "keyboard",
  "switch",
  "aac",
  "braille",
  "sign",
  "haptic",
]);

export function negotiateModalities({ available = [], required = [], avoided = [] } = {}) {
  const usable = [...new Set(available)].filter(
    (mode) => SUPPORTED.has(mode) && !avoided.includes(mode),
  );
  const missing = required.filter((mode) => !usable.includes(mode));
  if (missing.length) {
    return {
      status: "needs-fallback",
      selected: usable.includes("captions") ? ["captions"] : usable.includes("visual") ? ["visual"] : [],
      missing,
      semanticActionsPreserved: true,
    };
  }
  const selected = required.length ? required : usable;
  return {
    status: selected.length ? "ready" : "unavailable",
    selected,
    missing: [],
    semanticActionsPreserved: true,
  };
}

export function applyAdaptivePreferences(root, preferences = {}) {
  if (!root) return;
  root.dataset.highContrast = preferences.highContrast === true ? "true" : "false";
  root.dataset.simplifiedLanguage = preferences.simplifiedLanguage === true ? "true" : "false";
  root.dataset.reducedMotion = preferences.reduceMotion === true ? "true" : "false";
}
