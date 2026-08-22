/**
 * Typed API client for the Chakravyuha FastAPI backend.
 * All requests go through Next.js rewrites → localhost:8000.
 */

// ── Types ────────────────────────────────────────────────────────────────────

export interface LegalSection {
  section_id: string;
  title: string;
  act: string;
  law?: string; // backend may return "law" instead of "act"
  description: string;
  punishment?: string;
  cognizable?: boolean | string;
  bailable?: boolean | string;
  court?: string;
  keywords?: string[];
  score?: number;
}

export interface TextQueryResponse {
  query: string;
  sections: LegalSection[];
  confidence: string;
  message: string | null;
  disclaimer: string;
}

export interface VoiceProcessResponse {
  success: boolean;
  data: {
    transcript?: string;
    text?: string;
    sections?: LegalSection[];
    audio?: string; // base64
    confidence?: number;
    language?: string;
  };
}

export interface GuidedOption {
  label: string;
  label_hi: string;
  next: string | null;
  sections: string[];
  severity: string | null;
}

export interface GuidedFlowStep {
  node_key: string;
  question: string;
  question_hi: string;
  options: GuidedOption[];
  is_leaf: boolean;
  matched_sections: LegalSection[];
  severity: string | null;
}

export interface GuidedFlowState {
  current_node: string;
  path: string[];
  selected_answer: string;
}

// ── Smart (Classification-first) Types ──────────────────────────────────────

export interface WorkflowHandoff {
  journey: string;
  handler: string;
  workflow?: string;
  intent?: string;
  domain?: string | null;
}

export interface SmartResponse {
  scenario: string;
  title: string;
  guidance: string;
  sections: string[];
  outcome: string;
  severity: string;
  complaint_draft: string;
  helplines: string[];
  source: string; // "classifier" or "rag_fallback"
  response_language: string; // e.g. "en-IN", "hi-IN", "ta-IN"
  intent?: string | null;
  workflow?: string | null;
  domain?: string | null;
  handoff?: WorkflowHandoff | null;
  routing_confidence?: number | null;
  automatic_handoff?: boolean;
}

export interface SmartVoiceResponse {
  transcript: string;
  confidence: number;
  language: string;
  response: SmartResponse | null;
  audio: string | null; // base64 TTS
  error: string | null;
}

// ── Auto-Draft (Agentic Complaint Drafting) Types ───────────────────────────

export interface AutoDraftRequest {
  narrative: string;
  complainant_name?: string;
  complainant_phone?: string;
  complainant_address?: string;
  complainant_email?: string;
  preferred_document_type?: string;
  language?: string;
}

export interface AutoDraftResponse {
  status: "success" | "needs_info" | "error";
  document_type: string;
  content: string;
  applicable_sections: string[];
  extracted_offense: string;
  offense_confidence: number;
  jurisdiction: string;
  punishment_summary: string;
  cognizable: boolean;
  bailable: boolean;
  strategy: {
    recommended_forum?: string;
    total_timeline?: string;
    total_estimated_cost?: string;
    next_immediate_action?: string;
    mediation_recommended?: boolean;
    evidence_checklist?: string[];
    steps?: { step: number; title: string; timeline: string; cost: string }[];
  } | null;
  missing_fields: string[];
  generated_at: string;
  error: string | null;
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch("/health", { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function queryLegal(
  query: string,
  language: string
): Promise<TextQueryResponse> {
  const res = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, language }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }

  return res.json();
}

export async function processVoice(
  audioBlob: Blob,
  language: string
): Promise<VoiceProcessResponse> {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  form.append("language", language);

  const res = await fetch("/api/voice", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Voice API error ${res.status}`);
  }

  return res.json();
}

// ── Smart (Classification-first) API Functions ─────────────────────────────

export async function smartQuery(
  query: string,
  language: string = "en-IN"
): Promise<SmartResponse> {
  const res = await fetch("/api/smart-query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, language }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `API error ${res.status}`);
  }

  return res.json();
}

export async function smartVoice(
  audioBlob: Blob,
  language: string
): Promise<SmartVoiceResponse> {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  form.append("language", language);

  const res = await fetch("/api/smart-voice", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Voice API error ${res.status}`);
  }

  return res.json();
}

export async function aiJudge(
  query: string,
  language: string = "en-IN"
): Promise<{
  scenario: string;
  title: string;
  outcome: string;
  severity: string;
  sections: string[];
}> {
  const res = await fetch("/api/judge", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, language }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Judge API error ${res.status}`);
  }

  return res.json();
}

export async function draftComplaint(
  query: string,
  language: string = "en-IN"
): Promise<{
  scenario: string;
  title: string;
  draft: string;
  available: boolean;
}> {
  const res = await fetch("/api/draft-complaint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, language }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Complaint API error ${res.status}`);
  }

  return res.json();
}

export async function startGuidedFlow(): Promise<GuidedFlowStep> {
  const res = await fetch("/api/guided/start", { method: "POST" });

  if (!res.ok) {
    throw new Error(`Guided flow start failed: ${res.status}`);
  }

  return res.json();
}

export async function nextGuidedStep(
  state: GuidedFlowState
): Promise<GuidedFlowStep> {
  const res = await fetch("/api/guided/next", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state),
  });

  if (!res.ok) {
    throw new Error(`Guided flow next failed: ${res.status}`);
  }

  return res.json();
}

// ── OpenClaw (Autonomous Form Filing) Types ──────────────────────────────────

export interface OpenClawPortal {
  id: string;
  name: string;
  url: string;
  description: string;
  required_fields: string[];
}

export interface OpenClawFilingRequest {
  portal_id: string;
  user_data: Record<string, string>;
  documents?: string[];
}

export interface OpenClawFilingResponse {
  session_id: string | null;
  portal_id: string;
  status: string;
  message: string;
  current_step: string;
  steps_completed: string[];
  reference_number: string | null;
  error: string | null;
  next_actions: string[];
  captcha_prompt?: string | null;
  captcha_image_base64?: string | null;
  payload_digest?: string | null;
  pending_action?: string | null;
}

// ── OpenClaw API Functions ───────────────────────────────────────────────────

export async function getOpenClawPortals(): Promise<OpenClawPortal[]> {
  const res = await fetch("/api/openclaw/portals");
  if (!res.ok) {
    throw new Error(`Failed to fetch portals: ${res.status}`);
  }
  return res.json();
}

export async function startOpenClawFiling(
  request: OpenClawFilingRequest
): Promise<OpenClawFilingResponse> {
  const res = await fetch("/api/openclaw/file", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `OpenClaw filing error ${res.status}`);
  }
  return res.json();
}

export async function pollOpenClawStatus(
  sessionId: string
): Promise<OpenClawFilingResponse> {
  const res = await fetch(`/api/openclaw/status/${sessionId}`);
  if (!res.ok) {
    throw new Error(`Status poll failed: ${res.status}`);
  }
  return res.json();
}

export async function submitOpenClawOTP(
  sessionId: string,
  otp: string
): Promise<{ success: boolean; message: string; next_actions: string[] }> {
  const res = await fetch("/api/openclaw/otp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, otp }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `OTP submit error ${res.status}`);
  }
  return res.json();
}

export async function submitOpenClawCaptcha(
  sessionId: string,
  captchaText: string
): Promise<{ success: boolean; message: string; next_actions: string[] }> {
  const res = await fetch("/api/openclaw/captcha", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, captcha_text: captchaText }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `CAPTCHA submit error ${res.status}`);
  }
  return res.json();
}

export async function confirmOpenClawSubmission(
  sessionId: string,
  payloadDigest: string,
  confirmed: boolean
): Promise<{ success: boolean; message: string; next_actions: string[] }> {
  const res = await fetch("/api/openclaw/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      payload_digest: payloadDigest,
      confirmed,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Confirmation error ${res.status}`);
  }
  return res.json();
}

// ── Auto-Draft (Agentic Complaint Drafting) ─────────────────────────────────

export async function autoDraft(
  request: AutoDraftRequest
): Promise<AutoDraftResponse> {
  const res = await fetch("/api/documents/auto-draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `Auto-draft error ${res.status}`);
  }

  return res.json();
}

// ── Civic assistant types ───────────────────────────────────────────────────

export type CivicConfidence =
  | "high"
  | "medium"
  | "low"
  | "requires_jurisdiction"
  | "requires_verification"
  | string;

export interface CivicProvenance {
  source?: string | null;
  source_url?: string | null;
  jurisdiction?: string | Record<string, unknown> | null;
  effective_date?: string | null;
  last_verified?: string | null;
  source_type?: string | null;
  status?: string | null;
}

export interface JurisdictionCompleteness {
  state_known: boolean;
  district_known: boolean;
  city_known: boolean;
  locality_known: boolean;
  authority_known: boolean;
}

export interface RTIIdentifyRequest {
  issue: string;
  state?: string;
  district?: string;
  city?: string;
  locality?: string;
  authority_hint?: string;
  road_type?: string;
  date_range?: string;
}

export interface RTIDepartmentResponse extends CivicProvenance {
  domain: string;
  likely_authority?: string | null;
  confidence: CivicConfidence | number;
  reason: string;
  missing_information: string[];
  jurisdiction_completeness: JurisdictionCompleteness;
  authority_type?: string | null;
  subtopic?: string | null;
  status?: string;
}

export interface RTIDraftRequest extends RTIIdentifyRequest {
  information_requests?: string[];
  applicant_name?: string;
  applicant_address?: string;
  applicant_contact?: string;
  is_indian_citizen?: boolean;
}

export interface RTIFilingGuidance {
  pathway?: string;
  steps?: string[];
  next_step?: string;
  warnings?: string[];
  sources?: CivicProvenance[];
}

export interface RTIDraftResponse extends CivicProvenance {
  status: string;
  domain?: string;
  likely_authority?: string;
  confidence?: CivicConfidence | number;
  routing?: RTIDepartmentResponse;
  information_requests: string[];
  content?: string;
  draft?: string;
  draft_text?: string;
  document_text?: string;
  download_filename?: string;
  missing_information: string[];
  filing_guidance?: RTIFilingGuidance | string[] | Record<string, unknown>;
  next_steps?: string[];
  disclaimer?: string;
}

export interface RTIGuideResponse extends CivicProvenance {
  title?: string;
  steps?: string[];
  guide?: string[] | string;
  filing_options?: string[];
  notes?: string[];
  disclaimer?: string;
}

export type SchemeProfileValue = string | number | boolean | null;
export type SchemeComparisonValue = SchemeProfileValue | SchemeProfileValue[];
export type SchemeProfile = Record<string, SchemeProfileValue>;

export interface SchemeCondition {
  rule_id?: string;
  field?: string;
  explanation: string;
  description?: string;
  outcome?: string;
  observed_value?: SchemeProfileValue;
  expected_value?: SchemeComparisonValue;
  operator?: string | null;
  effect?: string | null;
  reason?: string | null;
  question?: string | null;
  source_url?: string | null;
  expected?: SchemeComparisonValue;
  actual?: SchemeProfileValue;
}

export interface SchemeQuestion {
  rule_id?: string;
  field: string;
  question: string;
  reason?: string;
  input_type?: "text" | "number" | "boolean" | "select";
  options?: Array<string | { label: string; value: string }>;
  required?: boolean;
}

export interface SchemeSummary extends CivicProvenance {
  id: string;
  name: string;
  description?: string;
  required_documents?: string[];
  application_process?: string[] | string;
  official_portal_url?: string | null;
  helpline?: string | null;
}

export interface SchemeEligibilityResult extends CivicProvenance {
  scheme_id: string;
  scheme_name: string;
  description?: string;
  status: string;
  matched_conditions: SchemeCondition[];
  unknown_conditions: SchemeCondition[];
  potential_disqualifiers: SchemeCondition[];
  why: string;
  next_questions?: SchemeQuestion[];
  required_documents: string[];
  application_process?: string[] | string;
  official_portal_url?: string | null;
  helpline?: string | null;
  contact_guidance?: string | null;
  record_status?: string;
  verification_note?: string | null;
  evaluation_warnings?: string[];
  disclaimer?: string;
  provenance?: CivicProvenance;
}

export interface SchemeEligibilityRequest {
  profile: SchemeProfile;
  scheme_id?: string;
}

export interface SchemeGuidedResponse {
  profile?: SchemeProfile;
  questions?: SchemeQuestion[];
  next_questions?: SchemeQuestion[];
  results?: SchemeEligibilityResult[];
  schemes?: SchemeEligibilityResult[];
  candidates?: SchemeEligibilityResult[];
  status?: string;
  message?: string;
  complete?: boolean;
}

export interface CPGRAMSPrepareRequest {
  grievance: string;
  state?: string;
  district?: string;
  city?: string;
  locality?: string;
  organisation_hint?: string;
  incident_date?: string;
  prior_reference?: string;
  desired_resolution?: string;
  evidence?: string[];
  prior_steps?: string[];
  cpgrams_account_status?: "registered" | "not_registered" | "unknown";
}

export interface CPGRAMSClassification {
  domain: string;
  label: string;
  confidence: CivicConfidence;
  reason: string;
}

export interface CPGRAMSSuitability {
  is_suitable: boolean | null;
  exclusion_category?: string | null;
  reason: string;
  alternative_path?: string | null;
  requires_verification: boolean;
}

export interface CPGRAMSAuthority {
  authority_type: string;
  candidate: string;
  confidence: CivicConfidence;
  reason: string;
  status?: string;
  requires_verification: boolean;
  authority_hint?: string | null;
  authority_hint_status?: string | null;
  provenance?: CivicProvenance;
}

export interface CPGRAMSDraft {
  subject: string;
  facts: string[];
  relief_requested: string[];
  evidence: string[];
  formatted_text: string;
}

export interface CPGRAMSFilingGuide {
  portal_url?: string | null;
  status_url?: string | null;
  steps: string[];
  tracking: string[];
  fee_note?: string;
  email_note?: string;
  human_actions_required: string[];
  provenance?: CivicProvenance[];
}

export type CPGRAMSHandoffState =
  | "DRAFT"
  | "PREPARED"
  | "REVIEWED"
  | "CONFIRMATION_REQUIRED"
  | "HANDOFF";

export interface CPGRAMSPrepareResponse {
  status: string;
  classification: CPGRAMSClassification;
  suitability: CPGRAMSSuitability;
  authority: CPGRAMSAuthority;
  missing_information: string[];
  jurisdiction_completeness: JurisdictionCompleteness;
  draft?: CPGRAMSDraft | null;
  filing_guide: CPGRAMSFilingGuide;
  sources: CivicProvenance[];
  disclaimer?: string;
  intent?: string | null;
  workflow?: string | null;
  domain?: string | null;
  handoff?: WorkflowHandoff | null;
  handoff_state: CPGRAMSHandoffState;
  handoff_blockers: string[];
  external_action_requires_confirmation: boolean;
}

export interface LegalDomainQueryRequest {
  query: string;
  domain?: "consumer" | "tenant" | "labour" | "civic" | "government" | string;
  state?: string;
  district?: string;
  city?: string;
  locality?: string;
  authority_hint?: string;
  jurisdiction?: string;
}

export interface LegalDomainSource extends CivicProvenance {
  title?: string;
  excerpt?: string;
  content?: string;
  text?: string;
  summary?: string;
  rule?: string;
  guidance?: string[];
  id?: string;
  score?: number;
  document_type?: string;
  domain?: string;
}

export interface LegalDomainQueryResponse extends CivicProvenance {
  query?: string;
  domain?: string | null;
  answer?: string;
  guidance?: string;
  confidence?: CivicConfidence | number;
  requires_verification?: boolean;
  missing_information?: string[];
  jurisdiction_completeness: JurisdictionCompleteness;
  next_steps: string[];
  evidence_checklist?: string[];
  sources?: LegalDomainSource[];
  results?: LegalDomainSource[];
  disclaimer?: string;
}

async function civicApiRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item?.msg ?? String(item)).join("; ")
      : typeof detail === "string"
        ? detail
        : `API error ${res.status}`;
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

function postCivic<T>(url: string, body: unknown): Promise<T> {
  return civicApiRequest<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── RTI ─────────────────────────────────────────────────────────────────────

export function identifyRTIDepartment(
  request: RTIIdentifyRequest
): Promise<RTIDepartmentResponse> {
  return postCivic("/api/rti/identify-department", request);
}

export function draftRTI(request: RTIDraftRequest): Promise<RTIDraftResponse> {
  return postCivic("/api/rti/draft", request);
}

export async function downloadRTI(
  request: RTIDraftRequest
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch("/api/rti/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof body.detail === "string" ? body.detail : `Download failed: ${res.status}`);
  }
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i);
  const filename = match ? decodeURIComponent(match[1].trim()) : "rti-application.txt";
  return { blob: await res.blob(), filename };
}

export function getRTIGuide(state?: string, authorityHint?: string): Promise<RTIGuideResponse> {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  if (authorityHint) params.set("authority_hint", authorityHint);
  const suffix = params.size ? `?${params.toString()}` : "";
  return civicApiRequest(`/api/rti/guide${suffix}`);
}

// ── Government schemes ──────────────────────────────────────────────────────

export async function listGovernmentSchemes(): Promise<SchemeSummary[]> {
  const response = await civicApiRequest<{ schemes: SchemeSummary[] }>("/api/schemes/list");
  return response.schemes;
}

export function getGovernmentScheme(schemeId: string): Promise<SchemeSummary> {
  return civicApiRequest(`/api/schemes/${encodeURIComponent(schemeId)}`);
}

export async function searchGovernmentSchemes(query: string): Promise<SchemeSummary[]> {
  const response = await civicApiRequest<{ schemes: SchemeSummary[] }>(`/api/schemes/search?q=${encodeURIComponent(query)}`);
  return response.schemes;
}

export function checkSchemeEligibility(
  request: SchemeEligibilityRequest
): Promise<SchemeGuidedResponse> {
  return postCivic("/api/schemes/check-eligibility", request);
}

export function guidedSchemeCheck(
  request: SchemeEligibilityRequest
): Promise<SchemeGuidedResponse> {
  return postCivic("/api/schemes/guided-check", request);
}

// ── CPGRAMS preparation ─────────────────────────────────────────────────────

export function prepareCPGRAMS(
  request: CPGRAMSPrepareRequest
): Promise<CPGRAMSPrepareResponse> {
  return postCivic("/api/cpgrams/prepare", request);
}

// ── Jurisdiction-aware civic/legal domains ──────────────────────────────────

export function queryLegalDomain(
  request: LegalDomainQueryRequest
): Promise<LegalDomainQueryResponse> {
  return postCivic("/api/legal/domains/query", request);
}
