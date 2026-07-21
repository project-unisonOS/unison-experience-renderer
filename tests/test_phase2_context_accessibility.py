import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["DISABLE_AUTH_FOR_TESTS"] = "true"
os.environ["UNISON_PRINCIPAL_BINDING_TEST_BYPASS"] = "true"

import main


WEB = Path(__file__).resolve().parents[1] / "src" / "web"


def test_context_controls_are_semantic_keyboard_native_and_not_modality_dependent():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    required = [
        'section id="contextControls"', 'aria-labelledby="contextHeading"',
        '<fieldset>', '<legend>', 'role="status"', 'aria-live="polite"',
        'for="contextSpaceName"', 'for="contextSpacePurpose"',
        'for="memoryRecordId"', 'for="memoryCorrection"',
        'for="shareTargetSpace"', 'for="charterPrinciples"',
        'for="goalTitle"', 'for="goalSpaceId"',
        'for="commitmentTitle"', 'for="commitmentSpaceId"',
        'id="memoryDeleteConfirmed"', 'id="shareConfirmed"',
        'id="contextCancel"', 'type="button"',
    ]
    for marker in required:
        assert marker in html
    assert "Relationships alone never grant access" in html
    assert "Share preview" in html
    assert "drag" not in html.lower()


def test_context_controls_have_working_non_voice_actions():
    script = (WEB / "contextPrivacy.js").read_text(encoding="utf-8")
    for action in (
        "privacyRefresh", "contextSpaceCreate", "memoryCorrect", "memoryDelete",
        "memoryShare", "charterSave", "goalCreate", "commitmentCreate", "contextCancel",
    ):
        assert f'install("{action}"' in script
    assert "shareConfirmed" in script
    assert "memoryDeleteConfirmed" in script


def test_privacy_state_response_is_semantic(monkeypatch):
    monkeypatch.setattr(main, "_disable_auth", True)

    def fake_context(method, path, payload=None):
        if path.startswith("/v2/spaces"):
            return {"spaces": [{"space_id": "private-alice", "name": "Private", "kind": "private"}]}
        if path.startswith("/v2/charter"):
            return {"charter": {"principles": ["Protect my time"]}}
        if path.startswith("/v2/goals"):
            return {"goals": []}
        return {"commitments": []}

    monkeypatch.setattr(main, "_context_json", fake_context)
    response = TestClient(main.app).get("/context/privacy-state", params={"person_id": "alice"})
    assert response.status_code == 200
    body = response.json()
    assert body["privacy"] == {
        "sharing_requires_explicit_space": True,
        "relationships_grant_access": False,
        "default_disclosure": "deny",
    }
    assert body["spaces"][0]["kind"] == "private"
