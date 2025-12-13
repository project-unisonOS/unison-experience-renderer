export function createHapticAdapter(preferences) {
  const enabled = preferences && preferences.hapticCues === true;
  const vibrate = globalThis.navigator && typeof globalThis.navigator.vibrate === "function" ? globalThis.navigator.vibrate.bind(globalThis.navigator) : null;

  const apply = (plan) => {
    if (!enabled) return;
    if (!vibrate) return;
    if (!plan || typeof plan.kind !== "string") return;
    if (plan.kind === "ack") vibrate([12]);
    if (plan.kind === "complete") vibrate([10, 40, 12]);
  };

  return { apply };
}

