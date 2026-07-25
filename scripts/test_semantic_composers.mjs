import assert from "node:assert/strict";
import { composeConversation, composeVisual } from "../src/web/semanticComposer.js";

const sem = {
  schema_version: "sem.v1", experience_id: "calendar", outcome: "You have two calendar conflicts",
  nodes: [
    { node_id: "conflicts", kind: "value", label: "Conflicts", value: 2, summary: "Two meetings overlap", detail: "Design review overlaps the dentist appointment", required: true, exact: true },
    { node_id: "option", kind: "entity", label: "Second option", summary: "Move design review", detail: "Move design review to 3 PM", required: false, exact: false },
  ],
  actions: [{ action_id: "move", label: "Move design review", consequence: "Proposes 3 PM", confirmation_required: true }],
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

console.log("semantic composer conformance passed");
