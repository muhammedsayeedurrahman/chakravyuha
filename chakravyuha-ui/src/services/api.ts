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
