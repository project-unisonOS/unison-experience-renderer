import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("DISABLE_AUTH_FOR_TESTS", "true")
os.environ.setdefault("UNISON_REDACT_RENDERER_EVENTS", "true")

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT / "../unison-common/src"))

import main  # noqa: E402


def test_ingest_event_redacts_sensitive_fields():
    main._event_log.clear()
    client = TestClient(main.app)
    resp = client.post(
        "/events",
        json={"type": "outcome.reflected", "payload": {"text": "hi"}, "authorization": "Bearer abc.def.ghi"},
    )
    assert resp.status_code == 200
    listed = client.get("/events").json()["items"]
    assert listed, "expected stored envelope"
    assert listed[0].get("authorization") == "[REDACTED]"
