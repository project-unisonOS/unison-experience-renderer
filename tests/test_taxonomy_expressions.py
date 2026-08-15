from src.taxonomy_expressions import express_taxonomy_decision

PREVIEW = {"proposal_id": "p1", "prompt": "Create a legal domain?",
           "summary": "Legal records would have an independent boundary.",
           "why_now": ["Three repeated corrections"], "would_change": ["classification"],
           "would_not_change": ["content"], "choices": ["approve", "defer", "decline"],
           "requires_security_review": True}

def test_conversation_braille_and_visual_are_semantically_equivalent_and_native():
    outputs = [express_taxonomy_decision(PREVIEW, mode)
               for mode in ("conversation", "braille", "visual")]
    assert outputs[0]["semantic"] == outputs[1]["semantic"] == outputs[2]["semantic"]
    assert outputs[0]["expression"]["expected_reply_intents"] == PREVIEW["choices"]
    assert outputs[1]["expression"]["routing_actions"] == PREVIEW["choices"]
    native_keys = {key.lower() for output in outputs[:2] for key in output["expression"]}
    assert not native_keys.intersection({"screen_reader", "aria", "dom", "visual_focus"})
