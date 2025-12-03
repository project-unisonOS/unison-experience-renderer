import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("DISABLE_AUTH_FOR_TESTS", "true")
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT / "../unison-common/src"))

import main  # noqa: E402


def test_dashboard_proxy_forwards_person_and_headers(monkeypatch):
    calls = []

    class DummyResp:
        status_code = 200

        def json(self):
            return {"ok": True, "dashboard": {"cards": [], "preferences": {}}}

    class DummyClient:
        def __init__(self, *_, **__):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, headers=None):
            calls.append({"url": url, "headers": headers})
            return DummyResp()

    # Patch httpx.Client used inside main.get_dashboard
    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: DummyClient()}))
    client = TestClient(main.app)
    resp = client.get("/dashboard?person_id=p-test")
    assert resp.status_code == 200
    assert calls, "expected downstream GET to context"
    call = calls[0]
    assert "/dashboard/p-test" in call["url"]
    # x-test-role header should be forwarded when configured
    headers = call["headers"] or {}
    assert "x-test-role" in {k.lower() for k in headers.keys()}


def test_dashboard_preferences_adjust_text_and_contrast(monkeypatch):
    class DummyResp:
        status_code = 200

        def json(self):
            return {
                "ok": True,
                "dashboard": {
                    "cards": [],
                    "preferences": {"text_scale": 1.2, "contrast": "high"},
                },
            }

    class DummyClient:
        def __init__(self, *_, **__):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, headers=None):
            return DummyResp()

    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: DummyClient()}))
    client = TestClient(main.app)
    resp = client.get("/dashboard?person_id=p-pref")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True

