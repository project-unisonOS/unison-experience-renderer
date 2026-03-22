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
    def __init__(self, payload: dict, status: int = 200):
        self.payload = payload
        self.status = status
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, headers=None):
        self.requests.append({"url": url, "headers": headers})
        return _DummyResponse(self.status, self.payload)


def test_startup_status_proxies_orchestrator(monkeypatch):
    dummy = _DummyClient(
        {
            "ok": False,
            "state": "AUTH_BOOTSTRAP_REQUIRED",
            "bootstrap_required": True,
            "onboarding_required": True,
        }
    )
    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: dummy}))
    client = TestClient(main.app)
    resp = client.get("/startup-status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "AUTH_BOOTSTRAP_REQUIRED"
    assert body["bootstrap_required"] is True
    assert any("/startup/status" in req["url"] for req in dummy.requests)


def test_startup_status_returns_502_when_orchestrator_unavailable(monkeypatch):
    class FailingClient:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, headers=None):
            raise RuntimeError("down")

    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: FailingClient()}))
    client = TestClient(main.app)
    resp = client.get("/startup-status")
    assert resp.status_code == 502
