import pytest

from incident_expressions import REQUIRED_SEMANTICS, express_incident


INCIDENT = {
    "incident_id": "inc-1", "state": "action-needed", "severity": "urgent",
    "source_ids": ["obs-1", "pack-1"],
    "facts": [{"claim": "Water detected", "state": "confirmed"}],
    "uncertainties": ["Leak source is not confirmed"],
    "assignments": [{"assignee_person_id": "jordan", "action": "Inspect labeled shutoff",
                     "state": "proposed", "physical_actuation": False}],
}


def test_visual_braille_and_conversation_preserve_identical_semantics():
    expressions = [express_incident(INCIDENT, modality) for modality in ("visual", "braille", "conversation")]
    assert all(item["semantic"] == expressions[0]["semantic"] for item in expressions)
    assert set(expressions[0]["semantic"]) == set(REQUIRED_SEMANTICS)
    assert expressions[0]["expression"]["non_color_cue"] == "urgent incident"


def test_modality_loss_falls_back_without_losing_position_or_actions():
    result = express_incident(INCIDENT, "braille", unavailable_modalities={"braille"})
    assert result["modality"] == "conversation"
    assert result["degraded_from"] == "braille"
    assert result["resume_token"] == "inc-1:action-needed"
    assert "cancel" in result["semantic"]["actions"]


def test_no_available_expression_is_explicit_not_silent():
    with pytest.raises(ValueError, match="no incident expression"):
        express_incident(INCIDENT, "braille", unavailable_modalities={"braille", "conversation", "visual"})
