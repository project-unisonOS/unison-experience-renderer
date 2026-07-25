const byId = (id) => document.getElementById(id);

const status = byId("wellbeingStatus");
const dimensions = byId("wellbeingDimensions");
const recommendations = byId("maintenanceRecommendations");
const history = byId("maintenanceHistory");
const community = byId("communityProposals");
const decisionStatus = byId("maintenanceDecisionStatus");
let currentGrantId = null;
let currentRecommendationId = null;

function text(value, fallback) {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function renderDimensions(items) {
  dimensions.replaceChildren();
  const safeItems = Array.isArray(items) ? items : [];
  if (!safeItems.length) {
    const term = document.createElement("dt");
    term.textContent = "Status";
    const detail = document.createElement("dd");
    detail.textContent = "No local indicators are available yet.";
    dimensions.append(term, detail);
    return;
  }
  safeItems.forEach((item) => {
    const term = document.createElement("dt");
    term.textContent = text(item.label, "Indicator");
    const detail = document.createElement("dd");
    detail.textContent = `${text(item.status, "unknown")}: ${text(item.detail, "No detail available.")}`;
    dimensions.append(term, detail);
  });
}

function renderRecommendations(items) {
  recommendations.replaceChildren();
  const safeItems = Array.isArray(items) ? items : [];
  if (!safeItems.length) {
    const item = document.createElement("li");
    item.textContent = "No adjustment is currently recommended.";
    recommendations.append(item);
    return;
  }
  safeItems.forEach((entry) => {
    if (!currentRecommendationId && entry.recommendation_id) currentRecommendationId = entry.recommendation_id;
    const item = document.createElement("li");
    const title = document.createElement("strong");
    title.textContent = text(entry.title, "Review suggested adjustment");
    const explanation = document.createElement("p");
    explanation.textContent = text(entry.explanation, "Open the recommendation to review its evidence.");
    const authority = document.createElement("p");
    authority.textContent = `Action level: ${text(entry.authority, "recommend")}. Confirmation required: ${entry.requires_confirmation === false ? "no" : "yes"}.`;
    item.append(title, explanation, authority);
    recommendations.append(item);
  });
}

async function submitDecision(decision, extra = {}) {
  decisionStatus.textContent = "Submitting your decision for independent verification.";
  const response = await fetch("/maintenance/decision", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ decision, recommendation_id: currentRecommendationId, ...extra }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error("maintenance decision rejected");
  decisionStatus.textContent = text(result.detail, "Your decision was queued.");
}

function renderHistory(items) {
  history.replaceChildren();
  const safeItems = Array.isArray(items) ? items : [];
  if (!safeItems.length) {
    const item = document.createElement("li");
    item.textContent = "No bounded maintenance action has been recorded.";
    history.append(item);
    return;
  }
  safeItems.forEach((entry) => {
    const item = document.createElement("li");
    item.textContent = `${text(entry.result, "unknown")} at ${text(entry.completed_at, "an unknown time")}. Checkpoint: ${text(entry.checkpoint_id, "not recorded")}.`;
    history.append(item);
  });
}

function renderCommunity(items) {
  community.replaceChildren();
  const safeItems = Array.isArray(items) ? items : [];
  if (!safeItems.length) {
    const item = document.createElement("li");
    item.textContent = "No corroborated community test proposal is available.";
    community.append(item);
    return;
  }
  safeItems.forEach((entry) => {
    const item = document.createElement("li");
    item.textContent = `${text(entry.subject, "Improvement idea")}: ${text(entry.statement, "No claim detail available.")} Sources: ${Number(entry.source_count) || 0}. Authority: test proposal only.`;
    community.append(item);
  });
}

byId("wellbeingRefresh")?.addEventListener("click", async () => {
  status.textContent = "Checking the privacy-minimized local health summary.";
  try {
    const response = await fetch("/maintenance/wellbeing", { headers: { Accept: "application/json" } });
    const result = await response.json();
    if (!response.ok) throw new Error("wellbeing request rejected");
    if (result.privacy?.personal_content_collected !== false) {
      throw new Error("privacy contract missing");
    }
    status.textContent = text(result.summary, "System wellbeing check complete.");
    renderDimensions(result.dimensions);
    renderRecommendations(result.recommendations);
    renderHistory(result.maintenance_history);
    renderCommunity(result.community_proposals);
    currentGrantId = result.autonomy?.grant_id || null;
  } catch {
    status.textContent = "System wellbeing is temporarily unavailable. No maintenance action was taken.";
    renderDimensions([]);
    renderRecommendations([]);
    renderHistory([]);
    renderCommunity([]);
  }
});

byId("maintenanceGrant")?.addEventListener("click", async () => {
  const now = new Date();
  const expires = new Date(now.getTime() + 30 * 60 * 1000);
  const grantId = `grant-${now.getTime()}`;
  try {
    await submitDecision("grant", {
      grant_id: grantId,
      device_id: "local-appliance",
      action_classes: [byId("maintenanceActionClass").value],
      not_before: now.toISOString(),
      expires_at: expires.toISOString(),
      max_actions: 1,
      max_downtime_seconds: 120,
    });
    currentGrantId = grantId;
  } catch {
    decisionStatus.textContent = "The grant was not accepted. No maintenance authority changed.";
  }
});

byId("maintenanceDefer")?.addEventListener("click", async () => {
  try {
    const until = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    await submitDecision("defer", { defer_until: until });
  } catch {
    decisionStatus.textContent = "The suggestion was not deferred.";
  }
});

byId("maintenanceRevoke")?.addEventListener("click", async () => {
  if (!currentGrantId) {
    decisionStatus.textContent = "No active grant is available to revoke.";
    return;
  }
  try {
    await submitDecision("revoke", { grant_id: currentGrantId });
    currentGrantId = null;
  } catch {
    decisionStatus.textContent = "The grant was not revoked. Review System wellbeing before retrying.";
  }
});
