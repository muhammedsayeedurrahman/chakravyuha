"""Smart legal router — thin adapter delegating to controllers/pipeline.

All business logic lives in the 8-layer pipeline controller.
This module defines API models and routes only.
"""

from __future__ import annotations

import base64
import logging

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from backend.controllers.pipeline import process_query, _classify, get_pipeline_cache
from backend.services.response_engine import get_response, get_all_scenarios
from backend.services.translator import (
    detect_language,
    translate_smart_response,
)
from backend.services.voice_service import get_voice_service

logger = logging.getLogger("chakravyuha")

router = APIRouter(prefix="/api", tags=["smart-legal"])


# ── Request / Response Models ────────────────────────────────────────────────

class SmartQueryRequest(BaseModel):
    query: str = Field(..., description="User's legal question")
    language: str = Field(default="en-IN")


class SmartResponse(BaseModel):
    scenario: str
    title: str
    guidance: str
    sections: list[str]
    outcome: str
    severity: str
    complaint_draft: str = ""
    helplines: list[str] = []
    source: str = "classifier"  # "classifier" or "rag_fallback"
    response_language: str = "en-IN"  # Language the response is in


class SmartVoiceResponse(BaseModel):
    transcript: str
    confidence: float
    language: str
    response: SmartResponse | None = None
    audio: str | None = None  # base64 TTS
    error: str | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/smart-query", response_model=SmartResponse)
async def smart_query(request: SmartQueryRequest) -> SmartResponse:
    """Classification-first legal query — delegates to 8-layer pipeline."""
    return await process_query(request.query, request.language)


@router.post("/smart-voice", response_model=SmartVoiceResponse)
async def smart_voice(
    audio: UploadFile = File(...),
    language: str = Form("hi-IN"),
) -> SmartVoiceResponse:
    """Voice pipeline: ASR -> pipeline -> TTS.

    ASR and TTS are voice-specific concerns that stay in the router.
    Classification + response generation delegates to the pipeline.
    """
    voice = get_voice_service()
    audio_bytes = await audio.read()

    if not audio_bytes or len(audio_bytes) < 200:
        return SmartVoiceResponse(
            transcript="",
            confidence=0.0,
            language=language,
            error="Audio too short or empty. Please speak louder or closer to the microphone.",
        )

    # Step 1: ASR (convert webm->wav for Sarvam compatibility)
    content_type = audio.content_type or "audio/webm"
    transcription = await voice.transcribe(audio_bytes, language, content_type=content_type)

    if not transcription.text or transcription.mode == "fallback":
        return SmartVoiceResponse(
            transcript="",
            confidence=transcription.confidence,
            language=transcription.language,
            error="Could not understand the audio. Please speak clearly or type your question.",
        )

    # Step 2+3: Pipeline handles classify + response + translate
    detected_lang = transcription.language or language
    smart_resp = await process_query(transcription.text, detected_lang)

    # Step 4: TTS (for non-English, synthesize the TRANSLATED guidance)
    audio_b64 = None
    if voice.is_available and detected_lang != "en-IN":
        tts_text = smart_resp.guidance[:200].replace("\n", "... ")
        tts_bytes = await voice.synthesize(tts_text, detected_lang)
        if tts_bytes:
            audio_b64 = base64.b64encode(tts_bytes).decode("utf-8")

    return SmartVoiceResponse(
        transcript=transcription.text,
        confidence=transcription.confidence,
        language=transcription.language,
        response=smart_resp,
        audio=audio_b64,
    )


@router.get("/scenarios")
async def list_scenarios() -> dict:
    """List all known legal scenarios for the frontend."""
    return {"scenarios": get_all_scenarios()}


@router.post("/judge")
async def ai_judge(request: SmartQueryRequest) -> dict:
    """AI Judge — predict outcome for a legal scenario."""
    detected_lang = detect_language(request.query, request.language)
    result, _ = await _classify(request.query, detected_lang)
    resp = get_response(result.scenario) if result.scenario not in ("unknown", "empty") else None

    if resp:
        return {
            "scenario": resp.scenario,
            "title": resp.title,
            "outcome": resp.outcome,
            "severity": resp.severity,
            "sections": resp.sections,
        }

    return {
        "scenario": "unknown",
        "title": "Cannot Predict",
        "outcome": "Please describe your situation more clearly for an outcome prediction.",
        "severity": "unknown",
        "sections": [],
    }


@router.post("/draft-complaint")
async def draft_complaint(request: SmartQueryRequest) -> dict:
    """Generate a complaint/FIR draft for a legal scenario."""
    detected_lang = detect_language(request.query, request.language)
    result, _ = await _classify(request.query, detected_lang)
    resp = get_response(result.scenario) if result.scenario not in ("unknown", "empty") else None

    if resp and resp.complaint_draft:
        return {
            "scenario": resp.scenario,
            "title": resp.title,
            "draft": resp.complaint_draft,
            "available": True,
        }

    return {
        "scenario": result.scenario,
        "title": "No Template Available",
        "draft": "No complaint template available for this scenario. "
                 "Please consult a lawyer for drafting legal documents.",
        "available": False,
    }


@router.get("/pipeline-health")
async def pipeline_health() -> dict:
    """Diagnostic endpoint — shows pipeline architecture for judges.

    No-hallucination design: LLM used ONLY for classification.
    Responses come from curated templates (26 scenarios) or local RAG.
    """
    # LLM provider info
    try:
        from backend.services.llm.router import get_llm_service
        llm = get_llm_service()
        active_provider = llm.provider
        available_providers = llm.available_providers
    except Exception:
        active_provider = "none"
        available_providers = []

    # Cache stats
    cache = get_pipeline_cache()
    cache_stats = cache.stats

    # Voice service (translation + ASR/TTS)
    try:
        voice = get_voice_service()
        translation_available = voice.is_available
    except Exception:
        translation_available = False

    return {
        "pipeline": "8-layer Chakravyuha",
        "layers": [
            {"L1": "Input Validation", "type": "local"},
            {"L2": "Language Detection", "type": "local", "detail": "script-based, no API"},
            {"L3": "Intent Classification", "type": "local+llm_fallback",
             "detail": "rules first → translate → LLM ONLY if rules fail"},
            {"L4": "Scenario Routing", "type": "local", "detail": "template | rag_fallback | escalation"},
            {"L5": "Knowledge Retrieval", "type": "local", "detail": "curated templates (26 scenarios) + local RAG"},
            {"L6": "Response Building", "type": "local", "detail": "template engine, zero LLM"},
            {"L7": "Translation", "type": "api", "detail": "Sarvam AI (skipped if offline)"},
            {"L8": "Cache + Return", "type": "local", "detail": f"LRU cache (max 500)"},
        ],
        "no_hallucination_design": {
            "llm_usage": "classification_only (1 call max per input)",
            "response_source": "curated_templates (26 legal scenarios)",
            "rag_source": "local ChromaDB keyword search with confidence gating (threshold: 0.6)",
            "free_generation": False,
        },
        "llm": {
            "active_provider": active_provider,
            "available_providers": available_providers,
            "role": "classification_only",
        },
        "cache": cache_stats,
        "translation": {"available": translation_available},
        "offline_capable": True,
        "scenarios_count": len(get_all_scenarios()),
    }
