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
    assert "unison companion" in text
    assert "tool activity" in text
    # Basic accessibility landmarks
    assert 'role="main"' in resp.text or "role='main'" in resp.text
    assert "chat-heading" in resp.text
