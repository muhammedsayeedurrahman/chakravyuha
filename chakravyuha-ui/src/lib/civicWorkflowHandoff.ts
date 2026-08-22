import type { SmartResponse } from "@/services/api";

export type CivicJourney = "rti" | "schemes" | "cpgrams" | "rights";
export type CivicRightsDomain = "consumer" | "tenant" | "labour";

export interface CivicWorkflowContext {
  journey: CivicJourney;
  narrative: string;
  domain?: CivicRightsDomain;
  language: string;
}

export interface CivicWorkflowLaunch extends CivicWorkflowContext {
  intent: string;
  workflow: string;
  routingConfidence: number;
}

export const MIN_AUTOMATIC_CIVIC_CONFIDENCE = 0.8;

const JOURNEY_ALIASES: Record<string, CivicJourney> = {
  rti: "rti",
  information_request: "rti",
  cpgrams: "cpgrams",
  government_service_grievance: "cpgrams",
  scheme_eligibility: "schemes",
  schemes: "schemes",
  rights_guidance: "rights",
  rights: "rights",
};

const INTENT_JOURNEYS: Record<string, CivicJourney> = {
  information_request: "rti",
  government_service_grievance: "cpgrams",
  scheme_eligibility: "schemes",
  rights_guidance: "rights",
};

function normalized(value: string | null | undefined): string {
  return value?.trim().toLowerCase() ?? "";
}

function journeyFor(value: string | null | undefined): CivicJourney | null {
  return JOURNEY_ALIASES[normalized(value)] ?? null;
}

function rightsDomainFor(value: string | null | undefined): CivicRightsDomain | undefined {
  const candidate = normalized(value);
  return candidate === "consumer" || candidate === "tenant" || candidate === "labour"
    ? candidate
    : undefined;
}

/** Preserve form context after a workflow has already selected another civic journey. */
export function createCivicWorkflowContext(
  journey: CivicJourney,
  narrative: string,
  language: string = "en-IN",
  domain?: string | null,
): CivicWorkflowContext | null {
  const preservedNarrative = narrative.trim();
  if (!preservedNarrative) return null;

  const rightsDomain = journey === "rights" ? rightsDomainFor(domain) : undefined;
  return {
    journey,
    narrative: preservedNarrative,
    ...(rightsDomain ? { domain: rightsDomain } : {}),
    language,
  };
}

/** Read a server-selected civic destination without classifying user text. */
export function civicJourneyForResponse(data: SmartResponse): CivicJourney | null {
  return journeyFor(data.handoff?.journey)
    ?? journeyFor(data.workflow)
    ?? journeyFor(data.intent);
}

/** Build the typed context transferred by an explicit or automatic UI launch. */
export function createCivicWorkflowLaunch(
  data: SmartResponse,
  narrative: string,
  language: string = "en-IN",
): CivicWorkflowLaunch | null {
  const preservedNarrative = narrative.trim();
  const intent = normalized(data.intent);
  const expectedJourney = INTENT_JOURNEYS[intent];
  const explicitJourney = journeyFor(data.handoff?.journey);
  const handoffIntent = normalized(data.handoff?.intent);
  const workflow = normalized(data.handoff?.workflow ?? data.workflow);
  const workflowJourney = journeyFor(workflow);
  const handler = data.handoff?.handler?.trim();
  const routingConfidence = typeof data.routing_confidence === "number"
    && Number.isFinite(data.routing_confidence)
    ? data.routing_confidence
    : 0;

  if (
    !preservedNarrative
    || !expectedJourney
    || !explicitJourney
    || explicitJourney !== expectedJourney
    || (handoffIntent !== "" && handoffIntent !== intent)
    || workflowJourney !== expectedJourney
    || !handler
  ) {
    return null;
  }

  const context = createCivicWorkflowContext(
    expectedJourney,
    preservedNarrative,
    language,
    data.handoff?.domain ?? data.domain,
  );
  if (!context) return null;

  return {
    ...context,
    intent,
    workflow: workflow || normalized(data.workflow) || expectedJourney,
    routingConfidence,
  };
}

/** Gate automatic navigation using backend router metadata and contract integrity. */
export function resolveAutomaticCivicHandoff(
  data: SmartResponse,
  narrative: string,
  language: string = "en-IN",
): CivicWorkflowLaunch | null {
  if (
    data.source !== "intent_router"
    || data.automatic_handoff !== true
    || normalized(data.handoff?.intent) !== normalized(data.intent)
    || typeof data.routing_confidence !== "number"
    || data.routing_confidence < MIN_AUTOMATIC_CIVIC_CONFIDENCE
  ) {
    return null;
  }

  return createCivicWorkflowLaunch(data, narrative, language);
}
