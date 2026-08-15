from src.resolution_expressions import express_candidate_review, express_resolution

def test_unfamiliar_request_is_equivalent_but_natively_composed():
    outcome = {"summary": "Prepared safe leak isolation steps", "facts": ["water flowing"],
        "uncertainties": ["valve condition unknown"], "actions": ["inspect", "cancel"],
        "recovery": {"resume_from": "inspection"}}
    values = [express_resolution(outcome, mode) for mode in ("conversation", "braille", "visual")]
    assert values[0]["semantic"] == values[1]["semantic"] == values[2]["semantic"]
    assert values[0]["expression"]["reply_intents"] == values[1]["expression"]["routing_actions"]
    assert not set(values[1]["expression"]).intersection({"aria", "dom", "visual_focus", "screen_reader"})

def test_candidate_review_is_native_equivalent_and_never_executable():
    candidate = {"candidate_id": "cand-1", "reason": "You repeated this three times",
        "proposed_outcome": "Prepare the same maintenance checklist",
        "data_and_authority": ["appliance inventory: read"], "scope": "person-local"}
    values = [express_candidate_review(candidate, mode)
              for mode in ("conversation", "braille", "visual")]
    assert values[0]["semantic"] == values[1]["semantic"] == values[2]["semantic"]
    assert values[0]["semantic"]["choices"] == ["accept", "modify", "defer", "reject"]
    assert values[0]["semantic"]["executable"] is False
    assert not set(values[1]["expression"]).intersection({"aria", "dom", "visual_focus", "screen_reader"})
