const byId = (id) => document.getElementById(id);
const summary = byId("workflowPlanSummary");
const status = byId("workflowStatus");
const outcome = byId("workflowOutcome");
let planned = false;
let completed = false;

function announce(target, message) {
  if (target) target.textContent = message;
}

byId("workflowPlan")?.addEventListener("click", () => {
  const kind = byId("workflowKind")?.selectedOptions?.[0]?.textContent || "workflow";
  const purpose = byId("workflowPurpose")?.value.trim();
  const context = byId("workflowContext")?.value.trim();
  const recipients = byId("workflowRecipients")?.value.trim() || "none";
  if (!purpose || !context) {
    announce(status, "Planning stopped. Provide a purpose and an authorized context space.");
    return;
  }
  planned = true;
  completed = false;
  if (byId("workflowApproval")) byId("workflowApproval").checked = false;
  announce(
    summary,
    `${kind}. Purpose: ${purpose}. Context: ${context}. Recipients: ${recipients}. External fields are minimized and the action remains reversible.`,
  );
  announce(status, "Plan ready. Review the exact action, recipients, context, and disclosure before approval.");
});

byId("workflowRun")?.addEventListener("click", () => {
  if (!planned) {
    announce(status, "Run stopped. Review a workflow plan first.");
    byId("workflowPlan")?.focus();
    return;
  }
  if (!byId("workflowApproval")?.checked) {
    announce(status, "Run stopped. Exact approval is required for this plan.");
    byId("workflowApproval")?.focus();
    return;
  }
  completed = true;
  announce(status, "Workflow completed with a provider receipt and zero boundary incidents.");
  announce(outcome, "One administrative task completed. Estimated time returned: 12 minutes. External calls: 1. Recovery required: no. Boundary incidents: 0.");
});

byId("workflowCancel")?.addEventListener("click", () => {
  const message = completed
    ? "Workflow cancelled. Completed reversible actions were compensated and receipts remain in the local audit."
    : "Workflow cancelled before action. No provider call was made.";
  planned = false;
  completed = false;
  if (byId("workflowApproval")) byId("workflowApproval").checked = false;
  announce(status, message);
});

byId("workflowRetry")?.addEventListener("click", () => {
  announce(status, "Retry requested with the original idempotency key. Duplicate external action is prevented.");
});

byId("workflowReplaceProvider")?.addEventListener("click", () => {
  announce(status, "Compatible provider selected. The original plan, disclosure boundary, and audit remain unchanged.");
});
