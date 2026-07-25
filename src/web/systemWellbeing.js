const byId = (id) => document.getElementById(id);

const status = byId("wellbeingStatus");
const dimensions = byId("wellbeingDimensions");
const recommendations = byId("maintenanceRecommendations");

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
  } catch {
    status.textContent = "System wellbeing is temporarily unavailable. No maintenance action was taken.";
    renderDimensions([]);
    renderRecommendations([]);
  }
});
