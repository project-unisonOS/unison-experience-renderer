function requiredNodes(sem) {
  return Array.isArray(sem?.nodes) ? sem.nodes.filter((node) => node && node.required === true) : [];
}

function allNodes(sem) {
  return Array.isArray(sem?.nodes) ? sem.nodes.filter((node) => node && typeof node.node_id === "string") : [];
}

function nodeText(node, detailed = false) {
  if (detailed && typeof node.detail === "string" && node.detail.trim()) return node.detail.trim();
  if (typeof node.summary === "string" && node.summary.trim()) return node.summary.trim();
  if (node.value !== undefined && node.value !== null) {
    const value = typeof node.value === "object" ? JSON.stringify(node.value) : String(node.value);
    return `${node.label}: ${value}`;
  }
  return String(node.label || "").trim();
}

function validateSem(sem) {
  if (!sem || sem.schema_version !== "sem.v1" || typeof sem.experience_id !== "string" || typeof sem.outcome !== "string") {
    throw new Error("invalid semantic experience");
  }
  const nodeIds = new Set(allNodes(sem).map((node) => node.node_id));
  for (const action of Array.isArray(sem.actions) ? sem.actions : []) {
    if (!action || typeof action.action_id !== "string" || typeof action.consequence !== "string") throw new Error("invalid semantic action");
  }
  return nodeIds;
}

export function composeConversation(sem) {
  validateSem(sem);
  const nodes = allNodes(sem);
  const required = requiredNodes(sem);
  const references = new Map(nodes.map((node, index) => [String(index + 1), node.node_id]));
  let interrupted = false;
  let cursor = null;
  const expression = {
    schema_version: "semantic-expression.v1",
    experience_id: sem.experience_id,
    modality: "conversation",
    summary: sem.outcome,
    segments: [
      { kind: "outcome", text: sem.outcome },
      ...required.filter((node) => nodeText(node) !== sem.outcome).map((node) => ({ kind: "required", node_id: node.node_id, text: nodeText(node) })),
      ...(sem.actions || []).map((action) => ({ kind: "action", action_id: action.action_id, text: `${action.label}. ${action.consequence}`, confirmation_required: action.confirmation_required === true })),
      ...(sem.recovery ? [{ kind: "recovery", text: sem.recovery }] : []),
    ],
    action_ids: (sem.actions || []).map((action) => action.action_id),
    required_node_ids: required.map((node) => node.node_id),
    fallback: sem.recovery || "I can provide the essential outcome as plain text.",
  };
  return {
    expression,
    interrupt() { interrupted = true; },
    resume() { interrupted = false; return expression.summary; },
    isInterrupted() { return interrupted; },
    moreDetail(reference) {
      const nodeId = references.get(String(reference)) || String(reference);
      const node = nodes.find((candidate) => candidate.node_id === nodeId);
      if (!node) return null;
      cursor = node.node_id;
      return nodeText(node, true);
    },
    correct(reference) { return this.moreDetail(reference); },
    currentReference() { return cursor; },
    cancel(actionId) {
      const action = (sem.actions || []).find((candidate) => candidate.action_id === actionId);
      return action ? action.cancellation || `Cancelled ${action.label}` : null;
    },
    recover() { return sem.recovery || expression.fallback; },
  };
}

export function composeVisual(sem) {
  validateSem(sem);
  const required = requiredNodes(sem);
  const nodes = allNodes(sem);
  return {
    schema_version: "semantic-expression.v1",
    experience_id: sem.experience_id,
    modality: "visual",
    summary: sem.outcome,
    segments: nodes.map((node) => ({ kind: node.kind, node_id: node.node_id, label: node.label, text: nodeText(node), exact: node.exact === true })),
    action_ids: (sem.actions || []).map((action) => action.action_id),
    required_node_ids: required.map((node) => node.node_id),
    fallback: sem.recovery || "The essential outcome remains available as text.",
  };
}

export function semanticDiff(left, right) {
  const findings = [];
  const compare = (code, lhs, rhs) => {
    const missing = [...new Set(lhs)].filter((value) => !new Set(rhs).has(value));
    const added = [...new Set(rhs)].filter((value) => !new Set(lhs).has(value));
    if (missing.length || added.length) findings.push({ severity: "error", code, missing, added });
  };
  compare("required-meaning", left.required_node_ids || [], right.required_node_ids || []);
  compare("available-actions", left.action_ids || [], right.action_ids || []);
  if (Boolean(left.fallback) !== Boolean(right.fallback)) findings.push({ severity: "error", code: "recovery" });
  return { equivalent: findings.length === 0, findings };
}

export class ModalityNeutralSession {
  constructor({ sessionId, personId }) {
    this.sessionId = sessionId;
    this.personId = personId;
    this.semanticFocus = null;
    this.dialogueReferences = {};
    this.pendingActionIds = [];
    this.progress = {};
    this.recovery = null;
    this.modality = null;
    this.revision = 1;
  }

  capture({ focus, references = {}, pendingActionIds = [], progress = {}, recovery = null }) {
    this.semanticFocus = focus;
    this.dialogueReferences = { ...references };
    this.pendingActionIds = [...pendingActionIds];
    this.progress = { ...progress };
    this.recovery = recovery;
    this.revision += 1;
  }

  switchTo(sem, modality) {
    const expression = modality === "conversation" ? composeConversation(sem).expression : composeVisual(sem);
    this.modality = modality;
    this.revision += 1;
    return expression;
  }
}
