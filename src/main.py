import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
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


@app.on_event("startup")
def _startup_refresh():
    _capability_client.refresh()


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


@app.get("/", response_class=HTMLResponse)
def companion_ui():
    """
    Minimal companion display stub.
    Shows manifest display count and placeholders for chat/tool activity.
    """
    return """
    <html>
      <head>
        <title>Unison Companion</title>
        <style>
          body { font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 16px; }
          .card { background: #1e293b; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.2); }
          .title { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
          .subtitle { color: #94a3b8; margin-bottom: 12px; }
          .pill { display: inline-block; background: #334155; color: #cbd5e1; padding: 4px 10px; border-radius: 999px; margin-right: 6px; font-size: 12px; }
        </style>
      </head>
      <body>
        <div class="card">
          <div class="title">Unison Companion</div>
          <div class="subtitle">Always-on chat + tool activity</div>
          <div id="displays" class="pill">Loading displays…</div>
        </div>
        <div class="card">
          <div class="title">Chat</div>
          <div id="chat">Waiting for input…</div>
        </div>
        <div class="card">
          <div class="title">Tool Activity</div>
          <div id="tools">Idle</div>
        </div>
        <script>
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
          loadCapabilities();
        </script>
      </body>
    </html>
    """
