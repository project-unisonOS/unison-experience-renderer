import pathlib
import sys

from fastapi.testclient import TestClient

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT / "../unison-common/src"))

from main import app  # noqa: E402


def test_root_renders_ui():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.text.lower()
    # Basic accessibility landmarks
    assert 'role="main"' in resp.text or "role='main'" in resp.text
    assert 'id="field"' in resp.text
    assert 'data-scene="presence"' in resp.text
    assert "<nav" not in text
    assert "dashboard" not in text
    assert "panel" not in text
    assert "card" not in text
