const byId = (id) => document.getElementById(id);
const status = (message) => { const node = byId("contextStatus"); if (node) node.textContent = message; };

async function jsonRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Context request failed");
  return body;
}

async function refreshPrivacy() {
  const body = await jsonRequest("/context/privacy-state");
  const kinds = (body.spaces || []).map((space) => `${space.name} (${space.kind})`).join(", ") || "No spaces";
  byId("privacyState").textContent = `${kinds}. Sharing requires an explicit space. Relationships grant no access. Default disclosure is denied.`;
}

function install(id, handler) {
  const node = byId(id);
  if (node) node.addEventListener("click", async () => {
    try { await handler(); status("Context change completed."); }
    catch (error) { status(error.message || "Context change failed."); }
  });
}

install("privacyRefresh", refreshPrivacy);
install("contextSpaceCreate", async () => {
  await jsonRequest("/context/spaces", { method: "POST", body: JSON.stringify({
    name: byId("contextSpaceName").value,
    purpose: byId("contextSpacePurpose").value,
    kind: "shared",
  }) });
  await refreshPrivacy();
});
install("memoryCorrect", async () => {
  const id = byId("memoryRecordId").value;
  await jsonRequest(`/context/memory/${encodeURIComponent(id)}/correct`, { method: "POST", body: JSON.stringify({
    content: { correction: byId("memoryCorrection").value }, reason: "person correction",
  }) });
});
install("memoryDelete", async () => {
  if (!byId("memoryDeleteConfirmed").checked) throw new Error("Confirm deletion before continuing.");
  const id = byId("memoryRecordId").value;
  await jsonRequest(`/context/memory/${encodeURIComponent(id)}`, { method: "DELETE" });
});
install("memoryShare", async () => {
  if (!byId("shareConfirmed").checked) throw new Error("Review and confirm the share preview first.");
  const id = byId("memoryRecordId").value;
  await jsonRequest(`/context/memory/${encodeURIComponent(id)}/share`, { method: "POST", body: JSON.stringify({
    target_space_id: byId("shareTargetSpace").value,
  }) });
});
install("charterSave", async () => {
  const principles = byId("charterPrinciples").value.split("\n").map((item) => item.trim()).filter(Boolean);
  await jsonRequest("/context/charter", { method: "PUT", body: JSON.stringify({ principles, origin: "person" }) });
});
install("goalCreate", async () => {
  await jsonRequest("/context/goals", { method: "POST", body: JSON.stringify({
    title: byId("goalTitle").value, space_id: byId("goalSpaceId").value, origin: "person",
  }) });
});
install("commitmentCreate", async () => {
  await jsonRequest("/context/commitments", { method: "POST", body: JSON.stringify({
    title: byId("commitmentTitle").value, space_id: byId("commitmentSpaceId").value, origin: "person",
  }) });
});
install("contextCancel", async () => {
  for (const node of document.querySelectorAll("#contextControls input, #contextControls textarea")) {
    if (node.type === "checkbox") node.checked = false; else node.value = "";
  }
  status("Context changes cancelled.");
});
