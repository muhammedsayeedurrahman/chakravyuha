import assert from "node:assert/strict";
import test from "node:test";

import type { SmartResponse } from "../services/api.ts";
import {
  civicJourneyForResponse,
  createCivicWorkflowContext,
  createCivicWorkflowLaunch,
  resolveAutomaticCivicHandoff,
// @ts-expect-error Node's native TypeScript runner requires the explicit extension.
} from "./civicWorkflowHandoff.ts";

function routedResponse(overrides: Partial<SmartResponse> = {}): SmartResponse {
  return {
    scenario: "cpgrams",
    title: "Government service grievance identified",
    guidance: "Continue in the CPGRAMS assistant.",
    sections: [],
    outcome: "Continue to the matched guided workflow.",
    severity: "low",
    complaint_draft: "",
    helplines: [],
    source: "intent_router",
    response_language: "en-IN",
    intent: "government_service_grievance",
    workflow: "cpgrams",
    domain: null,
    routing_confidence: 0.9,
    automatic_handoff: true,
    handoff: {
      journey: "cpgrams",
      workflow: "cpgrams",
      handler: "cpgrams_assistant",
      intent: "government_service_grievance",
    },
    ...overrides,
  };
}

test("selects the backend-mapped civic journey for each supported intent", () => {
  const cases: Array<[Partial<SmartResponse>, string]> = [
    [{
      scenario: "cpgrams",
      intent: "government_service_grievance",
      workflow: "cpgrams",
      handoff: { journey: "cpgrams", handler: "cpgrams_assistant" },
    }, "cpgrams"],
    [{
      scenario: "rti",
      intent: "information_request",
      workflow: "rti",
      handoff: { journey: "rti", handler: "rti_assistant" },
    }, "rti"],
    [{
      scenario: "rights_guidance",
      intent: "rights_guidance",
      workflow: "rights_guidance",
      domain: "tenant",
      handoff: { journey: "rights", handler: "rights_navigator", domain: "tenant" },
    }, "rights"],
    [{
      scenario: "scheme_eligibility",
      intent: "scheme_eligibility",
      workflow: "scheme_eligibility",
      handoff: { journey: "scheme_eligibility", handler: "scheme_eligibility" },
    }, "schemes"],
  ];

  for (const [overrides, journey] of cases) {
    assert.equal(civicJourneyForResponse(routedResponse(overrides)), journey);
  }
});

test("creates an automatic internal workflow launch", () => {
  const launch = resolveAutomaticCivicHandoff(
    routedResponse(),
    "  Please repair this municipal road.  ",
    "en-IN",
  );

  assert.deepEqual(launch, {
    journey: "cpgrams",
    narrative: "Please repair this municipal road.",
    intent: "government_service_grievance",
    workflow: "cpgrams",
    routingConfidence: 0.9,
    language: "en-IN",
  });
});

test("keeps explicit workflow navigation compatible without automatic metadata", () => {
  const launch = createCivicWorkflowLaunch(
    routedResponse({ routing_confidence: null, automatic_handoff: false }),
    "Please repair this municipal road.",
  );

  assert.equal(launch?.journey, "cpgrams");
  assert.equal(launch?.routingConfidence, 0);
  assert.equal(
    resolveAutomaticCivicHandoff(
      routedResponse({ routing_confidence: null, automatic_handoff: false }),
      "Please repair this municipal road.",
    ),
    null,
  );
});

test("preserves the original narrative, language, and rights domain", () => {
  const narrative = "My employer has not paid my salary for three months.";
  const launch = resolveAutomaticCivicHandoff(
    routedResponse({
      scenario: "rights_guidance",
      intent: "rights_guidance",
      workflow: "rights_guidance",
      domain: "labour",
      routing_confidence: 0.92,
      handoff: {
        journey: "rights",
        workflow: "rights_guidance",
        handler: "rights_navigator",
        intent: "rights_guidance",
        domain: "labour",
      },
    }),
    narrative,
    "ta-IN",
  );

  assert.equal(launch?.journey, "rights");
  assert.equal(launch?.narrative, narrative);
  assert.equal(launch?.domain, "labour");
  assert.equal(launch?.language, "ta-IN");
});

test("preserves narrative and domain across an existing civic workflow redirect", () => {
  const narrative = "My landlord refuses to return my security deposit.";
  assert.deepEqual(
    createCivicWorkflowContext("rights", narrative, "en-IN", "tenant"),
    {
      journey: "rights",
      narrative,
      domain: "tenant",
      language: "en-IN",
    },
  );
});

test("refuses automatic handoff for low confidence or an invalid intent contract", () => {
  assert.equal(
    resolveAutomaticCivicHandoff(
      routedResponse({ routing_confidence: 0.79 }),
      "Please repair this road.",
    ),
    null,
  );
  assert.equal(
    resolveAutomaticCivicHandoff(
      routedResponse({ automatic_handoff: false }),
      "Please repair this road.",
    ),
    null,
  );
  assert.equal(
    resolveAutomaticCivicHandoff(
      routedResponse({ intent: "legal_query" }),
      "Explain this contract.",
    ),
    null,
  );
  assert.equal(
    resolveAutomaticCivicHandoff(
      routedResponse({ handoff: null }),
      "Please repair this road.",
    ),
    null,
  );
  assert.equal(
    resolveAutomaticCivicHandoff(
      routedResponse({
        workflow: "unknown_workflow",
        handoff: {
          journey: "cpgrams",
          workflow: "unknown_workflow",
          handler: "cpgrams_assistant",
          intent: "government_service_grievance",
        },
      }),
      "Please repair this road.",
    ),
    null,
  );
  assert.equal(
    resolveAutomaticCivicHandoff(
      routedResponse({
        handoff: {
          journey: "cpgrams",
          handler: "cpgrams_assistant",
          intent: "information_request",
        },
      }),
      "Please repair this road.",
    ),
    null,
  );
});
