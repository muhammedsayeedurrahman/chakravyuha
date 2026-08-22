"""Pydantic schemas for Chakravyuha API — all models are immutable (frozen)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Legal Section Models ─────────────────────────────────────────────────────

class LegalSection(BaseModel):
    """A single BNS or IPC section."""
    model_config = {"frozen": True}

    section_id: str
    title: str
    act: str
    chapter: str = ""
    description: str
    punishment: str = ""
    cognizable: bool = False
    bailable: bool = True
    court: str = ""
    replaces_ipc: str | None = None
    replaced_by_bns: str | None = None
    keywords: list[str] = Field(default_factory=list)
    domain: str = "criminal"
    jurisdiction: str = "India"
    source: str | None = None
    source_url: str | None = None
    effective_date: str | None = None
    last_verified: str | None = None
    document_type: str = "section_summary"
    status: str = "requires_verification"


# ── Query Models ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Free-text legal query."""
    model_config = {"frozen": True}

    text: str
    language: str = "en-IN"
    top_k: int = 5


class SectionResult(BaseModel):
    """A single section result with relevance score."""
    model_config = {"frozen": True}

    section: LegalSection
    score: float = 0.0
    confidence: str = "medium"


class QueryResponse(BaseModel):
    """Response to a legal query."""
    model_config = {"frozen": True}

    query: str
    sections: list[SectionResult] = Field(default_factory=list)
    summary: str = ""
    disclaimer: str = ""
    confidence: str = "medium"


# ── Voice Models ─────────────────────────────────────────────────────────────

class VoiceRequest(BaseModel):
    """Voice input for ASR processing."""
    language: str = "hi-IN"


class TranscriptionResult(BaseModel):
    """ASR transcription result."""
    model_config = {"frozen": True}

    text: str
    language: str
    confidence: float = 0.0
    mode: str = "accept"  # accept/confirm/fallback


class VoiceResponse(BaseModel):
    """Combined voice pipeline response."""
    model_config = {"frozen": True}

    transcription: TranscriptionResult | None = None
    legal_response: QueryResponse | None = None
    audio_url: str | None = None


# ── Guided Flow Models ───────────────────────────────────────────────────────

class GuidedOption(BaseModel):
    """A single option in guided flow."""
    model_config = {"frozen": True}

    label: str
    label_hi: str = ""
    next: str | None = None  # next node key, None if leaf
    sections: list[str] = Field(default_factory=list)
    severity: str | None = None


class GuidedFlowStep(BaseModel):
    """Current step in guided flow."""
    model_config = {"frozen": True}

    node_key: str
    question: str
    question_hi: str = ""
    options: list[GuidedOption] = Field(default_factory=list)
    is_leaf: bool = False
    matched_sections: list[LegalSection] = Field(default_factory=list)
    severity: str | None = None
    type: str | None = None
    prompt: str | None = None
    prompt_hi: str | None = None
    handler: str | None = None
    journey: str | None = None
    summary: str | None = None
    summary_hi: str | None = None
    next_steps: list[str] = Field(default_factory=list)


class GuidedFlowState(BaseModel):
    """Client-maintained state for guided flow traversal."""

    current_node: str = "start"
    path: list[str] = Field(default_factory=list)
    selected_answer: str = ""


# ── Case Tracker Models ──────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    """Single event in case timeline."""
    model_config = {"frozen": True}

    timestamp: str
    event: str
    details: str = ""


class CaseRecord(BaseModel):
    """A tracked legal case."""

    case_id: str = ""
    title: str
    description: str
    sections: list[str] = Field(default_factory=list)
    severity: str = "LOW"
    status: str = "open"
    timeline: list[TimelineEvent] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


# ── Escalation Models ────────────────────────────────────────────────────────

class EscalationInfo(BaseModel):
    """Escalation routing information."""
    model_config = {"frozen": True}

    severity: str  # HIGH, MEDIUM, LOW
    should_escalate: bool = False
    contacts: list[dict[str, str]] = Field(default_factory=list)
    message: str = ""


# ── Form Agent Models ────────────────────────────────────────────────────────

class FormRequest(BaseModel):
    """Request to start form filling."""

    portal: str  # e.g., "parivahan", "efiling"
    user_data: dict = Field(default_factory=dict)


class FormResponse(BaseModel):
    """Form filling progress response."""
    model_config = {"frozen": True}

    portal: str
    status: str  # "started", "in_progress", "otp_required", "completed", "error"
    current_step: str = ""
    steps_completed: list[str] = Field(default_factory=list)
    message: str = ""


# ── API Envelope ─────────────────────────────────────────────────────────────

class ApiResponse(BaseModel):
    """Standard API response envelope."""
    model_config = {"frozen": True}

    success: bool = True
    data: dict | list | None = None
    error: str | None = None
    disclaimer: str = ""


# -- Civic-assistant shared models ---------------------------------------------

class ConfidenceLevel(str, Enum):
    """Citizen-facing confidence labels used by civic workflows."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    REQUIRES_JURISDICTION = "requires_jurisdiction"


class KnowledgeStatus(str, Enum):
    """Verification state for a legal or government-information record."""

    VERIFIED = "verified"
    REQUIRES_VERIFICATION = "requires_verification"
    REQUIRES_JURISDICTION = "requires_jurisdiction"
    UNAVAILABLE = "unavailable"


class Provenance(BaseModel):
    """Primary-source metadata carried through civic responses."""

    model_config = {"frozen": True}

    source: str
    source_url: str
    source_type: str = "official_government"
    jurisdiction: str = "India"
    effective_date: str | None = None
    last_verified: str
    status: KnowledgeStatus = KnowledgeStatus.VERIFIED


# -- RTI ----------------------------------------------------------------------

class RTIIdentifyRequest(BaseModel):
    """Plain-language issue and optional jurisdiction used for RTI routing."""

    issue: str = Field(..., min_length=10, max_length=5000)
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    locality: str | None = Field(default=None, max_length=200)
    authority_hint: str | None = Field(default=None, max_length=300)
    road_type: str | None = Field(default=None, max_length=100)
    date_range: str | None = Field(default=None, max_length=200)


class RTIRoutingResult(BaseModel):
    """Uncertain authority routing; never represents a verified PIO identity."""

    model_config = {"frozen": True}

    domain: str
    likely_authority: str
    authority_type: str
    confidence: ConfidenceLevel
    reason: str
    missing_information: list[str] = Field(default_factory=list)
    status: KnowledgeStatus
    source: str
    source_url: str | None = None


class RTIDraftRequest(RTIIdentifyRequest):
    """RTI draft request, including citizen-reviewed information requests."""

    applicant_name: str | None = Field(default=None, max_length=200)
    applicant_address: str | None = Field(default=None, max_length=1000)
    applicant_contact: str | None = Field(default=None, max_length=200)
    is_indian_citizen: bool | None = None
    information_requests: list[str] = Field(default_factory=list, max_length=20)


class RTIFilingGuidance(BaseModel):
    """Jurisdiction-qualified filing and appeal guidance."""

    model_config = {"frozen": True}

    pathway: str
    steps: list[str]
    next_step: str
    warnings: list[str] = Field(default_factory=list)
    sources: list[Provenance] = Field(default_factory=list)


class RTIDraftResponse(BaseModel):
    """End-to-end RTI preparation result."""

    model_config = {"frozen": True}

    status: str
    routing: RTIRoutingResult
    information_requests: list[str]
    missing_information: list[str] = Field(default_factory=list)
    document_text: str
    download_filename: str
    filing_guidance: RTIFilingGuidance
    disclaimer: str


# -- Government schemes -------------------------------------------------------

class CitizenProfile(BaseModel):
    """Known profile fields; extra scheme-specific answers remain supported."""

    model_config = ConfigDict(extra="allow")

    age: int | None = Field(default=None, ge=0, le=120)
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    occupation: str | None = Field(default=None, max_length=200)
    monthly_income: float | None = Field(default=None, ge=0)
    annual_income: float | None = Field(default=None, ge=0)
    is_indian_citizen: bool | None = None
    is_unorganised_worker: bool | None = None
    income_tax_payer: bool | None = None
    is_income_tax_payer: bool | None = None
    is_or_has_been_income_tax_payer: bool | None = None
    has_savings_bank_account: bool | None = None
    has_savings_account: bool | None = None
    covered_epfo: bool | None = None
    covered_esic: bool | None = None
    covered_nps: bool | None = None
    covered_by_epfo: bool | None = None
    covered_by_esic: bool | None = None
    covered_by_nps: bool | None = None
    already_has_apy_account: bool | None = None
    is_landholding_farmer_family: bool | None = None
    owns_cultivable_land: bool | None = None
    pm_kisan_exclusion_category: bool | None = None


class SchemeEligibilityRequest(BaseModel):
    """Evaluate selected schemes, or all candidates when no IDs are supplied."""

    scheme_ids: list[str] = Field(default_factory=list, max_length=20)
    scheme_id: str | None = Field(default=None, max_length=100)
    profile: CitizenProfile = Field(default_factory=CitizenProfile)
    max_questions: int = Field(default=3, ge=0, le=10)


class EligibilityCondition(BaseModel):
    """One deterministic eligibility explanation."""

    model_config = {"frozen": True}

    rule_id: str
    description: str
    field: str
    outcome: str = "unknown"
    observed_value: Any = None
    explanation: str = ""
    source_url: str | None = None
    reason: str | None = None
    question: str | None = None


class SchemeEligibilityResult(BaseModel):
    """Explainable eligibility result without a fabricated percentage."""

    model_config = {"frozen": True}

    scheme_id: str
    scheme_name: str
    short_name: str = ""
    status: str
    matched_conditions: list[EligibilityCondition] = Field(default_factory=list)
    unknown_conditions: list[EligibilityCondition] = Field(default_factory=list)
    potential_disqualifiers: list[EligibilityCondition] = Field(default_factory=list)
    why: str
    required_documents: list[str] = Field(default_factory=list)
    application_process: list[str] = Field(default_factory=list)
    official_portal_url: str | None = None
    helpline: str | None = None
    contact_guidance: str | None = None
    jurisdiction: dict[str, Any] = Field(default_factory=dict)
    next_questions: list[dict[str, Any]] = Field(default_factory=list)
    record_status: str = "requires_verification"
    verification_note: str | None = None
    evaluation_warnings: list[str] = Field(default_factory=list)
    disclaimer: str = ""
    provenance: Provenance


class SchemeGuidedCheckResponse(BaseModel):
    """Eligibility results plus only the next unanswered questions."""

    model_config = {"frozen": True}

    results: list[SchemeEligibilityResult]
    next_questions: list[dict[str, Any]] = Field(default_factory=list)
    complete: bool = False


# -- CPGRAMS grievance preparation --------------------------------------------

class CPGRAMSPrepareRequest(BaseModel):
    """Prepare, but never submit, a CPGRAMS grievance."""

    grievance: str = Field(..., min_length=10, max_length=10000)
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    locality: str | None = Field(default=None, max_length=200)
    organisation_hint: str | None = Field(default=None, max_length=300)
    incident_date: str | None = Field(default=None, max_length=100)
    prior_reference: str | None = Field(default=None, max_length=200)
    desired_resolution: str | None = Field(default=None, max_length=1000)
    evidence: list[str] = Field(default_factory=list, max_length=30)
    prior_steps: list[str] = Field(default_factory=list, max_length=30)
    cpgrams_account_status: str = Field(
        default="unknown",
        pattern="^(unknown|registered|not_registered)$",
    )


class CPGRAMSClassification(BaseModel):
    """Explainable broad grievance classification."""

    model_config = {"frozen": True}

    domain: str
    label: str
    confidence: ConfidenceLevel
    reason: str


class CPGRAMSSuitability(BaseModel):
    """Whether official CPGRAMS exclusions appear to apply."""

    model_config = {"frozen": True}

    is_suitable: bool
    exclusion_category: str | None = None
    reason: str
    alternative_path: str | None = None
    requires_verification: bool = True


class CPGRAMSAuthorityCandidate(BaseModel):
    """Generic, review-required public-authority candidate."""

    model_config = {"frozen": True}

    authority_type: str
    candidate: str
    confidence: ConfidenceLevel
    reason: str
    status: KnowledgeStatus = KnowledgeStatus.REQUIRES_VERIFICATION
    requires_verification: bool = True
    authority_hint: str | None = None
    authority_hint_status: str | None = None
    provenance: Provenance


class CPGRAMSDraft(BaseModel):
    """Structured grievance ready for citizen review."""

    model_config = {"frozen": True}

    subject: str
    facts: list[str]
    relief_requested: list[str]
    evidence: list[str]
    formatted_text: str


class CPGRAMSFilingGuide(BaseModel):
    """Official-source filing and tracking orientation."""

    model_config = {"frozen": True}

    portal_url: str
    status_url: str
    steps: list[str]
    tracking: list[str]
    fee_note: str
    email_note: str
    human_actions_required: list[str]
    provenance: list[Provenance]


class CPGRAMSPrepareResponse(BaseModel):
    """Classification, routing, draft, and safe filing next steps."""

    model_config = {"frozen": True}

    status: str
    classification: CPGRAMSClassification
    suitability: CPGRAMSSuitability
    authority: CPGRAMSAuthorityCandidate
    missing_information: list[str]
    draft: CPGRAMSDraft | None = None
    filing_guide: CPGRAMSFilingGuide
    sources: list[Provenance]
    external_action_requires_confirmation: bool = True
    disclaimer: str


# -- Provenance-aware civic/legal retrieval -----------------------------------

class CivicLegalQueryRequest(BaseModel):
    """Query consumer, tenant, or labour records with optional jurisdiction."""

    query: str = Field(..., min_length=3, max_length=5000)
    domain: str | None = Field(default=None, pattern="^(consumer|tenant|labour)?$")
    jurisdiction: str | None = Field(default=None, max_length=100)
    top_k: int = Field(default=5, ge=1, le=10)


class CivicKnowledgeRecord(BaseModel):
    """One retrieved civic/legal record with source metadata."""

    model_config = {"frozen": True}

    id: str
    domain: str
    title: str
    summary: str
    guidance: list[str] = Field(default_factory=list)
    jurisdiction: str
    source: str
    source_url: str
    effective_date: str | None = None
    last_verified: str
    source_type: str
    document_type: str
    status: KnowledgeStatus
    score: float = 0.0


class CivicLegalQueryResponse(BaseModel):
    """Domain-separated civic retrieval response."""

    model_config = {"frozen": True}

    query: str
    domain: str | None = None
    jurisdiction: str | None = None
    confidence: ConfidenceLevel
    status: KnowledgeStatus
    results: list[CivicKnowledgeRecord]
    missing_information: list[str] = Field(default_factory=list)
    answer: str
    disclaimer: str
