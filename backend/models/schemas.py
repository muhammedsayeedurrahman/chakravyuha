"""Pydantic schemas for Chakravyuha API — all models are immutable (frozen)."""

from __future__ import annotations

from pydantic import BaseModel, Field


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


class GuidedFlowState(BaseModel):
    """Client-maintained state for guided flow traversal."""

    current_node: str = "root"
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
