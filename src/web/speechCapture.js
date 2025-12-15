function base64FromInt16(int16) {
  const bytes = new Uint8Array(int16.buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    const slice = bytes.subarray(i, i + chunk);
    binary += String.fromCharCode.apply(null, slice);
  }
  return btoa(binary);
}

function downsampleFloat32ToInt16(input, inputSampleRate, targetRate) {
  if (!input || input.length === 0) return new Int16Array(0);
  if (!inputSampleRate || inputSampleRate <= 0) return new Int16Array(0);
  if (!targetRate || targetRate <= 0) targetRate = inputSampleRate;
  if (targetRate === inputSampleRate) {
    const out = new Int16Array(input.length);
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }

  const ratio = inputSampleRate / targetRate;
  const outLen = Math.floor(input.length / ratio);
  const out = new Int16Array(outLen);
  let pos = 0;
  for (let i = 0; i < outLen; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j++) {
      sum += input[j];
      count++;
    }
    const sample = count > 0 ? sum / count : 0;
    const clamped = Math.max(-1, Math.min(1, sample));
    out[pos++] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
  }
  return out;
}

export function resolveSpeechWsUrl(rawUrl) {
  const host = window.location.hostname || "localhost";
  try {
    const u = new URL(rawUrl);
    // Replace container hostnames with the browser's current hostname.
    if (u.hostname === "io-speech" || u.hostname === "unison-io-speech") {
      u.hostname = host;
    }
    return u.toString();
  } catch (_) {
    return `ws://${host}:8084/stream`;
  }
}

export function createSpeechCapture() {
  let ws = null;
  let audioContext = null;
  let source = null;
  let processor = null;
  let sink = null;
  let stream = null;
  let running = false;
  let sequence = 0;

  const start = async ({ wsUrl, endpointing, asrProfile }) => {
    if (running) return;
    running = true;

    const resolved = resolveSpeechWsUrl(wsUrl || "");
    ws = new WebSocket(resolved);

    ws.onopen = async () => {
      try {
        ws.send(
          JSON.stringify({
            type: "control",
            action: "start_listening",
            timestamp: Date.now(),
            endpointing: endpointing || null,
            asr_profile: asrProfile || null,
          }),
        );
      } catch (_) {}

      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      } catch (err) {
        running = false;
        try {
          ws.close();
        } catch (_) {}
        ws = null;
        throw err;
      }

      const Ctx = globalThis.AudioContext || globalThis.webkitAudioContext;
      audioContext = new Ctx({ sampleRate: 16000 });
      source = audioContext.createMediaStreamSource(stream);
      processor = audioContext.createScriptProcessor(4096, 1, 1);
      sink = audioContext.createGain();
      sink.gain.value = 0;

      processor.onaudioprocess = (e) => {
        if (!ws || ws.readyState !== 1) return;
        const input = e.inputBuffer.getChannelData(0);
        const pcm16 = downsampleFloat32ToInt16(input, audioContext.sampleRate, 16000);
        if (!pcm16 || pcm16.length === 0) return;
        const b64 = base64FromInt16(pcm16);
        ws.send(
          JSON.stringify({
            type: "audio",
            data: b64,
            timestamp: Date.now(),
            sequence: sequence++,
          }),
        );
      };

      source.connect(processor);
      processor.connect(sink);
      sink.connect(audioContext.destination);
    };

    ws.onerror = () => {};
    ws.onclose = () => {
      running = false;
    };
  };

  const stop = async () => {
    running = false;
    try {
      if (ws && ws.readyState === 1) {
        ws.send(JSON.stringify({ type: "control", action: "stop_listening", timestamp: Date.now() }));
      }
    } catch (_) {}
    try {
      ws && ws.close();
    } catch (_) {}
    ws = null;
    try {
      processor && processor.disconnect();
    } catch (_) {}
    try {
      source && source.disconnect();
    } catch (_) {}
    try {
      sink && sink.disconnect();
    } catch (_) {}
    processor = null;
    source = null;
    sink = null;
    try {
      audioContext && audioContext.close();
    } catch (_) {}
    audioContext = null;
    try {
      if (stream) {
        for (const track of stream.getTracks()) track.stop();
      }
    } catch (_) {}
    stream = null;
  };

  return { start, stop };
}
