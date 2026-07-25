import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DISABLE_AUTH_FOR_TESTS"] = "true"
os.environ["UNISON_PRINCIPAL_BINDING_TEST_BYPASS"] = "true"

import main as renderer


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "src" / "web" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "src" / "web" / "systemWellbeing.js").read_text(encoding="utf-8")


def test_system_wellbeing_surface_is_semantic_and_non_executing():
    for identifier in (
        "systemWellbeingHeading",
        "wellbeingRefresh",
        "wellbeingStatus",
        "wellbeingDimensions",
        "maintenanceRecommendations",
    ):
        assert f'id="{identifier}"' in HTML
    assert 'role="status" aria-live="polite"' in HTML
    assert "does not install, purchase, or alter hardware" in HTML
    assert "Community popularity alone is never sufficient evidence" in HTML
    assert "innerHTML" not in SCRIPT


def test_missing_status_is_safe_and_privacy_explicit(monkeypatch, tmp_path):
    monkeypatch.setattr(renderer, "_maintenance_status_path", tmp_path / "missing.json")
    response = TestClient(renderer.app).get("/maintenance/wellbeing")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not-yet-observed"
    assert body["privacy"]["personal_content_collected"] is False
    assert body["recommendations"] == []


def test_wellbeing_projection_rejects_personal_content(monkeypatch, tmp_path):
    path = tmp_path / "wellbeing.json"
    path.write_text(json.dumps({
        "status": "healthy",
        "summary": "Healthy",
        "privacy": {"personal_content_collected": True},
    }))
    monkeypatch.setattr(renderer, "_maintenance_status_path", path)
    response = TestClient(renderer.app).get("/maintenance/wellbeing")
    assert response.status_code == 502


def test_wellbeing_projection_is_allowlisted(monkeypatch, tmp_path):
    path = tmp_path / "wellbeing.json"
    path.write_text(json.dumps({
        "status": "attention",
        "summary": "One adjustment may help.",
        "dimensions": [{"label": "Memory", "status": "warning", "detail": "Pressure is sustained."}],
        "recommendations": [{
            "title": "Use a smaller model",
            "explanation": "This avoids a hardware purchase.",
            "authority": "recommend",
            "requires_confirmation": True,
        }],
        "privacy": {"personal_content_collected": False},
        "private_debug": "Alice's message subject",
    }))
    monkeypatch.setattr(renderer, "_maintenance_status_path", path)
    body = TestClient(renderer.app).get("/maintenance/wellbeing").json()
    assert "private_debug" not in body
    assert body["recommendations"][0]["authority"] == "recommend"
