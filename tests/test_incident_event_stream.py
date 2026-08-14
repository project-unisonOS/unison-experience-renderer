import os

from fastapi.testclient import TestClient

os.environ["DISABLE_AUTH_FOR_TESTS"] = "true"
os.environ["UNISON_PRINCIPAL_BINDING_TEST_BYPASS"] = "true"

import main


def test_incident_event_is_composed_for_all_modalities(monkeypatch):
    monkeypatch.setenv("UNISON_REDACT_RENDERER_EVENTS", "false")
    main._event_log.clear()
    incident = {
        "incident_id": "inc-1", "state": "action-needed", "severity": "urgent",
        "source_ids": ["obs-1"], "facts": [], "uncertainties": ["source unknown"],
        "assignments": [],
    }
    client = TestClient(main.app)
    response = client.post("/events", json={
        "type": "household.incident.v1",
        "payload": {"incident": incident, "checklist": ["Stop if unsafe"]},
    })
    assert response.status_code == 200
    stored = client.get("/events").json()["items"][0]
    expressions = stored["payload"]["expressions"]
    assert set(expressions) == {"visual", "braille", "conversation"}
    assert expressions["visual"]["semantic"] == expressions["braille"]["semantic"]
