import assert from "node:assert/strict";
import test from "node:test";

import {
  INITIAL_CPGRAMS_HANDOFF_STATE,
  cpgramsHandoffBlockers,
  cpgramsHandoffReducer,
  cpgramsReviewBlockers,
  type CPGRAMSHandoffMachineState,
// @ts-expect-error Node's native TypeScript runner requires the explicit extension.
} from "./cpgramsHandoffMachine.ts";

function preparedState(): CPGRAMSHandoffMachineState {
  return cpgramsHandoffReducer(INITIAL_CPGRAMS_HANDOFF_STATE, {
    type: "PREPARATION_RECEIVED",
    backendState: "PREPARED",
    serverBlockers: [],
    hasDraft: true,
    subject: "Repair the municipal road",
    draftText: "The road has remained unrepaired despite repeated complaints.",
  });
}

test("completes the explicit human-controlled hand-off sequence", () => {
  assert.equal(INITIAL_CPGRAMS_HANDOFF_STATE.phase, "DRAFT");
  let state = preparedState();
  assert.equal(state.phase, "PREPARED");

  state = cpgramsHandoffReducer(state, { type: "REVIEW_REQUESTED" });
  assert.equal(state.phase, "REVIEWED");

  state = cpgramsHandoffReducer(state, { type: "CONFIRMATION_REQUESTED" });
  assert.equal(state.phase, "CONFIRMATION_REQUIRED");
  assert.deepEqual(cpgramsHandoffBlockers(state, true), [
    "Select the mandatory confirmation checkbox.",
  ]);

  state = cpgramsHandoffReducer(state, { type: "CONFIRMATION_CHANGED", accepted: true });
  assert.deepEqual(cpgramsHandoffBlockers(state, true), []);

  state = cpgramsHandoffReducer(state, { type: "HANDOFF_REQUESTED" });
  assert.equal(state.phase, "HANDOFF");
});

test("refuses review and hand-off while an exact server prerequisite is unmet", () => {
  const blocker = "Provide the State or Union Territory.";
  let state = cpgramsHandoffReducer(INITIAL_CPGRAMS_HANDOFF_STATE, {
    type: "PREPARATION_RECEIVED",
    backendState: "DRAFT",
    serverBlockers: [blocker],
    hasDraft: true,
    subject: "Repair the municipal road",
    draftText: "The road has remained unrepaired despite repeated complaints.",
  });

  assert.equal(state.phase, "DRAFT");
  assert.deepEqual(cpgramsReviewBlockers(state), [blocker]);

  state = cpgramsHandoffReducer(state, { type: "REVIEW_REQUESTED" });
  assert.equal(state.phase, "DRAFT");
  state = cpgramsHandoffReducer(state, { type: "HANDOFF_REQUESTED" });
  assert.equal(state.phase, "DRAFT");
});

test("editing a reviewed or confirmed draft invalidates review and confirmation", () => {
  let state = preparedState();
  state = cpgramsHandoffReducer(state, { type: "REVIEW_REQUESTED" });
  state = cpgramsHandoffReducer(state, { type: "CONFIRMATION_REQUESTED" });
  state = cpgramsHandoffReducer(state, { type: "CONFIRMATION_CHANGED", accepted: true });

  state = cpgramsHandoffReducer(state, {
    type: "DRAFT_EDITED",
    subject: "Updated road repair grievance",
    draftText: "Updated reviewed text.",
  });
  assert.equal(state.phase, "PREPARED");
  assert.equal(state.confirmationAccepted, false);

  state = cpgramsHandoffReducer(state, { type: "REVIEW_REQUESTED" });
  state = cpgramsHandoffReducer(state, { type: "CONFIRMATION_REQUESTED" });
  state = cpgramsHandoffReducer(state, { type: "CONFIRMATION_CHANGED", accepted: true });
  state = cpgramsHandoffReducer(state, {
    type: "DRAFT_EDITED",
    subject: "",
    draftText: "Updated reviewed text.",
  });
  assert.equal(state.phase, "DRAFT");
  assert.equal(state.confirmationAccepted, false);
  assert.deepEqual(cpgramsReviewBlockers(state), ["A grievance subject is required."]);
});
