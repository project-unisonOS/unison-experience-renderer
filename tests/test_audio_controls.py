import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("DISABLE_AUTH_FOR_TESTS", "true")
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
import main  # noqa: E402


def test_stt_error_updates_status(monkeypatch):
    class DummyResp:
        def __init__(self, status):
            self.status_code = status

        def json(self):
            return {}

    class DummyClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            return DummyResp(500)

    monkeypatch.setattr(main, "httpx", type("X", (), {"Client": lambda *a, **k: DummyClient()}))
    client = TestClient(main.app)
    resp = client.post("/speech/stt", json={"audio": "ZGF0YQ=="})
    # The proxy will still bubble upstream failure as 502 in this case
    assert resp.status_code in (400, 502)
