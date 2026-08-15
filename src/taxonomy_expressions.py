"""Native, semantically equivalent taxonomy-decision experiences.

Conversation and Braille are first-class compositions. Neither is derived from
visual layout, DOM focus, ARIA text, or a screen-reader representation.
"""
from __future__ import annotations
from typing import Any

MODALITIES = {"conversation", "braille", "visual"}

def express_taxonomy_decision(preview: dict[str, Any], modality: str) -> dict[str, Any]:
    if modality not in MODALITIES:
        raise ValueError("unsupported taxonomy modality")
    semantic = {
        "proposal_id": preview["proposal_id"], "prompt": preview["prompt"],
        "summary": preview["summary"], "why_now": list(preview.get("why_now", [])),
        "would_change": list(preview.get("would_change", [])),
        "would_not_change": list(preview.get("would_not_change", [])),
        "actions": list(preview.get("choices", ["approve", "defer", "decline"])),
        "security_review_required": bool(preview.get("requires_security_review")),
    }
    expression = {
        "conversation": {"turns": [semantic["prompt"], semantic["summary"]],
                         "expected_reply_intents": semantic["actions"], "interruptible": True},
        "braille": {"regions": [
            {"semantic_id": "prompt", "text": semantic["prompt"]},
            {"semantic_id": "summary", "text": semantic["summary"]},
            *({"semantic_id": f"why-{i}", "text": value}
              for i, value in enumerate(semantic["why_now"], 1))],
            "routing_actions": semantic["actions"], "navigation": "semantic-regions"},
        "visual": {"groups": ["prompt", "summary", "why_now", "would_change", "would_not_change"],
                   "controls": semantic["actions"]},
    }[modality]
    return {"schema_version": "taxonomy-expression.v1", "modality": modality,
            "semantic": semantic, "expression": expression}
