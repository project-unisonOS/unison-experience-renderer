import os
import time
import json
import asyncio
import httpx
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, StreamingResponse

try:
    from unison_common import BatonMiddleware
except Exception:
    BatonMiddleware = None
from unison_common.multimodal import CapabilityClient
try:
    from wakeword import WakewordDetector, detectWakeWord  # type: ignore
except Exception:  # pragma: no cover
    # Fallback stub if module isn't importable (tests)
    class WakewordDetector:  # type: ignore
        def __init__(self, keyword="unison", threshold=0.9): self.keyword = keyword
        def setKeyword(self, keyword): self.keyword = keyword
        def processFrame(self, pcm): return False
    def detectWakeWord(detector, pcm): return False

app = FastAPI(title="unison-experience-renderer")
_disable_auth = os.getenv("DISABLE_AUTH_FOR_TESTS", "false").lower() in {"1", "true", "yes", "on"}
if BatonMiddleware and not _disable_auth:
    app.add_middleware(BatonMiddleware)
_started = time.time()
CAPABILITIES_URL = os.getenv("ORCHESTRATOR_CAPABILITIES_URL", "http://orchestrator:8080/capabilities")
_capability_client = CapabilityClient(CAPABILITIES_URL)
_experience_log: List[Dict[str, Any]] = []
_experience_log_max = 50
_experience_queue: asyncio.Queue = asyncio.Queue()
_context_base = os.getenv("CONTEXT_BASE_URL", "http://context:8081")
_context_role = os.getenv("UNISON_CONTEXT_ROLE", "service")
_context_headers = {"x-test-role": _context_role} if _context_role else {}
_speech_base = os.getenv("SPEECH_BASE_URL", "http://unison-io-speech:8084")
_orchestrator_base = os.getenv("ORCHESTRATOR_BASE_URL", "http://orchestrator:8080")
_wakeword_default = os.getenv("UNISON_WAKEWORD_DEFAULT", "unison")
_porcupine_access_key = os.getenv("PORCUPINE_ACCESS_KEY") or ""
_porcupine_keyword_b64 = os.getenv("PORCUPINE_KEYWORD_BASE64") or ""
_default_person_id = os.getenv("UNISON_DEFAULT_PERSON_ID", "local-user")
_test_mode = os.getenv("UNISON_UI_TEST_MODE", "false").lower() in {"1", "true", "yes", "on"}


@app.on_event("startup")
def _startup_refresh():
    _capability_client.refresh()
    if _test_mode:
        _seed_test_data()


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "service": "unison-experience-renderer", "uptime": time.time() - _started}


@app.get("/readyz")
@app.get("/ready")
def ready(request: Request):
    manifest_loaded = bool(_capability_client.manifest)
    displays = _capability_client.modality_count("displays")
    # Fall back to 1 display if manifest is missing or empty
    ready_flag = displays > 0 or not manifest_loaded
    if displays == 0:
        fallback = {"modalities": {"displays": [{"id": "default", "name": "fallback"}]}}
        _capability_client.manifest = fallback
        displays = _capability_client.modality_count("displays")
        ready_flag = True
    return {
        "ready": ready_flag,
        "checks": {
            "manifest_loaded": manifest_loaded,
            "displays": displays,
            "last_error": _capability_client.last_error,
        },
    }


@app.get("/capabilities")
def get_capabilities():
    manifest = _capability_client.manifest
    if manifest is None:
        raise HTTPException(status_code=503, detail="Capability manifest unavailable.")
    return {"manifest": manifest, "displays": _capability_client.modality_count("displays")}


@app.get("/wakeword")
def get_wakeword(person_id: str | None = None):
    """Fetch the active wake word from context profile; fallback to default."""
    pid = person_id or _default_person_id
    wakeword = _wakeword_default
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{_context_base}/profile/{pid}", headers=_context_headers or None)
            if resp.status_code == 200:
                body = resp.json() or {}
                profile = body.get("profile") or {}
                voice = profile.get("voice") or {}
                ww = voice.get("wakeword")
                if isinstance(ww, str) and ww.strip():
                    wakeword = ww.strip()
    except Exception:
        pass
    return {"wakeword": wakeword, "person_id": pid}


@app.post("/capabilities/refresh")
def refresh_capabilities():
    manifest = _capability_client.refresh()
    return {"ok": manifest is not None}


@app.post("/speech/stt")
def proxy_speech_stt(request: Request, body: Dict[str, Any] = Body(...)):
    """Proxy mic audio to the speech STT service with baton propagation."""
    audio_b64 = body.get("audio")
    person_id = body.get("person_id") or _default_person_id
    session_id = body.get("session_id") or "default-session"
    if not isinstance(audio_b64, str) or not audio_b64:
        raise HTTPException(status_code=400, detail="audio base64 string required")
    payload = {"audio": audio_b64, "person_id": person_id, "session_id": session_id}
    headers = {}
    baton = request.headers.get("X-Context-Baton")
    if baton:
        headers["X-Context-Baton"] = baton
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(f"{_speech_base}/speech/stt", json=payload, headers=headers or None)
            resp.raise_for_status()
            return resp.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="speech service unavailable")


@app.get("/dashboard")
def get_dashboard(person_id: str | None = None):
    pid = person_id or _default_person_id
    if not pid:
        raise HTTPException(status_code=400, detail="person_id required")
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{_context_base}/dashboard/{pid}", headers=_context_headers or None)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="dashboard unavailable")
            return resp.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="dashboard fetch failed")


@app.post("/payments/approvals")
def record_payment_approval(body: Dict[str, Any] = Body(...)):
    """Capture a payment approval intent for renderer-driven flows."""
    approval = {
        "txn_id": body.get("txn_id"),
        "approved": bool(body.get("approved")),
        "person_id": body.get("person_id") or _default_person_id,
        "surface": body.get("surface"),
        "timestamp": time.time(),
    }
    _experience_log.append({"type": "payment_approval", **approval})
    if len(_experience_log) > _experience_log_max:
        _experience_log.pop(0)
    return {"ok": True, "approval": approval}


@app.get("/payments/transactions/{txn_id}")
def get_payment_status(txn_id: str, person_id: str | None = None):
    """Proxy payment status from orchestrator for UI display."""
    pid = person_id or _default_person_id
    headers = {}
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{_orchestrator_base}/payments/transactions/{txn_id}", headers=headers or None)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="payment status unavailable")
            body = resp.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="orchestrator unavailable")
    txn = body.get("transaction") or {}
    _experience_log.append({"type": "payment_status", "person_id": pid, "transaction": txn, "timestamp": time.time()})
    if len(_experience_log) > _experience_log_max:
        _experience_log.pop(0)
    return {"ok": True, "transaction": txn}


@app.get("/", response_class=HTMLResponse)
def companion_ui():
    """
    Full-screen canvas for AI-driven experiences, informed by persona/preferences.
    """
    return """
    <html>
      <head>
        <title>Unison Companion</title>
        <style>
          html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; }
          :root { --unison-text-scale: 1; }
          body { font-family: 'Inter', system-ui, sans-serif; background: radial-gradient(circle at 20% 20%, #0b1224, #050915 45%, #02060f 85%); color: #e2e8f0; display: flex; flex-direction: column; font-size: calc(16px * var(--unison-text-scale)); }
          .hud { position: fixed; top: 20px; left: 20px; display: flex; gap: 10px; z-index: 10; }
          .pill { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); padding: 6px 14px; border-radius: 999px; font-size: 12px; color: #cbd5e1; }
          .pill-button { cursor: pointer; transition: background 0.2s ease, border-color 0.2s ease; }
          .pill-button:hover { background: rgba(255,255,255,0.12); border-color: rgba(255,255,255,0.16); }
          .canvas { flex: 1; display: grid; grid-template-columns: 2fr 1fr; grid-template-rows: 2fr 1fr 1fr; gap: 12px; padding: 32px; box-sizing: border-box; }
          .panel { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px; box-shadow: 0 8px 28px rgba(0,0,0,0.35); overflow: hidden; display: flex; flex-direction: column; }
          .panel h2 { margin: 0 0 8px 0; font-size: 16px; letter-spacing: 0.3px; color: #c7d2fe; }
          .panel .content { flex: 1; border-radius: 12px; background: rgba(0,0,0,0.12); padding: 12px; overflow: auto; }
          .media-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
          video, audio, img { width: 100%; border-radius: 12px; background: #0f172a; }
          #chat-stream { line-height: 1.5; }
          #tool-activity { font-family: monospace; white-space: pre-wrap; }
          .card { border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px; margin-bottom: 8px; background: rgba(255,255,255,0.03); }
          .card-header { font-weight: 700; margin-bottom: 6px; color: #cbd5e1; }
          .card-body { font-size: 14px; color: #e2e8f0; line-height: 1.4; }
          .card .media iframe, .card .media img, .card .media audio { width: 100%; border-radius: 10px; background: #0f172a; }
          body.dashboard-contrast-high { background: #020617; color: #f9fafb; }
          body.dashboard-contrast-high .panel { background: rgba(15,23,42,0.96); border-color: rgba(248,250,252,0.25); }
          body.dashboard-contrast-high .card { background: rgba(15,23,42,0.98); border-color: rgba(248,250,252,0.35); }
        </style>
        <script type="module">
          // Porcupine loader (browser-only, optional)
          const ACCESS_KEY = """ + json.dumps(_porcupine_access_key) + """;
          const KEYWORD_B64 = """ + json.dumps(_porcupine_keyword_b64) + """;
          window.__porcupineLoader = async () => {
            if (!ACCESS_KEY || !KEYWORD_B64) return null;
            try {
              const { PorcupineWeb } = await import("https://cdn.jsdelivr.net/npm/@picovoice/porcupine-web@2.2.2/dist/porcupine-web.esm.js");
              const keyword = { label: "wakeword", base64: KEYWORD_B64 };
              const engine = await PorcupineWeb.create(ACCESS_KEY, keyword);
              return engine;
            } catch (e) {
              console.warn("Porcupine load failed", e);
              return null;
            }
          };
        </script>
      </head>
      <body>
        <div class="hud">
          <div id="displays" class="pill">Displays: loading…</div>
          <div id="persona" class="pill">Persona: guest</div>
          <div id="status" class="pill">Status: idle</div>
          <div id="mic-status" class="pill">Mic: idle</div>
          <button id="mic-toggle" class="pill pill-button" type="button">Start Mic</button>
          <button id="mic-mute" class="pill pill-button" type="button">Mute Audio</button>
          <button id="mic-stop-audio" class="pill pill-button" type="button">Stop Audio</button>
        </div>
        <div class="canvas">
          <div class="panel" style="grid-row: 1 / span 2;">
            <h2>Media Canvas</h2>
            <div class="content media-grid">
              <div id="media-image"><img id="img-slot" alt="image slot" /></div>
              <div id="media-video"><video id="video-slot" controls></video></div>
              <div id="media-audio"><audio id="audio-slot" controls></audio></div>
              <div id="media-stream"><video id="stream-slot" autoplay muted></video></div>
            </div>
          </div>
          <div class="panel">
            <h2>Chat</h2>
            <div id="chat-stream" class="content">Waiting for input…</div>
          </div>
          <div class="panel">
            <h2>Tool Activity</h2>
            <div id="tool-activity" class="content">Idle</div>
          </div>
          <div class="panel" style="grid-column: 1 / span 2;">
            <h2>Priority Cards</h2>
            <div id="cards" class="content">Loading…</div>
          </div>
        </div>
        <script>
          const chatEl = document.getElementById('chat-stream');
          const toolsEl = document.getElementById('tool-activity');
          const personaEl = document.getElementById('persona');
          const statusEl = document.getElementById('status');
          const cardsEl = document.getElementById('cards');
          const micStatusEl = document.getElementById('mic-status');
          const micToggleEl = document.getElementById('mic-toggle');
          const micMuteEl = document.getElementById('mic-mute');
          const micStopAudioEl = document.getElementById('mic-stop-audio');
          const DEFAULT_PERSON_ID = """ + json.dumps(_default_person_id) + """;
          const SPEECH_BASE = """ + json.dumps(_speech_base) + """;
          let wakeword = """ + json.dumps(_wakeword_default) + """;
          const PORCUPINE_ENABLED = !!(""" + ("True" if _porcupine_access_key and _porcupine_keyword_b64 else "False") + """);
          let evtSource;
          let sessionId = localStorage.getItem('unison_session_id') || crypto.randomUUID();
          localStorage.setItem('unison_session_id', sessionId);
          let micStream = null;
          let mediaRecorder = null;
          let audioChunks = [];
          let analyser = null;
          let vadActive = false;
          let silenceMs = 0;
          const vadConfig = { start: 0.02, stop: 0.01, maxSilenceMs: 600, frameMs: 80 };
          let playQueue = [];
          let audioMuted = false;
          let wakeDetector = new WakewordDetector(wakeword);
          let porcupine = null;
          function escapeHtml(str) {
            return String(str)
              .replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#39;');
          }
          function safeMediaUrl(url, { embed=false } = {}) {
            if (!url) return '';
            try {
              const u = new URL(url, window.location.origin);
              if (u.protocol !== 'http:' && u.protocol !== 'https:') return '';
              const host = u.hostname.toLowerCase();
              if (embed) {
                // allowlist common embed hosts
                if (host.includes('youtube.com') || host === 'youtu.be') {
                  const id = u.searchParams.get('v') || u.pathname.split('/').pop();
                  return id ? `https://www.youtube.com/embed/${id}` : '';
                }
                if (host.includes('vimeo.com')) {
                  const id = u.pathname.split('/').filter(Boolean).pop();
                  return id ? `https://player.vimeo.com/video/${id}` : '';
                }
              }
              return u.href;
            } catch (e) {
              return '';
            }
          }
          function setMediaSrc(elId, url, opts) {
            const el = document.getElementById(elId);
            if (!el) return;
            const safe = safeMediaUrl(url, opts);
            el.src = safe || '';
          }
          function applyExperience(latest) {
            personaEl.textContent = `Persona: ${latest.person_id || 'guest'}`;
            statusEl.textContent = `Status: rendered ${new Date(latest.ts * 1000).toLocaleTimeString()}`;
            chatEl.textContent = latest.text || 'No text yet';
            toolsEl.textContent = latest.tool_activity || 'Idle';
            setMediaSrc('img-slot', latest.image_url);
            setMediaSrc('video-slot', latest.video_url);
            setMediaSrc('audio-slot', latest.audio_url);
            const audioEl = document.getElementById('audio-slot');
            if (audioEl && latest.audio_url) {
              playQueue.push(latest.audio_url);
              if (!audioEl.src || audioEl.ended) {
                const next = playQueue.shift();
                audioEl.src = next || '';
                audioEl.muted = audioMuted;
                audioEl.play().catch(() => {});
                audioEl.onended = () => {
                  if (playQueue.length) {
                    audioEl.src = playQueue.shift();
                    audioEl.play().catch(() => {});
                  }
                };
              }
            }
            setMediaSrc('stream-slot', latest.stream_url);
            if (Array.isArray(latest.cards)) {
              cardsEl.innerHTML = latest.cards.map(c => renderCard(c)).join('');
            }
          }

          function renderCard(card) {
            const type = escapeHtml(card.type || 'summary');
            const title = escapeHtml(card.title || type);
            const body = escapeHtml(card.body || '');
            let inner = '';
            if (type === 'media.embed') {
              const video = safeMediaUrl(card.video_url, { embed: true });
              const image = safeMediaUrl(card.image_url);
              const audio = safeMediaUrl(card.audio_url);
              if (video) inner += `<div class="media"><iframe src="${video}" allowfullscreen frameborder="0"></iframe></div>`;
              if (image) inner += `<div class="media"><img src="${image}" alt="image"/></div>`;
              if (audio) inner += `<div class="media"><audio controls src="${audio}"></audio></div>`;
            }
            if (type === 'guide') {
              const diagram = safeMediaUrl(card.diagram_url);
              if (diagram) inner += `<div class="media"><img src="${diagram}" alt="diagram"/></div>`;
              if (Array.isArray(card.steps)) inner += `<ol>${card.steps.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ol>`;
            }
            if (type === 'tool_result' && Array.isArray(card.items)) {
              inner += `<ul>${card.items.map(i => `<li><strong>${escapeHtml(i.title || '')}</strong>: ${escapeHtml(i.summary || '')}</li>`).join('')}</ul>`;
            }
            if (body) inner += `<p>${body}</p>`;
            return `<div class="card"><div class="card-header">${title}</div><div class="card-body">${inner}</div></div>`;
          }

          async function loadCapabilities() {
            try {
              const res = await fetch('/capabilities');
              if (!res.ok) { throw new Error('capabilities unavailable'); }
              const data = await res.json();
              const count = data.displays || (data.manifest && data.manifest.modalities && data.manifest.modalities.displays ? data.manifest.modalities.displays.length : 0);
              document.getElementById('displays').textContent = `${count} display(s) ready`;
            } catch (e) {
              document.getElementById('displays').textContent = 'Fallback display';
            }
          }

          async function loadExperiences() {
            try {
              const res = await fetch('/experiences');
              if (!res.ok) return;
              const data = await res.json();
              if (Array.isArray(data.items) && data.items.length > 0) {
                applyExperience(data.items[0]);
              }
            } catch (e) {}
          }
          async function loadDashboard() {
            try {
              const personId = new URLSearchParams(window.location.search).get('person_id') || window.DEFAULT_PERSON_ID || DEFAULT_PERSON_ID;
              window.DEFAULT_PERSON_ID = personId;
              const res = await fetch(`/dashboard?person_id=${encodeURIComponent(personId)}`);
              if (!res.ok) return;
              const data = await res.json();
              if (data.dashboard && Array.isArray(data.dashboard.cards)) {
                cardsEl.innerHTML = data.dashboard.cards.map(c => renderCard(c)).join('');
              }
              const prefs = data.dashboard && typeof data.dashboard.preferences === 'object' ? data.dashboard.preferences : null;
              if (prefs) {
                const rootStyle = document.documentElement.style;
                // Basic text scale preference; accept numeric or simple named values.
                let scale = prefs.text_scale;
                if (typeof scale === 'string') {
                  const lowered = scale.toLowerCase();
                  if (lowered === 'small') scale = 0.9;
                  else if (lowered === 'large') scale = 1.1;
                }
                if (typeof scale === 'number' && isFinite(scale)) {
                  const clamped = Math.min(1.4, Math.max(0.8, scale));
                  rootStyle.setProperty('--unison-text-scale', String(clamped));
                }
                const contrast = typeof prefs.contrast === 'string' ? prefs.contrast.toLowerCase() : null;
                if (contrast === 'high') {
                  document.body.classList.add('dashboard-contrast-high');
                } else if (contrast === 'normal' || contrast === 'default') {
                  document.body.classList.remove('dashboard-contrast-high');
                }
              }
            } catch (e) {}
          }

          async function refreshWakeword() {
            const personId = new URLSearchParams(window.location.search).get('person_id') || window.DEFAULT_PERSON_ID || DEFAULT_PERSON_ID;
            try {
              const res = await fetch(`/wakeword?person_id=${encodeURIComponent(personId)}`);
              if (res.ok) {
                const data = await res.json();
                if (data.wakeword) {
                  wakeword = data.wakeword;
                  wakeDetector.setKeyword(wakeword);
                  micStatusEl.textContent = `Mic: wake word "${wakeword}"`;
                }
              }
            } catch (e) {}
          }

          async function blobToBase64(blob) {
            return new Promise((resolve, reject) => {
              const reader = new FileReader();
              reader.onloadend = () => resolve(reader.result.split(',')[1]);
              reader.onerror = reject;
              reader.readAsDataURL(blob);
            });
          }

          async function sendAudioBlob(blob) {
            const b64 = await blobToBase64(blob);
            const personId = new URLSearchParams(window.location.search).get('person_id') || window.DEFAULT_PERSON_ID || DEFAULT_PERSON_ID;
            const payload = { audio: b64, person_id: personId, session_id: sessionId };
            micStatusEl.textContent = 'Mic: transcribing…';
            try {
              const res = await fetch('/speech/stt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
              });
              if (res.ok) {
                const data = await res.json();
                const t = data.transcript || '(no transcript)';
                chatEl.textContent = t;
                statusEl.textContent = `Status: transcribed @ ${new Date().toLocaleTimeString()}`;
              } else {
                micStatusEl.textContent = `Mic: STT error (${res.status})`;
                chatEl.textContent = 'Speech-to-text failed. Try again or type.';
              }
            } catch (e) {
              micStatusEl.textContent = 'Mic: STT failed';
              chatEl.textContent = 'Speech-to-text unavailable. Try again or type.';
            }
          }

          function stopRecording(send = true) {
            if (!mediaRecorder) return;
            const chunks = audioChunks.slice();
            mediaRecorder.onstop = () => {
              mediaRecorder = null;
              if (send && chunks.length) {
                const blob = new Blob(chunks, { type: 'audio/webm' });
                sendAudioBlob(blob);
              }
              audioChunks = [];
            };
            try { mediaRecorder.stop(); } catch (_) {}
          }

          function startRecording() {
            if (!micStream) return;
            if (mediaRecorder && mediaRecorder.state === 'recording') return;
            audioChunks = [];
            mediaRecorder = new MediaRecorder(micStream, { mimeType: 'audio/webm' });
            mediaRecorder.ondataavailable = (evt) => {
              if (evt.data && evt.data.size > 0) audioChunks.push(evt.data);
            };
            mediaRecorder.start();
            micStatusEl.textContent = 'Mic: recording…';
          }

          function analyseLoop() {
            if (!analyser || !vadActive) return;
            const data = new Uint8Array(analyser.fftSize);
            analyser.getByteTimeDomainData(data);
            let sum = 0;
            for (let i = 0; i < data.length; i++) {
              const v = (data[i] - 128) / 128;
              sum += v * v;
            }
            const rms = Math.sqrt(sum / data.length);
            if (!mediaRecorder && rms > vadConfig.start) {
              silenceMs = 0;
              startRecording();
            } else if (mediaRecorder) {
              if (rms < vadConfig.stop) {
                silenceMs += vadConfig.frameMs;
                if (silenceMs >= vadConfig.maxSilenceMs) {
                  stopRecording(true);
                  micStatusEl.textContent = 'Mic: listening…';
                }
              } else {
                silenceMs = 0;
              }
            }
            // Wake-word detection
            const pcm = new Float32Array(data.length);
            for (let i = 0; i < data.length; i++) {
              pcm[i] = (data[i] - 128) / 128;
            }
            if (porcupine && typeof porcupine.process === 'function') {
              // Downsample roughly to 16k by picking every 3rd sample (approx for 48k input)
              const step = 3;
              const downsized = new Int16Array(Math.floor(pcm.length / step));
              for (let i = 0, j = 0; i < pcm.length && j < downsized.length; i += step, j++) {
                let v = pcm[i];
                v = Math.max(-1, Math.min(1, v));
                downsized[j] = v * 32767;
              }
              try {
                const keywordIndex = porcupine.process(downsized);
                if (keywordIndex !== -1 && !mediaRecorder) {
                  micStatusEl.textContent = `Wake word "${wakeword}" detected`;
                  startRecording();
                }
              } catch (e) {
                // ignore processing errors to avoid UI spam
              }
            } else if (wakeDetector && typeof wakeDetector.processFrame === 'function') {
              const triggered = wakeDetector.processFrame(pcm);
              if (triggered && !mediaRecorder) {
                micStatusEl.textContent = `Wake word "${wakeword}" detected`;
                startRecording();
              }
            }
            requestAnimationFrame(analyseLoop);
          }

          async function startMic() {
            if (vadActive) return;
            try {
              micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
              const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
              const source = audioCtx.createMediaStreamSource(micStream);
              analyser = audioCtx.createAnalyser();
              analyser.fftSize = 2048;
              source.connect(analyser);
              if (PORCUPINE_ENABLED && window.__porcupineLoader) {
                porcupine = await window.__porcupineLoader();
                if (porcupine) micStatusEl.textContent = `Mic: wake word "${wakeword}" (porcupine)`;
              }
              vadActive = true;
              micStatusEl.textContent = 'Mic: listening…';
              micToggleEl.textContent = 'Stop Mic';
              analyseLoop();
            } catch (e) {
              micStatusEl.textContent = 'Mic: permission denied';
            }
          }

          function stopMic() {
            vadActive = false;
            stopRecording(false);
            if (micStream) {
              micStream.getTracks().forEach(t => t.stop());
            }
            micStream = null;
            analyser = null;
            micToggleEl.textContent = 'Start Mic';
            micStatusEl.textContent = 'Mic: idle';
          }

          micToggleEl?.addEventListener('click', () => {
            if (vadActive) {
              stopMic();
            } else {
              startMic();
            }
          });

          micMuteEl?.addEventListener('click', () => {
            audioMuted = !audioMuted;
            const audioEl = document.getElementById('audio-slot');
            if (audioEl) audioEl.muted = audioMuted;
            micMuteEl.textContent = audioMuted ? 'Unmute Audio' : 'Mute Audio';
          });

          micStopAudioEl?.addEventListener('click', () => {
            const audioEl = document.getElementById('audio-slot');
            playQueue = [];
            if (audioEl) {
              audioEl.pause();
              audioEl.currentTime = 0;
              audioEl.removeAttribute('src');
            }
          });

          function startStream() {
            try {
              evtSource = new EventSource('/experiences/stream');
              evtSource.onmessage = (ev) => {
                try { const data = JSON.parse(ev.data); applyExperience(data); } catch (_) {}
              };
              evtSource.onerror = () => {
                statusEl.textContent = 'Status: stream error (using cache)';
              };
            } catch (e) {}
          }
          loadCapabilities();
          loadExperiences();
          loadDashboard();
          startStream();
        </script>
      </body>
    </html>
    """


@app.post("/experiences")
def log_experience(body: Dict[str, Any] = Body(...)):
    """
    Store a rendered experience for future resurfacing.
    Body should include person_id, session_id, text, tool_activity, and media URLs.
    """
    payload = dict(body or {})
    # Preserve an explicit timestamp if provided; otherwise stamp now.
    payload.setdefault("ts", time.time())
    _experience_log.insert(0, payload)
    del _experience_log[_experience_log_max:]
    try:
        _experience_queue.put_nowait(payload)
    except Exception:
        pass
    # Persist to context dashboard if person_id present
    person_id = payload.get("person_id")
    if person_id:
        try:
            with httpx.Client(timeout=2.0) as client:
                client.post(
                    f"{_context_base}/dashboard/{person_id}",
                    json={"dashboard": {"cards": _experience_log[:10]}},
                    headers=_context_headers or None,
                )
        except Exception:
            pass
    return {"ok": True, "stored": len(_experience_log)}


@app.get("/experiences")
def list_experiences():
    return {"items": _experience_log}


@app.get("/experiences/stream")
async def stream_experiences():
    """
    Server-sent events (SSE) stream of new experiences.
    """
    async def event_generator():
        while True:
            item = await _experience_queue.get()
            yield f"data: {json.dumps(item)}\\n\\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _seed_test_data():
    """Populate experiences/dashboard with test persona and cards for UI/dev testing."""
    test_person = os.getenv("UNISON_TEST_PERSON_ID", "test-user")
    sample_cards = [
        {
            "id": "card-1",
            "type": "summary",
            "title": "Morning Briefing",
            "body": "3 meetings today. Standup at 9:00. Design review at 11:00.",
            "tool_activity": "calendar.refresh",
            "person_id": test_person,
            "ts": time.time(),
        },
        {
            "id": "card-2",
            "type": "comms",
            "title": "Priority Comms",
            "body": "2 replies pending: product questions from Alex; budget from Jamie.",
            "tool_activity": "comms.triage",
            "person_id": test_person,
            "ts": time.time(),
        },
        {
            "id": "card-3",
            "type": "tasks",
            "title": "Today’s Tasks",
            "body": "1) Draft project brief; 2) Send launch notes; 3) Confirm vendor.",
            "person_id": test_person,
            "ts": time.time(),
        },
    ]
    _experience_log[:] = sample_cards[:_experience_log_max]
    for card in sample_cards:
        try:
            _experience_queue.put_nowait(card)
        except Exception:
            pass
    # Persist to context if available
    try:
        with httpx.Client(timeout=2.0) as client:
            client.post(
                f"{_context_base}/dashboard/{test_person}",
                json={"dashboard": {"cards": sample_cards}},
                headers=_context_headers or None,
            )
    except Exception:
        pass
