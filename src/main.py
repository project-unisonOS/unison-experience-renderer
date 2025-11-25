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

app = FastAPI(title="unison-experience-renderer")
if BatonMiddleware:
    app.add_middleware(BatonMiddleware)
_started = time.time()
CAPABILITIES_URL = os.getenv("ORCHESTRATOR_CAPABILITIES_URL", "http://orchestrator:8080/capabilities")
_capability_client = CapabilityClient(CAPABILITIES_URL)
_experience_log: List[Dict[str, Any]] = []
_experience_log_max = 50
_experience_queue: asyncio.Queue = asyncio.Queue()
_context_base = os.getenv("CONTEXT_BASE_URL", "http://context:8081")
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
    # Fall back to 1 display if manifest is missing
    ready_flag = displays > 0 or not manifest_loaded
    # If probe failed, fall back to default display manifest
    if not manifest_loaded and displays == 0:
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


@app.post("/capabilities/refresh")
def refresh_capabilities():
    manifest = _capability_client.refresh()
    return {"ok": manifest is not None}


@app.get("/dashboard")
def get_dashboard(person_id: str | None = None):
    pid = person_id or _default_person_id
    if not pid:
        raise HTTPException(status_code=400, detail="person_id required")
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{_context_base}/dashboard/{pid}")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="dashboard unavailable")
            return resp.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="dashboard fetch failed")


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
          body { font-family: 'Inter', system-ui, sans-serif; background: radial-gradient(circle at 20% 20%, #0b1224, #050915 45%, #02060f 85%); color: #e2e8f0; display: flex; flex-direction: column; }
          .hud { position: fixed; top: 20px; left: 20px; display: flex; gap: 10px; z-index: 10; }
          .pill { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); padding: 6px 14px; border-radius: 999px; font-size: 12px; color: #cbd5e1; }
          .canvas { flex: 1; display: grid; grid-template-columns: 2fr 1fr; grid-template-rows: 2fr 1fr; gap: 12px; padding: 32px; box-sizing: border-box; }
          .panel { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px; box-shadow: 0 8px 28px rgba(0,0,0,0.35); overflow: hidden; display: flex; flex-direction: column; }
          .panel h2 { margin: 0 0 8px 0; font-size: 16px; letter-spacing: 0.3px; color: #c7d2fe; }
          .panel .content { flex: 1; border-radius: 12px; background: rgba(0,0,0,0.12); padding: 12px; overflow: auto; }
          .media-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
          video, audio, img { width: 100%; border-radius: 12px; background: #0f172a; }
          #chat-stream { line-height: 1.5; }
          #tool-activity { font-family: monospace; white-space: pre-wrap; }
        </style>
      </head>
      <body>
        <div class="hud">
          <div id="displays" class="pill">Displays: loading…</div>
          <div id="persona" class="pill">Persona: guest</div>
          <div id="status" class="pill">Status: idle</div>
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
        </div>
        <script>
          const chatEl = document.getElementById('chat-stream');
          const toolsEl = document.getElementById('tool-activity');
          const personaEl = document.getElementById('persona');
          const statusEl = document.getElementById('status');
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
          let evtSource;
          function applyExperience(latest) {
            personaEl.textContent = `Persona: ${latest.person_id || 'guest'}`;
            statusEl.textContent = `Status: rendered ${new Date(latest.ts * 1000).toLocaleTimeString()}`;
            chatEl.textContent = latest.text || 'No text yet';
            toolsEl.textContent = latest.tool_activity || 'Idle';
            if (latest.image_url) document.getElementById('img-slot').src = latest.image_url;
            if (latest.video_url) document.getElementById('video-slot').src = latest.video_url;
            if (latest.audio_url) document.getElementById('audio-slot').src = latest.audio_url;
            if (latest.stream_url) document.getElementById('stream-slot').src = latest.stream_url;
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
              const res = await fetch(`/dashboard?person_id=${encodeURIComponent(window.DEFAULT_PERSON_ID || '')}`);
              if (!res.ok) return;
              const data = await res.json();
              if (data.dashboard && Array.isArray(data.dashboard.cards)) {
                applyExperience(data.dashboard.cards[0]);
              }
            } catch (e) {}
          }
          function startStream() {
            try {
              evtSource = new EventSource('/experiences/stream');
              evtSource.onmessage = (ev) => {
                try { const data = JSON.parse(ev.data); applyExperience(data); } catch (_) {}
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
    payload["ts"] = time.time()
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
                client.post(f"{_context_base}/dashboard/{person_id}", json={"dashboard": {"cards": _experience_log[:10]}})
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
            client.post(f"{_context_base}/dashboard/{test_person}", json={"dashboard": {"cards": sample_cards}})
    except Exception:
        pass
