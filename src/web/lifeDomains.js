const byId = (id) => document.getElementById(id);
const sessionHeaders = () => {
  const token = window.localStorage.getItem("unison.session.token");
  return { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
};

async function domainRequest(path, method = "GET", body = null) {
  const response = await fetch(`/life-domains/${path}`, {
    method, headers: sessionHeaders(), ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "This private review is unavailable.");
  return result;
}

function bind(buttonId, statusId, operation) {
  byId(buttonId)?.addEventListener("click", async () => {
    const status = byId(statusId);
    status.textContent = "Reviewing private local records.";
    try { status.textContent = await operation(); } catch (error) { status.textContent = error.message; }
  });
}

bind("householdAttentionRefresh", "householdLifeStatus", async () => {
  const body = await domainRequest("household/attention", "POST", { recall_feed: [] });
  return body.items?.length ? `${body.items.length} household deadline item(s) need review. No action was performed.` : "No household deadline currently needs attention.";
});

bind("healthTimelineRefresh", "healthLifeStatus", async () => {
  const body = await domainRequest("health/timeline");
  const sources = new Set((body.records || []).flatMap((record) => record.source_ids || []));
  return `${body.records?.length || 0} health timeline record(s) cite ${sources.size} source(s). This is not a diagnosis.`;
});

bind("healthContradictionsRefresh", "healthLifeStatus", async () => {
  const body = await domainRequest("health/contradictions");
  const conflicts = (body.contradictions || []).filter((item) => item.contradiction);
  return conflicts.length ? `${conflicts.length} source conflict(s) need your review.` : "No conflicting health sources were found.";
});

bind("financeAttentionRefresh", "financeLifeStatus", async () => {
  const body = await domainRequest("finance/attention");
  return body.items?.length ? `${body.items.length} financial exception(s) need review. No financial action was performed.` : "No financial exception currently needs attention.";
});

bind("financeForecastRefresh", "financeLifeStatus", async () => {
  const body = await domainRequest("finance/forecast");
  const range = body.range || [0, 0];
  return `Inferred 30-day range: ${range[0]} to ${range[1]}, confidence ${Math.round((body.confidence || 0) * 100)} percent. Review source assumptions before relying on it.`;
});

bind("financeBriefRefresh", "financeLifeStatus", async () => {
  const body = await domainRequest("finance/weekly-brief");
  return `${body.title}. ${body.citations?.length || 0} cited exception record(s). ${body.note || ""}`;
});

bind("lifeAttentionRefresh", "lifeAttentionStatus", async () => {
  const goals = (byId("lifeAttentionGoals")?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
  const body = await domainRequest("attention", "POST", { goals });
  const list = byId("lifeAttentionList");
  list.replaceChildren();
  for (const item of body.items || []) {
    const row = document.createElement("li");
    row.textContent = `${item.summary}. Risk ${item.risk}. Ranking uses risk, deadline, your selected goals, and review burden.`;
    list.append(row);
  }
  return `${body.items?.length || 0} purpose-scoped item(s) prioritized. No external action was performed.`;
});
