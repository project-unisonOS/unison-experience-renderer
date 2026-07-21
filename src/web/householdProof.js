const byId = (id) => document.getElementById(id);
const outcome = (message) => { const node = byId("householdOutcome"); if (node) node.textContent = message; };

async function jsonRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Household request was denied.");
  return body;
}

function install(id, handler) {
  const node = byId(id);
  if (!node) return;
  node.addEventListener("click", async () => {
    try { await handler(); }
    catch (error) { outcome(`${error.message || "Household request was denied."} No private record existence was revealed.`); }
  });
}

install("householdMembersRefresh", async () => {
  const body = await jsonRequest("/household/members");
  const names = (body.members || []).map((member) => `${member.display_name}: ${member.membership_role}, ${member.status}`);
  byId("householdMembers").textContent = names.join("; ") || "No active household members.";
  outcome("Membership review includes operational identity facts only, never private activity or data.");
});
install("householdInvite", async () => {
  const body = await jsonRequest("/household/invitations", { method: "POST", body: JSON.stringify({
    intended_role: "adult-member", ttl_minutes: Number(byId("householdInvitationMinutes").value || 30),
  }) });
  outcome(`Invitation ${body.invitation_id} created. One-use token: ${body.invitation_token}. It expires at ${body.expires_at}.`);
});
install("householdRemove", async () => {
  if (!byId("householdRemoveConfirmed").checked) throw new Error("Confirm the removal consequences first.");
  const person = encodeURIComponent(byId("householdRemovePerson").value);
  await jsonRequest(`/household/members/${person}`, { method: "DELETE" });
  outcome("Membership and shared access were revoked. Private keys and data were not transferred.");
});

function coordinationBase(action, purpose) {
  return {
    version: "4.0", household_id: byId("householdId").value,
    space_id: byId("householdSpaceId").value, action, purpose,
  };
}
install("householdCalendarAdd", async () => {
  await jsonRequest("/household/coordinate", { method: "POST", body: JSON.stringify({
    ...coordinationBase("create", "household calendar coordination"), artifact_kind: "calendar_event",
    calendar: { title: byId("householdCalendarTitle").value, starts_at: byId("householdCalendarStart").value, ends_at: byId("householdCalendarEnd").value },
  }) });
  outcome("Shared calendar event added without reading either assistant's private memory.");
});
install("householdGroceryAdd", async () => {
  await jsonRequest("/household/coordinate", { method: "POST", body: JSON.stringify({
    ...coordinationBase("create", "household grocery coordination"), artifact_kind: "grocery_item",
    grocery: { item: byId("householdGroceryItem").value, quantity: byId("householdGroceryQuantity").value },
  }) });
  outcome("Shared grocery item added without reading either assistant's private memory.");
});
install("householdArtifactsRefresh", async () => {
  const body = await jsonRequest("/household/coordinate", { method: "POST", body: JSON.stringify(coordinationBase("list", "review shared artifacts")) });
  outcome(`${(body.artifacts || []).length} shared artifacts found. Private sources read: ${body.private_sources_read || 0}.`);
});
install("householdAuditRefresh", async () => {
  const space = encodeURIComponent(byId("householdSpaceId").value);
  const body = await jsonRequest(`/household/audit?space_id=${space}`);
  outcome(`${(body.events || []).length} shared audit events are visible. Private audit events remain hidden.`);
});
install("householdResourcesRefresh", async () => {
  const body = await jsonRequest("/household/resources");
  outcome(`${body.assistant_count} assistants have independent concurrency, queue, CPU, and memory limits. Task content is not included.`);
});
install("householdRecoveryReview", async () => {
  outcome("Restart requeues opaque interrupted tasks; member removal rotates the shared-space key; rollback restores configuration without transferring private keys.");
});
install("householdCancel", async () => {
  for (const node of document.querySelectorAll("#householdControls input")) {
    if (node.type === "checkbox") node.checked = false; else node.value = "";
  }
  outcome("Household changes cancelled.");
});
