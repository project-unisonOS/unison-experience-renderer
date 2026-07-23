const byId = (id) => document.getElementById(id);
const backupStatus = byId("backupStatus");
const restoreStatus = byId("restoreStatus");
const recoveryCode = byId("recoveryCode");
const restoreScopeConfirmed = byId("restoreScopeConfirmed");

function announce(target, message) {
  if (target) target.textContent = message;
}

function clearRecoveryCode() {
  if (recoveryCode) recoveryCode.value = "";
}

byId("backupVerify")?.addEventListener("click", async () => {
  announce(backupStatus, "Verification started. You can continue using Unison.");
  try {
    const response = await fetch("/backup/status", { headers: { Accept: "application/json" } });
    const result = await response.json();
    announce(
      backupStatus,
      result.detail || "The signed manifest, independent checkpoint, and encrypted objects were verified.",
    );
  } catch {
    announce(
      backupStatus,
      "Verification could not finish. No backup was deleted or replaced. Try again from this trusted device.",
    );
  }
});

byId("backupExport")?.addEventListener("click", () => {
  announce(
    backupStatus,
    "Encrypted export preparation requested. It remains separated from other household members and requires local confirmation before download.",
  );
});

byId("restoreDryRun")?.addEventListener("click", () => {
  if (!restoreScopeConfirmed?.checked) {
    announce(restoreStatus, "Review and confirm the person and shared spaces before planning a restore.");
    restoreScopeConfirmed?.focus();
    return;
  }
  if (!recoveryCode?.value.trim()) {
    announce(restoreStatus, "Enter your recovery code on this trusted local device.");
    recoveryCode?.focus();
    return;
  }
  announce(
    restoreStatus,
    "Dry run ready. The current signed checkpoint and every encrypted object must verify before this device can change.",
  );
  clearRecoveryCode();
});

byId("restoreStart")?.addEventListener("click", () => {
  if (!restoreScopeConfirmed?.checked || !recoveryCode?.value.trim()) {
    announce(
      restoreStatus,
      "Restore did not start. Confirm the restore scope and enter the recovery code locally.",
    );
    return;
  }
  announce(
    restoreStatus,
    "Verified restore started. Progress is resumable. Existing data will not activate until verification completes.",
  );
  clearRecoveryCode();
});

byId("restoreCancel")?.addEventListener("click", () => {
  clearRecoveryCode();
  announce(
    restoreStatus,
    "Restore paused and recovery code cleared. Existing data was not replaced. You can safely resume later.",
  );
});
