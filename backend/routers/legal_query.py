"""REST API routes for legal queries and voice endpoints.

DEPRECATED: These endpoints use the RAG-first pipeline. Prefer the
classification-first pipeline at /api/smart-query and /api/smart-voice
which provides deterministic, hallucination-free responses for known
legal scenarios. These endpoints remain fully functional for backwards
compatibility and as a fallback for complex queries.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from backend.legal.rag import LegalRAG, get_rag
from backend.voice.asr import transcribe as asr_transcribe
from backend.voice.tts import synthesize as tts_synthesize

logger = logging.getLogger("chakravyuha")

router = APIRouter(prefix="/api", tags=["legal (legacy — prefer /api/smart-query)"])


# ============================================================================
# Request/Response Models
# ============================================================================


class TextQueryRequest(BaseModel):
    """User query request."""

    query: str = Field(..., description="Legal question in natural language")
    language: str = Field(default="hi-IN", description="BCP-47 language code")


class TextQueryResponse(BaseModel):
    """Legal query response."""

    query: str
    sections: list[dict]
    confidence: str  # "high", "medium", "low", "none"
    message: str | None
    disclaimer: str


class VoiceQueryRequest(BaseModel):
    """Voice query request."""

    audio_base64: str = Field(..., description="Base64-encoded audio bytes")
    language: str = Field(default="hi-IN", description="BCP-47 language code")


class VoiceQueryResponse(BaseModel):
    """Voice query response."""

    transcript: str
    asr_confidence: float
    sections: list[dict]
    retrieval_confidence: str
    audio_response: str  # Base64-encoded audio


class SectionDetailsResponse(BaseModel):
    """Full details of a specific section."""

    section_id: str
    section_number: str
    title: str
    act: str
    court_type: str
    full_text: str
    tags: list[str]


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/query",
    response_model=TextQueryResponse,
    deprecated=True,
    summary="[Legacy] Query legal sections by text — use POST /api/smart-query instead",
)
async def legal_query(request: TextQueryRequest) -> TextQueryResponse:
    """Query legal sections by text.

    **Deprecated**: Use POST /api/smart-query for classification-first,
    hallucination-free responses. This endpoint remains functional.

    Example:
        POST /api/query
        {"query": "I was hit by someone", "language": "hi-IN"}

    Returns:
        Relevant legal sections with confidence score
    """
    rag = get_rag()

    if not rag.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Legal database not ready. Please try again later."
        )

    result = rag.retrieve_with_correction(request.query)

    from backend.config import DISCLAIMER

    return TextQueryResponse(
        query=request.query,
        sections=result["sections"],
        confidence=result["confidence"],
        message=result.get("message"),
        disclaimer=DISCLAIMER,
    )


@router.post("/voice/dictation")
async def voice_dictation(
    audio_file: UploadFile = File(...),
    language: str = "hi-IN",
) -> dict:
    """Transcribe voice audio to text.

    Audio format: WAV, MP3, or OGG (16-bit, mono preferred)
    
    Returns:
        {
            "text": "transcript",
            "confidence": 0.92,
            "language": "hi-IN",
            "status": "accepted"  # or "confirm" or "fallback"
        }
    """
    audio_bytes = await audio_file.read()

    result = asr_transcribe(audio_bytes, language)

    return {
        "text": result.get("text", ""),
        "confidence": result.get("confidence", 0.0),
        "language": result.get("language", language),
        "status": result.get("status", "fallback"),
        "source": result.get("source", "unknown"),
    }


@router.post(
    "/voice/query",
    response_model=VoiceQueryResponse,
    deprecated=True,
    summary="[Legacy] Voice query — use POST /api/smart-voice instead",
)
async def voice_legal_query(request: VoiceQueryRequest) -> VoiceQueryResponse:
    """Full voice query: transcribe → retrieve → speak.

    **Deprecated**: Use POST /api/smart-voice for classification-first pipeline.
    This endpoint remains functional.

    Args:
        request.audio_base64: Base64-encoded audio
        request.language: Target language

    Returns:
        Transcript, retrieved sections, and audio response
    """
    import base64

    # Decode audio
    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio: {e}")

    # Transcribe
    asr_result = asr_transcribe(audio_bytes, request.language)

    if not asr_result.get("text"):
        raise HTTPException(
            status_code=400,
            detail=f"ASR failed: {asr_result.get('error', 'Unknown error')}"
        )

    # Retrieve sections
    rag = get_rag()
    retrieval_result = rag.retrieve_with_correction(asr_result["text"])

    # Format response
    response_text = rag.generate_response(
        asr_result["text"],
        retrieval_result["sections"],
        request.language
    )

    # Synthesize speech
    audio_response_bytes = tts_synthesize(
        response_text,
        request.language,
    )

    audio_response_b64 = ""
    if audio_response_bytes:
        audio_response_b64 = base64.b64encode(audio_response_bytes).decode("utf-8")

    return VoiceQueryResponse(
        transcript=asr_result["text"],
        asr_confidence=asr_result.get("confidence", 0.0),
        sections=retrieval_result["sections"],
        retrieval_confidence=retrieval_result["confidence"],
        audio_response=audio_response_b64,
    )


@router.get("/sections/{section_id}", response_model=SectionDetailsResponse)
async def get_section_details(section_id: str) -> SectionDetailsResponse:
    """Get full details of a specific section.

    Example:
        GET /api/sections/IPC-152

    Returns:
        Full section text, punishment, and related information
    """
    rag = get_rag()

    if not rag.is_ready:
        raise HTTPException(status_code=503, detail="Legal database not ready")

    # This requires extending RAG with a get_section method
    # For now, just search for the section
    results = rag.retrieve_sections(section_id, top_k=1)

    if not results:
        raise HTTPException(status_code=404, detail=f"Section {section_id} not found")

    section = results[0]
    return SectionDetailsResponse(
        section_id=section_id,
        section_number=section.get("section_id", ""),
        title=section["title"],
        act=section.get("law", ""),
        court_type=section.get("cognizable", "Court"),
        full_text=section["description"],
        tags=section.get("tags", []),
    )


@router.get("/health", tags=["system"])
async def health_check() -> dict:
    """System health check."""
    rag = get_rag()
    return {
        "status": "healthy",
        "rag_ready": rag.is_ready,
        "rag_sections": rag._collection.count() if rag.is_ready else 0,
    }
