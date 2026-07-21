const byId = (id) => document.getElementById(id);
const text = (id, value) => { const node = byId(id); if (node) node.textContent = value || "Not provided — Unison will not continue."; };

export function renderTrustDecision(decision, request) {
  const section = byId("trustDecision");
  if (!section) return;
  section.hidden = false;
  text("trustDecisionSummary", decision.explanation);
  text("trustAction", request.action);
  text("trustRecipients", (request.recipient_ids || []).join(", ") || (request.audience || []).join(", "));
  text("trustData", (decision.disclosed_fields || request.data_classes || []).join(", "));
  text("trustPurpose", request.purpose);
  text("trustConsequence", decision.consequence);
  text("trustReversible", decision.reversible ? "Yes" : "No");
  text("trustCost", request.estimated_cost || "No cost declared");
  byId("trustConfirm").disabled = !decision.confirmation_id;
  byId("trustConfirm").focus();
}

for (const [id, message] of [["trustCancel", "Action cancelled. Nothing was sent."], ["trustMinimize", "I will prepare a new preview with less information."], ["trustConfirm", "Confirmation recorded for this exact action only."]]) {
  const node = byId(id);
  if (node) node.addEventListener("click", () => text("trustDecisionSummary", message));
}
