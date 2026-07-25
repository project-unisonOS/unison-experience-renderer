const byId = (id) => document.getElementById(id);
const headers = () => {
  const token = window.localStorage.getItem("unison.session.token");
  return { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) };
};

let sessionId = null;
const pendingSourceIds = [];

async function request(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { ...headers(), ...(options.headers || {}) } });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "The request was not accepted.");
  return body;
}

function fileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("This file could not be read."));
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.readAsDataURL(file);
  });
}

async function previewImport() {
  const files = [...(byId("lifeSourceFiles")?.files || []), ...(byId("lifeCameraPages")?.files || [])];
  if (!files.length) throw new Error("Choose a file or scan a page first.");
  const status = byId("lifeImportStatus");
  status.textContent = `Preparing ${files.length} private source${files.length === 1 ? "" : "s"}.`;
  const session = await request("/life-operations/imports", {
    method: "POST", body: JSON.stringify({ channel: byId("lifeCameraPages")?.files?.length ? "camera" : "file" }),
  });
  sessionId = session.session_id;
  const list = byId("lifeImportPreviewList");
  list.replaceChildren();
  for (const file of files) {
    const source = await request(`/life-operations/imports/${encodeURIComponent(sessionId)}/sources`, {
      method: "POST", body: JSON.stringify({ filename: file.name, media_type: file.type || "application/octet-stream", content_b64: await fileAsBase64(file) }),
    });
    pendingSourceIds.push(source.source_id);
    const item = document.createElement("li");
    const flags = (source.security_flags || []).filter((flag) => flag !== "untrusted-content");
    item.textContent = `${source.filename}, ${source.size_bytes} bytes, private${flags.length ? `. Review flag: ${flags.join(", ")}` : ""}.`;
    list.append(item);
  }
  status.textContent = "Review the source names and any safety flags, then choose whether to keep them privately.";
  byId("lifeImportAdmit")?.focus();
}

async function admitImport() {
  if (!sessionId) throw new Error("There is no reviewed import to keep.");
  await request(`/life-operations/imports/${encodeURIComponent(sessionId)}/admit`, { method: "POST", body: "{}" });
  byId("lifeImportStatus").textContent = "The reviewed sources are encrypted and available in your private source library.";
  sessionId = null;
  pendingSourceIds.length = 0;
}

async function loadCatalog() {
  const body = await request("/life-operations/catalog");
  const select = byId("lifeProvider");
  select.replaceChildren();
  for (const [id, manifest] of Object.entries(body.providers || {})) {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = `${id.replaceAll("-", " ")}: ${(manifest.scopes || []).join(", ")}`;
    select.append(option);
  }
}

async function startConnection() {
  const providerId = byId("lifeProvider").value;
  if (providerId === "local-folder" || providerId === "bounded-mcp") {
    byId("lifeConnectionStatus").textContent = "Choose a folder or MCP resource through the trusted local picker. Unison will store only its bounded read grant.";
    return;
  }
  const setup = await request("/life-operations/connections/oauth/start", {
    method: "POST", body: JSON.stringify({ provider_id: providerId, redirect_uri: `${window.location.origin}/life-operations/oauth/callback` }),
  });
  byId("lifeConnectionStatus").textContent = `The secure ${providerId.replaceAll("-", " ")} sandbox authorization is ready. PKCE ${setup.code_challenge_method} protects the callback. Continue only on the provider page and review its read-only scopes.`;
}

async function refreshConnections() {
  const [connections, sources] = await Promise.all([
    request("/life-operations/connections"), request("/life-operations/sources"),
  ]);
  const list = byId("lifeConnectionList");
  list.replaceChildren();
  for (const connection of connections.connections || []) {
    const item = document.createElement("li");
    item.textContent = `${connection.provider_id}: ${connection.status}, read only, scopes ${(connection.scopes || []).join(", ")}.`;
    list.append(item);
  }
  byId("lifeConnectionStatus").textContent = `${connections.connections?.length || 0} connection(s) and ${sources.sources?.length || 0} private source(s).`;
}

function report(target, fn) {
  return async () => {
    try { await fn(); } catch (error) { byId(target).textContent = error.message; }
  };
}

byId("lifeImportPreview")?.addEventListener("click", report("lifeImportStatus", previewImport));
byId("lifeImportAdmit")?.addEventListener("click", report("lifeImportStatus", admitImport));
byId("lifeConnectionStart")?.addEventListener("click", report("lifeConnectionStatus", startConnection));
byId("lifeConnectionsRefresh")?.addEventListener("click", report("lifeConnectionStatus", refreshConnections));
loadCatalog().catch((error) => { byId("lifeConnectionStatus").textContent = error.message; });
