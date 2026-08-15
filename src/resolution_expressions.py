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
