import os
import time
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

try:
    from unison_common import BatonMiddleware
except Exception:
    BatonMiddleware = None
from unison_common.multimodal import CapabilityClient

app = FastAPI(title="unison-experience-renderer")

_disable_auth = os.getenv("DISABLE_AUTH_FOR_TESTS", "false").lower() in {"1", "true", "yes", "on"}
if BatonMiddleware and not _disable_auth:
    app.add_middleware(BatonMiddleware)

_started = time.time()
_here = Path(__file__).resolve().parent
_web_root = _here / "web"
app.mount("/static", StaticFiles(directory=str(_web_root), html=False), name="static")

CAPABILITIES_URL = os.getenv("ORCHESTRATOR_CAPABILITIES_URL", "http://orchestrator:8080/capabilities")
_capability_client = CapabilityClient(CAPABILITIES_URL)

_context_base = os.getenv("CONTEXT_BASE_URL", "http://context:8081")
_context_role = os.getenv("UNISON_CONTEXT_ROLE", "service")
_context_headers = {"x-test-role": _context_role} if _context_role else {}

_speech_base = os.getenv("SPEECH_BASE_URL", "http://unison-io-speech:8084")
_orchestrator_base = os.getenv("ORCHESTRATOR_BASE_URL", "http://orchestrator:8080")

_wakeword_default = os.getenv("UNISON_WAKEWORD_DEFAULT", "unison")
_default_person_id = os.getenv("UNISON_DEFAULT_PERSON_ID", "local-person")

_test_mode = os.getenv("UNISON_RENDERER_TEST_MODE", os.getenv("UNISON_UI_TEST_MODE", "false")).lower() in {"1", "true", "yes", "on"}

_event_log: List[Dict[str, Any]] = []
_event_log_max = 50
_event_queue: asyncio.Queue = asyncio.Queue()

_actuation_log: List[Dict[str, Any]] = []
_actuation_log_max = 50


@app.on_event("startup")
def _startup_refresh():
    _capability_client.refresh()
    if _test_mode:
        _seed_test_data()


@app.get("/", response_class=FileResponse)
def renderer_surface():
    return FileResponse(str(_web_root / "index.html"))


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "service": "unison-experience-renderer", "uptime": time.time() - _started}


@app.get("/readyz")
@app.get("/ready")
def ready(request: Request):
    manifest_loaded = bool(_capability_client.manifest)
    displays = _capability_client.modality_count("displays")
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


@app.post("/capabilities/refresh")
def refresh_capabilities():
    manifest = _capability_client.refresh()
    return {"ok": manifest is not None}


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
    envelope = {"type": "payment.approval", "payload": approval, "ts": time.time()}
    _record_envelope(envelope)
    return {"ok": True, "approval": approval}


@app.get("/payments/transactions/{txn_id}")
def get_payment_status(txn_id: str, person_id: str | None = None):
    """Proxy payment status from orchestrator for renderer consumption."""
    pid = person_id or _default_person_id
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{_orchestrator_base}/payments/transactions/{txn_id}")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="payment status unavailable")
            body = resp.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="orchestrator unavailable")
    txn = body.get("transaction") or {}
    envelope = {"type": "payment.status", "payload": {"person_id": pid, "transaction": txn, "timestamp": time.time()}, "ts": time.time()}
    _record_envelope(envelope)
    return {"ok": True, "transaction": txn}


@app.post("/events")
@app.post("/experiences")
def ingest_event(body: Dict[str, Any] = Body(...)):
    """
    Ingest an intent or experience envelope for composition on the renderer surface.

    Supported shapes:
    - Canonical envelope: {"type": "...", "payload": {...}, "urgency": "low|normal|high"}
    - Legacy envelope: arbitrary JSON; the client composer applies a best-effort mapping.
    """
    envelope = dict(body or {})
    envelope.setdefault("ts", time.time())
    _record_envelope(envelope)
    return {"ok": True, "stored": len(_event_log)}


@app.get("/events")
@app.get("/experiences")
def list_events():
    return {"items": _event_log}


@app.post("/telemetry/actuation")
def actuation_telemetry(event: Dict[str, Any] = Body(...)):
    """Accept actuation lifecycle events and surface them to the renderer stream."""
    evt = dict(event or {})
    evt.setdefault("ts", time.time())
    evt.setdefault("type", "actuation")
    _actuation_log.insert(0, evt)
    del _actuation_log[_actuation_log_max:]
    _record_envelope({"type": "actuation", "payload": evt, "ts": evt["ts"]})
    return {"ok": True, "stored": len(_actuation_log)}


@app.get("/telemetry/actuation")
def list_actuation_telemetry():
    return {"items": _actuation_log}


@app.get("/events/stream")
@app.get("/experiences/stream")
async def stream_events():
    """Server-sent events (SSE) stream of incoming envelopes."""

    async def event_generator():
        while True:
            item = await _event_queue.get()
            yield f"data: {json.dumps(item)}\\n\\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def _record_envelope(envelope: Dict[str, Any]) -> None:
    _event_log.insert(0, envelope)
    del _event_log[_event_log_max:]
    try:
        _event_queue.put_nowait(envelope)
    except Exception:
        pass


def _seed_test_data():
    """Populate the stream with a small set of envelopes for local testing."""
    test_person = os.getenv("UNISON_TEST_PERSON_ID", "test-person")
    sample = [
        {"type": "presence", "payload": {"person_id": test_person}, "ts": time.time()},
        {"type": "intent.recognized", "payload": {"person_id": test_person}, "ts": time.time()},
        {"type": "intent.clarify", "payload": {"text": "What outcome matters most right now?", "person_id": test_person}, "ts": time.time()},
        {"type": "outcome.reflected", "payload": {"text": "Done.", "person_id": test_person}, "ts": time.time()},
    ]
    for envelope in sample:
        _record_envelope(envelope)

