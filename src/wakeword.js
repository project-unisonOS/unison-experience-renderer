// Minimal wake-word detector placeholder.
// In production, replace `detectWakeWord` with a real model (e.g., WASM keyword spotter).
export class WakewordDetector {
  constructor(target = "unison", threshold = 0.9) {
    this.target = (target || "unison").toLowerCase();
    this.threshold = threshold;
    this.active = true;
  }

  setKeyword(keyword) {
    this.target = (keyword || "unison").toLowerCase();
  }

  /**
   * Naive detector: for now, return false (no detection).
   * Real implementations should consume audio frames and return true on keyword.
   */
  processFrame(_pcmFloat32Array) {
    if (!this.active) return false;
    return false;
  }
}

export function detectWakeWord(detector, pcm) {
  return detector && detector.processFrame(pcm);
}
