const byId = (id) => document.getElementById(id);
const outcome = byId("telegramOutcome");

function setOutcome(message) {
  if (outcome) outcome.textContent = message;
}

function accountId() {
  return byId("telegramAccountId")?.value.trim() || "";
}

async function jsonRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Remote channel request was denied.");
  return body;
}

function install(id, handler) {
  byId(id)?.addEventListener("click", async () => {
    try { await handler(); }
    catch (error) { setOutcome(`${error.message || "Remote channel request was denied."} No private record existence is revealed.`); }
  });
}

install("telegramRegister", async () => {
  if (!byId("telegramDisclosureAccepted")?.checked) {
    setOutcome("Review and accept the Telegram privacy disclosure before connecting.");
    throw new Error("Review and accept the Telegram privacy disclosure before connecting.");
  }
  const token = byId("telegramBotToken")?.value || "";
  if (!accountId() || !token || !byId("telegramBotId")?.value.trim()) {
    setOutcome("Provider account name, bot identifier, and bot token are required.");
    throw new Error("Provider account name, bot identifier, and bot token are required.");
  }
  await jsonRequest("/remote-assistant/telegram/register", { method: "POST", body: JSON.stringify({
    provider_account_id: accountId(), bot_id: byId("telegramBotId").value.trim(), bot_token: token,
  }) });
  setOutcome("Credential stored in your encrypted namespace. Pairing still requires stronger local authentication.");
  byId("telegramBotToken").value = "";
});

install("telegramPair", async () => {
  const body = await jsonRequest("/remote-assistant/telegram/pair", { method: "POST", body: JSON.stringify({
    provider_account_id: accountId(),
  }) });
  byId("telegramPairingCode").textContent = `Send /pair ${body.pairing_code} in your private bot chat. Expires ${body.expires_at}.`;
  setOutcome("Strong local authentication is required and succeeded. Send the one-use code only in your private bot chat.");
});

install("telegramCheck", async () => {
  const body = await jsonRequest("/remote-assistant/telegram/check", { method: "POST", body: JSON.stringify({
    provider_account_id: accountId(),
  }) });
  setOutcome(`${body.status || "unavailable"}. Connection checks disclose only coarse outcomes. No private record existence is revealed.`);
});

install("telegramRevoke", async () => {
  if (!byId("telegramRevokeConfirmed")?.checked) {
    setOutcome("Confirm revocation before the credential and binding are cleared.");
    throw new Error("Confirm revocation before the credential and binding are cleared.");
  }
  await jsonRequest(`/remote-assistant/telegram/${encodeURIComponent(accountId())}`, { method: "DELETE" });
  setOutcome("Channel and binding revoked. Also revoke a stolen token with BotFather before pairing a replacement.");
});

byId("telegramCancel")?.addEventListener("click", () => {
  byId("telegramBotToken").value = "";
  byId("telegramDisclosureAccepted").checked = false;
  byId("telegramRevokeConfirmed").checked = false;
  setOutcome("Remote-channel changes cancelled. No message was sent.");
});
