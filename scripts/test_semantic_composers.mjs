import assert from "node:assert/strict";
import { ModalityNeutralSession, composeConversation, composeVisual, semanticDiff } from "../src/web/semanticComposer.js";

const sem = {
  schema_version: "sem.v1", experience_id: "calendar", outcome: "You have two calendar conflicts",
  nodes: [
    { node_id: "conflicts", kind: "value", label: "Conflicts", value: 2, summary: "Two meetings overlap", detail: "Design review overlaps the dentist appointment", required: true, exact: true },
    { node_id: "option", kind: "entity", label: "Second option", summary: "Move design review", detail: "Move design review to 3 PM", required: false, exact: false },
  ],
  actions: [{ action_id: "move", label: "Move design review", consequence: "Proposes 3 PM", confirmation_required: true, risk: "medium", provenance: [{ source_id: "calendar-api" }] }],
  recovery: "Keep the calendar unchanged",
};

const conversation = composeConversation(sem);
const visual = composeVisual(sem);
assert.equal(conversation.expression.summary, visual.summary);
assert.deepEqual(conversation.expression.required_node_ids, visual.required_node_ids);
assert.deepEqual(conversation.expression.action_ids, visual.action_ids);
assert.equal(conversation.moreDetail("2"), "Move design review to 3 PM");
conversation.interrupt();
assert.equal(conversation.isInterrupted(), true);
assert.equal(conversation.resume(), sem.outcome);
assert.equal(conversation.cancel("move"), "Cancelled Move design review");
assert.equal(conversation.recover(), "Keep the calendar unchanged");
assert.throws(() => composeVisual({ schema_version: "sem.v1" }), /invalid semantic experience/);
assert.equal(semanticDiff(conversation.expression, visual).equivalent, true);
const session = new ModalityNeutralSession({ sessionId: "s", personId: "p" });
session.capture({ focus: "conflicts", references: { "1": "conflicts" }, pendingActionIds: ["move"], recovery: sem.recovery });
const switched = session.switchTo(sem, "visual");
assert.equal(switched.modality, "visual");
assert.equal(session.semanticFocus, "conflicts");
assert.deepEqual(session.pendingActionIds, ["move"]);
assert.equal(session.recovery, sem.recovery);
assert.equal(semanticDiff(conversation.expression, { ...visual, required_node_ids: [] }).equivalent, false);
assert.equal(semanticDiff(conversation.expression, { ...visual, action_risk: { move: "low" } }).equivalent, false);
assert.equal(semanticDiff(conversation.expression, { ...visual, provenance_source_ids: [] }).equivalent, false);

console.log("semantic composer conformance passed");
