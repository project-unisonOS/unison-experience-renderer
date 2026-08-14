"""Equivalent semantic expressions for shared household incidents."""

from __future__ import annotations

from typing import Any


REQUIRED_SEMANTICS = ("state", "severity", "facts", "uncertainties", "assignments", "actions", "provenance")


def express_incident(incident: dict[str, Any], modality: str, *,
                     unavailable_modalities: set[str] | None = None) -> dict[str, Any]:
    unavailable = unavailable_modalities or set()
    if modality not in {"visual", "braille", "conversation"}:
        raise ValueError("unsupported incident modality")
    if modality in unavailable:
        fallback = "conversation" if "conversation" not in unavailable else "visual"
        if fallback in unavailable:
            raise ValueError("no incident expression modality is available")
        result = express_incident(incident, fallback, unavailable_modalities=unavailable)
        result["degraded_from"] = modality
        result["resume_token"] = f"{incident['incident_id']}:{incident['state']}"
        return result

    assignments = [{"assignee_person_id": item["assignee_person_id"], "action": item["action"],
                    "state": item["state"], "physical_actuation": False}
                   for item in incident.get("assignments", [])]
    semantic = {
        "state": incident["state"], "severity": incident["severity"],
        "facts": incident.get("facts", []), "uncertainties": incident.get("uncertainties", []),
        "assignments": assignments,
        "actions": ["acknowledge", "cancel", "request-guidance", "escalate"],
        "provenance": incident.get("source_ids", []),
    }
    expression = {
        "visual": {"layout": "incident-card", "status_text": incident["state"],
                   "non_color_cue": f"{incident['severity']} incident"},
        "braille": {"cells": _plain_summary(semantic), "navigation": "semantic-regions"},
        "conversation": {"speech": _plain_summary(semantic), "turn_position": incident["state"]},
    }[modality]
    return {"schema_version": "incident-expression.v1", "incident_id": incident["incident_id"],
            "modality": modality, "semantic": semantic, "expression": expression,
            "required_semantics": list(REQUIRED_SEMANTICS)}


def _plain_summary(semantic: dict[str, Any]) -> str:
    uncertainty = "; ".join(semantic["uncertainties"]) or "none recorded"
    return (f"{semantic['severity']} incident, state {semantic['state']}. "
            f"Uncertainty: {uncertainty}. Available actions: {', '.join(semantic['actions'])}.")
