import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("DISABLE_AUTH_FOR_TESTS", "true")
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT / "../unison-common/src"))

import main  # noqa: E402


def test_onboarding_status_aggregates_startup_and_profile(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_startup_status",
        lambda: {
            "ok": False,
            "state": "AUTH_BOOTSTRAP_REQUIRED",
            "bootstrap_required": True,
            "onboarding_required": True,
        },
    )
    monkeypatch.setattr(
        main,
        "_get_cached_profile",
        lambda person_id: {
            "voice": {"wakeword": "hey unison", "wakeword_opt_in": True},
            "preferences": {"renderer": {"presenceCueVisual": True}},
            "onboarding": {"completed": False},
        },
    )
    monkeypatch.setattr(
        main,
        "_service_ready",
        lambda url: (True, "ok") if "speech" in url else (False, "model missing"),
    )

    client = TestClient(main.app)
    resp = client.get("/onboarding-status?person_id=p1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["person_id"] == "p1"
    assert body["startup"]["bootstrap_required"] is True
    assert body["wakeword"]["value"] == "hey unison"
    assert body["ready_to_finish"] is False
    assert "admin-bootstrap" in body["blocked_steps"]
    assert any("Create the first admin identity" in item for item in body["remediation"])
    assert any(step["id"] == "local-model" and step["ready"] is False and step["available"] is False for step in body["steps"])


def test_onboarding_profile_persists_renderer_and_voice_preferences(monkeypatch):
    stored = {}

    monkeypatch.setattr(main, "_get_cached_profile", lambda person_id: {"preferences": {}, "voice": {}, "onboarding": {}})

    def _capture_store(person_id, profile):
        stored["person_id"] = person_id
        stored["profile"] = profile

    monkeypatch.setattr(main, "_store_profile", _capture_store)
    main._context_profile_cache.clear()
    main._context_profile_cache_ts.clear()

    client = TestClient(main.app)
    resp = client.post(
        "/onboarding/profile",
        json={
            "person_id": "p1",
            "renderer_preferences": {"presenceCueVisual": True, "presenceCueAudio": False},
            "reduce_motion": True,
            "wakeword_opt_in": False,
            "microphone_checked": True,
            "speaker_checked": True,
            "model_checked": False,
            "wakeword_configured": True,
            "completed": False,
        },
    )

    assert resp.status_code == 200
    assert stored["person_id"] == "p1"
    profile = stored["profile"]
    assert profile["preferences"]["renderer"]["presenceCueVisual"] is True
    assert profile["accessibility"]["reduceMotion"] is True
    assert profile["voice"]["wakeword_opt_in"] is False
    assert profile["onboarding"]["microphone_checked"] is True


def test_bootstrap_admin_proxies_to_auth(monkeypatch):
    class DummyResponse:
        status_code = 201

        def json(self):
            return {"username": "founder", "roles": ["admin"], "active": True}

    class DummyClient:
        def __init__(self):
            self.request = None

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def post(self, url, json=None, headers=None):
            self.request = {"url": url, "json": json, "headers": headers}
            return DummyResponse()

    dummy = DummyClient()
    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: dummy}))

    client = TestClient(main.app)
    resp = client.post(
        "/onboarding/bootstrap-admin",
        json={
            "username": "founder",
            "password": "StrongPass1!",
            "email": "founder@example.com",
            "bootstrap_token": "bootstrap-secret",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["admin"]["username"] == "founder"
    assert dummy.request["url"].endswith("/bootstrap/admin")
    assert dummy.request["headers"]["X-Unison-Bootstrap-Token"] == "bootstrap-secret"
