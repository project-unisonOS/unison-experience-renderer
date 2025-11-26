import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

os.environ.setdefault("DISABLE_AUTH_FOR_TESTS", "true")
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
import main  # noqa: E402

# Ensure middleware from prior imports does not enforce baton verification in tests
main.app.user_middleware = []
main.app.middleware_stack = main.app.build_middleware_stack()


class _DummyResponse:
    status_code = 200

    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _DummyClient:
    def __init__(self, *_, **__):
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, json=None, headers=None):
        self.requests.append({"url": url, "json": json, "headers": headers})
        return _DummyResponse({"ok": True, "echo": json, "headers": headers})


def test_proxy_stt_forwards_baton_and_ids(monkeypatch):
    dummy = _DummyClient()
    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: dummy}))

    client = TestClient(main.app)
    resp = client.post(
        "/speech/stt",
        headers={"X-Context-Baton": "baton-123"},
        json={"audio": "ZGF0YQ==", "person_id": "p1", "session_id": "s1"},
    )
    assert resp.status_code == 200
    sent = dummy.requests[0]
    assert "/speech/stt" in sent["url"]
    assert sent["json"]["person_id"] == "p1"
    assert sent["json"]["session_id"] == "s1"
    assert sent["headers"]["X-Context-Baton"] == "baton-123"


def test_proxy_stt_rejects_missing_audio(monkeypatch):
    dummy = _DummyClient()
    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: dummy}))

    client = TestClient(main.app)
    resp = client.post("/speech/stt", json={"audio": None})
    assert resp.status_code == 400
