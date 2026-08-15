"""Native expressions for unfamiliar-request progress and outcomes."""
from __future__ import annotations

def express_resolution(outcome: dict, modality: str) -> dict:
    if modality not in {"conversation", "braille", "visual"}:
        raise ValueError("unsupported resolution modality")
    semantic = {key: outcome.get(key, default) for key, default in (
        ("summary", ""), ("facts", []), ("uncertainties", []), ("actions", []), ("recovery", {}))}
    expressions = {
        "conversation": {"turns": [semantic["summary"], *semantic["uncertainties"]],
                         "reply_intents": semantic["actions"], "barge_in": True},
        "braille": {"regions": [{"semantic_id": "summary", "text": semantic["summary"]},
                                  *({"semantic_id": f"uncertainty-{i}", "text": text}
                                    for i, text in enumerate(semantic["uncertainties"], 1))],
                    "routing_actions": semantic["actions"], "resume": semantic["recovery"]},
        "visual": {"sections": ["summary", "facts", "uncertainties", "actions"],
                   "controls": semantic["actions"], "resume": semantic["recovery"]},
    }
    return {"schema_version": "resolution-expression.v1", "modality": modality,
            "semantic": semantic, "expression": expressions[modality]}

def express_candidate_review(candidate: dict, modality: str) -> dict:
    """Compose a candidate review natively without granting executable authority."""
    if modality not in {"conversation", "braille", "visual"}:
        raise ValueError("unsupported candidate review modality")
    semantic = {
        "candidate_id": candidate["candidate_id"],
        "reason": candidate["reason"],
        "proposed_outcome": candidate["proposed_outcome"],
        "data_and_authority": candidate.get("data_and_authority", []),
        "scope": candidate.get("scope", "person-local"),
        "choices": ["accept", "modify", "defer", "reject"],
        "executable": False,
    }
    expressions = {
        "conversation": {
            "opening": f"I noticed a repeatable pattern: {semantic['reason']}",
            "explanation": semantic["proposed_outcome"],
            "spoken_choices": semantic["choices"],
            "barge_in": True,
        },
        "braille": {
            "regions": [
                {"semantic_id": "reason", "text": semantic["reason"]},
                {"semantic_id": "outcome", "text": semantic["proposed_outcome"]},
            ],
            "routing_actions": semantic["choices"],
        },
        "visual": {
            "sections": ["reason", "proposed_outcome", "data_and_authority", "scope"],
            "controls": semantic["choices"],
        },
    }
    return {"schema_version": "candidate-review-expression.v1", "modality": modality,
            "semantic": semantic, "expression": expressions[modality]}
