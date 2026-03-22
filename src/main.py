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
from unison_common.redaction import redact_obj

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
_context_profile_cache_seconds = float(os.getenv("RENDERER_CONTEXT_PROFILE_CACHE_SECONDS", "1.0"))
_context_profile_cache: Dict[str, Dict[str, Any]] = {}
_context_profile_cache_ts: Dict[str, float] = {}
_context_client: httpx.Client | None = None

_speech_base = os.getenv("SPEECH_BASE_URL", "http://unison-io-speech:8084")
_orchestrator_base = os.getenv("ORCHESTRATOR_BASE_URL", "http://orchestrator:8080")
_inference_base = os.getenv("INFERENCE_BASE_URL", "http://inference:8087")
_auth_base = os.getenv("AUTH_BASE_URL", "http://auth:8083")

_wakeword_default = os.getenv("UNISON_WAKEWORD_DEFAULT", "unison")
_default_person_id = os.getenv("UNISON_DEFAULT_PERSON_ID", "local-person")

_test_mode = os.getenv("UNISON_RENDERER_TEST_MODE", os.getenv("UNISON_UI_TEST_MODE", "false")).lower() in {"1", "true", "yes", "on"}

_event_log: List[Dict[str, Any]] = []
_event_log_max = 50
_event_queue: asyncio.Queue = asyncio.Queue()

_actuation_log: List[Dict[str, Any]] = []
_actuation_log_max = 50

_build_sha = os.getenv("UNISON_RENDERER_BUILD_SHA", "unknown")
_build_time = os.getenv("UNISON_RENDERER_BUILD_TIME", "unknown")
_build_source = os.getenv("UNISON_RENDERER_BUILD_SOURCE", "workspace")
_dev_watermark = os.getenv("UNISON_RENDERER_DEV_WATERMARK", "false").lower() in {"1", "true", "yes", "on"}


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
    return {
        "status": "ok",
        "service": "unison-experience-renderer",
        "uptime": time.time() - _started,
        "build": {"sha": _build_sha, "time": _build_time, "source": _build_source},
    }


@app.get("/meta")
def meta(request: Request):
    """
    Lightweight build/runtime metadata for dev verification.

    This is intended to prevent confusion about what renderer bundle is actually running.
    """
    hostname = os.getenv("HOSTNAME", "")
    return {
        "service": "unison-experience-renderer",
        "repo": "unison-experience-renderer",
        "build": {"sha": _build_sha, "time": _build_time, "source": _build_source},
        "runtime": {"hostname": hostname},
        "dev": {"watermark": _dev_watermark},
    }


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
        profile = _get_cached_profile(pid)
        voice = profile.get("voice") or {}
        ww = voice.get("wakeword")
        if isinstance(ww, str) and ww.strip():
            wakeword = ww.strip()
    except Exception:
        pass
    return {"wakeword": wakeword, "person_id": pid}


@app.get("/preferences")
def get_preferences(person_id: str | None = None):
    """
    Fetch renderer preferences from context profile.

    This keeps preferences modality-independent and avoids local-only state.
    """
    pid = person_id or _default_person_id
    prefs: Dict[str, Any] = {}
    try:
        profile = _get_cached_profile(pid)
        if isinstance(profile, dict):
            prefs = _extract_renderer_preferences(profile)
    except Exception:
        prefs = {}
    return {"ok": True, "person_id": pid, "preferences": prefs}


@app.get("/startup-status")
def get_startup_status():
    """Proxy orchestrator startup status for renderer-led first-run onboarding."""
    try:
        with httpx.Client(timeout=2.5) as client:
            resp = client.get(f"{_orchestrator_base}/startup/status")
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="startup status unavailable")
            body = resp.json() or {}
            if not isinstance(body, dict):
                raise HTTPException(status_code=502, detail="startup status malformed")
            return body
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="orchestrator unavailable")


@app.get("/onboarding-status")
def get_onboarding_status(person_id: str | None = None):
    """Aggregate startup, speech, inference, and preference state for first-run guidance."""
    pid = person_id or _default_person_id
    startup = get_startup_status()
    profile = _get_cached_profile(pid)
    preferences = _extract_renderer_preferences(profile) if isinstance(profile, dict) else {}
    voice = profile.get("voice") if isinstance(profile.get("voice"), dict) else {}
    onboarding = profile.get("onboarding") if isinstance(profile.get("onboarding"), dict) else {}
    wakeword = voice.get("wakeword") if isinstance(voice.get("wakeword"), str) and voice.get("wakeword").strip() else _wakeword_default
    wakeword_opt_in = bool(voice.get("wakeword_opt_in")) if isinstance(voice, dict) else False

    speech_ready, speech_detail = _service_ready(f"{_speech_base}/ready")
    inference_ready, inference_detail = _service_ready(f"{_inference_base}/ready")

    steps = [
        {
            "id": "admin-bootstrap",
            "label": "Create first admin identity",
            "available": bool(startup.get("bootstrap_required")),
            "ready": not bool(startup.get("bootstrap_required")),
            "detail": "Required before first real use" if startup.get("bootstrap_required") else "Completed",
        },
        {
            "id": "microphone-path",
            "label": "Microphone path available",
            "available": speech_ready,
            "ready": speech_ready and bool(onboarding.get("microphone_checked")),
            "detail": "Confirmed" if onboarding.get("microphone_checked") else speech_detail,
        },
        {
            "id": "speaker-path",
            "label": "Speaker path available",
            "available": speech_ready,
            "ready": speech_ready and bool(onboarding.get("speaker_checked")),
            "detail": "Confirmed" if onboarding.get("speaker_checked") else speech_detail,
        },
        {
            "id": "local-model",
            "label": "Local model ready",
            "available": inference_ready,
            "ready": inference_ready and bool(onboarding.get("model_checked")),
            "detail": "Confirmed" if onboarding.get("model_checked") else inference_detail,
        },
        {
            "id": "wakeword-choice",
            "label": "Wakeword choice recorded",
            "available": True,
            "ready": bool(onboarding.get("wakeword_configured")),
            "detail": "Opted in" if wakeword_opt_in else "Defaulting to wakeword off",
        },
    ]

    blocked_steps = [step["id"] for step in steps if step.get("ready") is not True]
    remediation = []
    if startup.get("bootstrap_required"):
        remediation.append("Create the first admin identity with the bootstrap token from platform.env.")
    if not speech_ready:
        remediation.append("Bring the speech service to ready, then confirm microphone and speaker checks.")
    if not inference_ready:
        remediation.append("Bring the local inference service to ready before confirming the model step.")
    if speech_ready and not onboarding.get("microphone_checked"):
        remediation.append("Grant microphone access in the browser and confirm the microphone step.")
    if speech_ready and not onboarding.get("speaker_checked"):
        remediation.append("Run the speaker check and confirm that audio played.")
    if inference_ready and not onboarding.get("model_checked"):
        remediation.append("Confirm that the local model is available for first-run use.")
    if not onboarding.get("wakeword_configured"):
        remediation.append("Choose whether to keep wakeword off or opt in explicitly.")

    ready_to_finish = startup.get("bootstrap_required") is False and not blocked_steps

    return {
        "ok": True,
        "person_id": pid,
        "startup": startup,
        "preferences": preferences,
        "wakeword": {
            "value": wakeword,
            "opt_in": wakeword_opt_in,
            "default": _wakeword_default,
        },
        "onboarding": onboarding,
        "steps": steps,
        "blocked_steps": blocked_steps,
        "remediation": remediation,
        "ready_to_finish": ready_to_finish,
    }


@app.post("/onboarding/profile")
def persist_onboarding_profile(body: Dict[str, Any] = Body(...)):
    """Persist onboarding-related preferences and wakeword posture to context profile."""
    pid = body.get("person_id") or _default_person_id
    if not isinstance(pid, str) or not pid.strip():
        raise HTTPException(status_code=400, detail="person_id required")

    existing = _get_cached_profile(pid)
    profile = dict(existing or {})
    profile.setdefault("preferences", {})
    profile.setdefault("voice", {})
    profile.setdefault("onboarding", {})

    renderer_preferences = body.get("renderer_preferences")
    if isinstance(renderer_preferences, dict):
        prefs = profile["preferences"] if isinstance(profile.get("preferences"), dict) else {}
        prefs_renderer = prefs.get("renderer") if isinstance(prefs.get("renderer"), dict) else {}
        prefs_renderer.update({k: v for k, v in renderer_preferences.items() if isinstance(v, (bool, str, int, float))})
        prefs["renderer"] = prefs_renderer
        profile["preferences"] = prefs

    reduce_motion = body.get("reduce_motion")
    if isinstance(reduce_motion, bool):
        accessibility = profile.get("accessibility") if isinstance(profile.get("accessibility"), dict) else {}
        accessibility["reduceMotion"] = reduce_motion
        profile["accessibility"] = accessibility

    wakeword_opt_in = body.get("wakeword_opt_in")
    if isinstance(wakeword_opt_in, bool):
        voice = profile.get("voice") if isinstance(profile.get("voice"), dict) else {}
        voice["wakeword_opt_in"] = wakeword_opt_in
        if wakeword_opt_in:
            wakeword = body.get("wakeword")
            voice["wakeword"] = wakeword.strip() if isinstance(wakeword, str) and wakeword.strip() else _wakeword_default
        else:
            voice["wakeword"] = ""
        profile["voice"] = voice

    onboarding = profile.get("onboarding") if isinstance(profile.get("onboarding"), dict) else {}
    for key in ("microphone_checked", "speaker_checked", "model_checked", "wakeword_configured", "completed"):
        value = body.get(key)
        if isinstance(value, bool):
            onboarding[key] = value
    onboarding["updated_at"] = time.time()
    if onboarding.get("completed") is True and "completed_at" not in onboarding:
        onboarding["completed_at"] = time.time()
    profile["onboarding"] = onboarding

    try:
        _store_profile(pid, profile)
        _context_profile_cache[pid] = profile
        _context_profile_cache_ts[pid] = time.time()
        return {"ok": True, "person_id": pid, "profile": profile}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="profile persistence failed")


@app.post("/onboarding/bootstrap-admin")
def bootstrap_admin(body: Dict[str, Any] = Body(...)):
    """Proxy first-admin bootstrap to auth so onboarding can complete end to end."""
    username = body.get("username")
    password = body.get("password")
    bootstrap_token = body.get("bootstrap_token")
    email = body.get("email")

    if not isinstance(username, str) or not username.strip():
        raise HTTPException(status_code=400, detail="username required")
    if not isinstance(password, str) or not password:
        raise HTTPException(status_code=400, detail="password required")
    if not isinstance(bootstrap_token, str) or not bootstrap_token.strip():
        raise HTTPException(status_code=400, detail="bootstrap_token required")

    payload: Dict[str, Any] = {
        "username": username.strip(),
        "password": password,
    }
    if isinstance(email, str) and email.strip():
        payload["email"] = email.strip()

    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(
                f"{_auth_base}/bootstrap/admin",
                json=payload,
                headers={"X-Unison-Bootstrap-Token": bootstrap_token.strip()},
            )
        if resp.status_code >= 400:
            detail: Any
            try:
                detail = resp.json()
            except Exception:
                detail = {"detail": "auth bootstrap failed"}
            raise HTTPException(status_code=resp.status_code, detail=detail)
        data = resp.json() or {}
        return {"ok": True, "admin": data}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="auth bootstrap unavailable")


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
    max_bytes = int(os.getenv("UNISON_RENDERER_MAX_ENVELOPE_BYTES", "0"))
    if max_bytes > 0:
        try:
            if len(json.dumps(envelope, ensure_ascii=False).encode("utf-8")) > max_bytes:
                raise HTTPException(status_code=413, detail="envelope_too_large")
        except TypeError:
            pass

    if os.getenv("UNISON_REDACT_RENDERER_EVENTS", "true").lower() in {"1", "true", "yes", "on"}:
        envelope = redact_obj(envelope)
        envelope.setdefault("meta", {})
        if isinstance(envelope["meta"], dict):
            envelope["meta"]["redacted"] = True
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


def _extract_renderer_preferences(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort normalization for context profile fields into renderer preferences.

    Expected shapes (any may exist):
    - profile["renderer"][<keys>]
    - profile["preferences"]["renderer"][<keys>]
    - profile["accessibility"][<keys>]
    """
    renderer = profile.get("renderer") if isinstance(profile.get("renderer"), dict) else {}
    preferences = profile.get("preferences") if isinstance(profile.get("preferences"), dict) else {}
    preferences_renderer = preferences.get("renderer") if isinstance(preferences.get("renderer"), dict) else {}
    accessibility = profile.get("accessibility") if isinstance(profile.get("accessibility"), dict) else {}

    def pick_bool(*values: Any) -> bool | None:
        for v in values:
            if isinstance(v, bool):
                return v
        return None

    def pick_str(*values: Any) -> str | None:
        for v in values:
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None

    presence_visual = pick_bool(
        renderer.get("presenceCueVisual"),
        renderer.get("presence_cue_visual"),
        preferences_renderer.get("presenceCueVisual"),
        preferences_renderer.get("presence_cue_visual"),
    )
    presence_audio = pick_bool(
        renderer.get("presenceCueAudio"),
        renderer.get("presence_cue_audio"),
        preferences_renderer.get("presenceCueAudio"),
        preferences_renderer.get("presence_cue_audio"),
    )
    haptic_cues = pick_bool(
        renderer.get("hapticCues"),
        renderer.get("haptic_cues"),
        preferences_renderer.get("hapticCues"),
        preferences_renderer.get("haptic_cues"),
    )
    reduce_motion = pick_bool(
        accessibility.get("reduceMotion"),
        accessibility.get("reduce_motion"),
        accessibility.get("prefers_reduced_motion"),
    )

    out: Dict[str, Any] = {}
    if presence_visual is not None:
        out["presenceCueVisual"] = presence_visual
    if presence_audio is not None:
        out["presenceCueAudio"] = presence_audio
    if haptic_cues is not None:
        out["hapticCues"] = haptic_cues
    if reduce_motion is not None:
        out["reduceMotion"] = reduce_motion

    contrast = pick_str(accessibility.get("contrast"), accessibility.get("visual_contrast"))
    if contrast is not None:
        out["contrast"] = contrast

    return out


def _get_context_client() -> httpx.Client:
    global _context_client
    if _context_client is not None:
        return _context_client
    kwargs: Dict[str, Any] = {
        "timeout": 2.0,
        "headers": _context_headers or None,
    }
    limits_ctor = getattr(httpx, "Limits", None)
    if limits_ctor:
        kwargs["limits"] = limits_ctor(max_keepalive_connections=10, max_connections=20, keepalive_expiry=30.0)
    _context_client = httpx.Client(**kwargs)
    return _context_client


def _service_ready(url: str) -> tuple[bool, str]:
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            return False, f"status {resp.status_code}"
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if isinstance(body, dict):
            if "ready" in body:
                return bool(body.get("ready")), str(body.get("detail") or body.get("provider", {}).get("detail") or "ok")
            return True, str(body.get("status") or "ok")
        return True, "ok"
    except Exception:
        return False, "unreachable"


def _store_profile(person_id: str, profile: Dict[str, Any]) -> None:
    client = _get_context_client()
    resp = client.post(f"{_context_base}/profile/{person_id}", json={"profile": profile})
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="profile store failed")
    body = resp.json() or {}
    if not isinstance(body, dict) or body.get("ok") is not True:
        raise HTTPException(status_code=502, detail="profile store failed")


def _get_cached_profile(person_id: str) -> Dict[str, Any]:
    now = time.time()
    cached = _context_profile_cache.get(person_id)
    ts = _context_profile_cache_ts.get(person_id, 0.0)
    if cached is not None and _context_profile_cache_seconds > 0 and (now - ts) <= _context_profile_cache_seconds:
        return cached

    profile: Dict[str, Any] = {}
    try:
        client = _get_context_client()
        resp = client.get(f"{_context_base}/profile/{person_id}")
        if resp.status_code == 200:
            body = resp.json() or {}
            p = body.get("profile")
            if isinstance(p, dict):
                profile = p
    except Exception:
        profile = cached or {}

    _context_profile_cache[person_id] = profile
    _context_profile_cache_ts[person_id] = now
    return profile
