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
    def __init__(self, *_, **__):
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, headers=None):
        self.requests.append({"url": url, "headers": headers})
        # Simulate a profile with a custom wakeword.
        return _DummyResponse(
            200,
            {"ok": True, "profile": {"voice": {"wakeword": "hey unison"}}},
        )


def test_get_wakeword_prefers_profile_value(monkeypatch):
    dummy = _DummyClient()
    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: dummy}))
    client = TestClient(main.app)
    resp = client.get("/wakeword?person_id=p1")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("wakeword") == "hey unison"
    assert body.get("person_id") == "p1"
    assert any("/profile/p1" in r["url"] for r in dummy.requests)


def test_get_wakeword_falls_back_to_default_on_error(monkeypatch):
    class FailingClient:
        def __init__(self, *_, **__):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, headers=None):
            raise RuntimeError("context unreachable")

    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: FailingClient()}))
    # Ensure default is known for this test.
    os.environ["UNISON_WAKEWORD_DEFAULT"] = "unison"
    client = TestClient(main.app)
    resp = client.get("/wakeword?person_id=someone")
    assert resp.status_code == 200
    body = resp.json()
    # When context fails, we should still return the default wake word.
    assert body.get("wakeword") == "unison"

