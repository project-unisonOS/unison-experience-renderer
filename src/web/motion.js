export function waitMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function fadeIn(element, durationMs) {
  if (!element) return;
  if (durationMs <= 0) {
    element.classList.add("on");
    return;
  }
  element.classList.add("on");
  await waitMs(durationMs);
}

export async function fadeOut(element, durationMs) {
  if (!element) return;
  if (durationMs <= 0) {
    element.classList.remove("on");
    return;
  }
  element.classList.remove("on");
  await waitMs(durationMs);
}

