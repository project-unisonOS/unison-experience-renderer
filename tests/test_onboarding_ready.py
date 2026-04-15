import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

os.environ.setdefault("DISABLE_AUTH_FOR_TESTS", "true")
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))
sys.path.append(str(ROOT / "../unison-common/src"))

import main  # noqa: E402


def test_onboarding_status_ready_to_finish_when_all_checks_pass(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_startup_status",
        lambda: {
            "ok": True,
            "state": "READY_LISTENING",
            "bootstrap_required": False,
            "onboarding_required": False,
            "renderer_ready": True,
            "core_ready": True,
            "speech_ready": True,
        },
    )
    monkeypatch.setattr(
        main,
        "_get_cached_profile",
        lambda person_id: {
            "voice": {"wakeword": "unison", "wakeword_opt_in": False},
            "preferences": {"renderer": {"presenceCueVisual": True}},
            "onboarding": {
                "completed": False,
                "microphone_checked": True,
                "speaker_checked": True,
                "model_checked": True,
                "wakeword_configured": True,
            },
        },
    )
    monkeypatch.setattr(main, "_service_ready", lambda url: (True, "ok"))

    client = TestClient(main.app)
    resp = client.get("/onboarding-status?person_id=p1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["person_id"] == "p1"
    assert body["startup"]["state"] == "READY_LISTENING"
    assert body["blocked_steps"] == []
    assert body["ready_to_finish"] is True
    assert any(step["id"] == "local-model" and step["ready"] is True for step in body["steps"])
