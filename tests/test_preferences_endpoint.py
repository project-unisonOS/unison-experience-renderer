import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("DISABLE_AUTH_FOR_TESTS", "true")
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT / "../unison-common/src"))

import main  # noqa: E402


class _DummyResponse:
    def __init__(self, status: int, payload: dict):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


class _DummyClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, headers=None):
        self.requests.append({"url": url, "headers": headers})
        return _DummyResponse(200, self.payload)


def test_preferences_proxy_normalizes_profile(monkeypatch):
    dummy = _DummyClient(
        {
            "ok": True,
            "profile": {
                "renderer": {"presenceCueVisual": True, "presenceCueAudio": True, "hapticCues": True},
                "accessibility": {"reduce_motion": True, "contrast": "high"},
            },
        }
    )
    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: dummy}))
    client = TestClient(main.app)
    resp = client.get("/preferences?person_id=p1")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("person_id") == "p1"
    prefs = body.get("preferences") or {}
    assert prefs.get("presenceCueVisual") is True
    assert prefs.get("presenceCueAudio") is True
    assert prefs.get("hapticCues") is True
    assert prefs.get("reduceMotion") is True
    assert prefs.get("contrast") == "high"
    assert any("/profile/p1" in r["url"] for r in dummy.requests)


def test_preferences_returns_empty_on_context_error(monkeypatch):
    class FailingClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, headers=None):
            raise RuntimeError("context unreachable")

    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: FailingClient()}))
    client = TestClient(main.app)
    resp = client.get("/preferences?person_id=someone")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("person_id") == "someone"
    assert body.get("preferences") == {}


def test_extract_renderer_preferences_supports_nested_shapes():
    prefs = main._extract_renderer_preferences(
        {
            "preferences": {"renderer": {"presence_cue_audio": True}},
            "accessibility": {"prefers_reduced_motion": True},
        }
    )
    assert prefs == {"presenceCueAudio": True, "reduceMotion": True}

