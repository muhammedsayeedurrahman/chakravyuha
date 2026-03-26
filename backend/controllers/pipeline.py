"""8-Layer pipeline controller — the ONE orchestrator for smart legal queries.

Flow:
  L1 Validate → L2 Detect Language → L3 Classify → L4 Route →
  L5 Retrieve → L6 Build Response → L7 Translate → L8 Cache + Return

Cache check happens early (between L2 and L3) to skip expensive layers.
All existing services are reused — this module only orchestrates the flow.
"""

from __future__ import annotations

import logging

from backend.agent.escalation import check_escalation_needed
from backend.services.cache import PipelineCache
from backend.services.classifier import (
    ClassifyResult,
    classify,
    llm_classify,
    safety_check,
)
from backend.services.response_engine import LegalResponse, get_response
from backend.services.translator import (
    detect_language,
    translate_smart_response,
    translate_to_english,
)

logger = logging.getLogger("chakravyuha")

# Module-level cache instance (thread-safe)
_cache = PipelineCache(maxsize=500)

# Minimum RAG score to trust results (below this, return guided fallback)
_RAG_CONFIDENCE_THRESHOLD = 0.6


# ── Layer 1: Input Validation ────────────────────────────────────────────────

def _validate_input(text: str) -> str:
    """Clean and validate input. Raises ValueError on empty."""
    if not text or not text.strip():
        raise ValueError("empty_input")
    import re
    import unicodedata
    clean = unicodedata.normalize("NFC", text.strip())
    clean = re.sub(r"\s+", " ", clean)
    return clean


# ── Layer 3: Intent Classification ───────────────────────────────────────────

async def _classify(text: str, detected_lang: str) -> tuple[ClassifyResult, str]:
    """Rule-based -> translate -> LLM fallback classification.

    Returns (ClassifyResult, english_text) so downstream layers can use
    the translated text for fallbacks.
    """
    # Fast path: try English rule-based classification first
    result = classify(text)
    if result.scenario not in ("unknown", "empty"):
        return result, text

    # If non-English, translate to English and retry rules
    english_text = text
    if detected_lang != "en-IN":
        english_text = await translate_to_english(text, source_lang=detected_lang)
        if english_text != text:
            result = classify(english_text)
            if result.scenario not in ("unknown", "empty"):
                logger.info("Classified after translation: '%s' -> %s", english_text[:50], result.scenario)
                return result, english_text

    # LLM semantic classifier (last resort)
    # Pass both original Indic text + English translation for disambiguation
    if result.scenario == "unknown":
        original_for_llm = text if detected_lang != "en-IN" else None
        llm_result = await llm_classify(english_text, original_text=original_for_llm)
        if llm_result.scenario != "unknown":
            return llm_result, english_text

    return result, english_text


# ── Layer 4: Scenario Routing ────────────────────────────────────────────────

def _route(result: ClassifyResult, query_text: str) -> str:
    """Route to response strategy: 'template' | 'rag_fallback' | 'escalation'.

    Escalation is prepended as urgency; the response still comes from
    template or RAG, but severity is elevated.
    """
    if check_escalation_needed(query_text):
        return "escalation"

    if result.scenario not in ("unknown", "empty"):
        return "template"

    return "rag_fallback"


# ── Layer 5: Knowledge Retrieval ─────────────────────────────────────────────

def _retrieve(
    english_text: str,
    route: str,
    scenario: str,
    original_query: str,
) -> dict:
    """Get response from templates or RAG fallback.

    Returns a dict with response data. For 'template' route, uses the
    curated response engine. For 'rag_fallback', tries keyword search
    with confidence gating.
    """
    # Import SmartResponse lazily to avoid circular imports at module level
    from backend.routers.smart_legal import SmartResponse

    if route in ("template", "escalation"):
        resp = get_response(scenario)
        if resp:
            # Safety check: ensure response is appropriate for the scenario
            smart_resp = _legal_to_smart(resp)
            if not safety_check(smart_resp.guidance, scenario):
                logger.warning("Safety filter triggered for scenario=%s, using fallback", scenario)
                return {"response": _rag_fallback(original_query, english_text), "route": "rag_fallback"}
            return {"response": smart_resp, "route": route}

    # RAG fallback with confidence gating
    return {"response": _rag_fallback(original_query, english_text), "route": "rag_fallback"}


def _legal_to_smart(resp: LegalResponse) -> object:
    """Convert LegalResponse dataclass to SmartResponse Pydantic model."""
    from backend.routers.smart_legal import SmartResponse

    return SmartResponse(
        scenario=resp.scenario,
        title=resp.title,
        guidance=resp.guidance,
        sections=resp.sections,
        outcome=resp.outcome,
        severity=resp.severity,
        complaint_draft=resp.complaint_draft,
        helplines=resp.helplines,
        source="classifier",
    )


def _rag_fallback(query: str, english_query: str | None = None) -> object:
    """Keyword search fallback with confidence gating.

    If RAG score < threshold, return a guided fallback instead of
    low-quality results.
    """
    from backend.routers.smart_legal import SmartResponse

    search_text = english_query or query
    try:
        from backend.services.legal_service import get_legal_service
        service = get_legal_service()
        results = service.keyword_search(search_text, top_k=3)

        if results:
            # Confidence gating: check if top result meets threshold
            top_score = results[0].score if results else 0.0
            if top_score < _RAG_CONFIDENCE_THRESHOLD and top_score > 0:
                logger.info("RAG score %.2f below threshold %.2f, using guided fallback",
                            top_score, _RAG_CONFIDENCE_THRESHOLD)
                return _guided_fallback()

            section_refs = []
            law_lines = []
            top_sec = results[0].section
            for r in results:
                sec = r.section
                section_refs.append(f"{sec.section_id} — {sec.title} ({sec.act})")
                punishment = sec.punishment if sec.punishment else "Not specified"
                law_lines.append(f"{sec.section_id} ({sec.act}): {sec.title} — Punishment: {punishment}")

            # Determine bail/cognizable from top result
            bail = "Bailable" if getattr(top_sec, "bailable", False) else "Non-bailable"
            cog = "Cognizable" if getattr(top_sec, "cognizable", False) else "Non-cognizable"

            # Structured guidance (Status / What to do / Law)
            actions = []
            if cog == "Cognizable":
                actions.append("File an FIR at the nearest police station.")
            else:
                actions.append("File a complaint with a magistrate.")
            actions.append("Contact NALSA (15100) for free legal aid.")

            guidance = (
                f"**Status**: {top_sec.title} ({cog}, {bail})\n\n"
                f"**What to do**: {' '.join(actions)}\n\n"
                f"**Law**: {'; '.join(law_lines)}"
            )

            return SmartResponse(
                scenario="rag_result",
                title="Legal Sections Found",
                guidance=guidance,
                sections=section_refs,
                outcome="Please consult a qualified lawyer for specific legal advice on your situation.",
                severity="medium",
                source="rag_fallback",
            )
    except Exception as e:
        logger.error("RAG fallback failed: %s", e)

    return _guided_fallback()


def _guided_fallback() -> object:
    """Return a helpful fallback response when no match is found.

    Includes category selection so the user can self-route to the
    correct legal domain. Categories trigger re-classification on the
    frontend (VoiceCard / ChatModal send a specific query).
    """
    from backend.routers.smart_legal import SmartResponse

    return SmartResponse(
        scenario="unknown",
        title="I Will Help You",
        guidance=(
            "I will help you. Please choose your issue:\n\n"
            "**Categories**: Theft, Assault, Fraud, Property, Family, Consumer, Employment, Emergency\n\n"
            "Select the category that best matches your situation, "
            "or describe your problem in more detail."
        ),
        sections=[],
        outcome="Select a category below for immediate legal guidance.",
        severity="low",
        helplines=["15100 (NALSA)", "112 (Emergency)"],
        source="rag_fallback",
    )


# ── Layer 6: Response Building ───────────────────────────────────────────────

def _build_response(retrieval: dict) -> object:
    """Finalize the response, adding escalation info if needed."""
    response = retrieval["response"]
    route = retrieval["route"]

    if route == "escalation" and response.severity not in ("critical",):
        # Elevate severity for escalation-routed queries
        from backend.routers.smart_legal import SmartResponse
        response = SmartResponse(
            scenario=response.scenario,
            title=response.title,
            guidance=response.guidance,
            sections=response.sections,
            outcome=response.outcome,
            severity="critical",
            complaint_draft=response.complaint_draft,
            helplines=response.helplines or ["112 (Emergency)", "15100 (NALSA)"],
            source=response.source,
            response_language=response.response_language,
        )

    return response


# ── Main Pipeline ────────────────────────────────────────────────────────────

async def process_query(query: str, language: str = "en-IN") -> object:
    """The ONE controller — 8-layer pipeline.

    L1: Validate input
    L2: Detect language from script
    L8 (early): Cache check
    L3: Classify (rules -> translate -> LLM)
    L4: Route to response strategy
    L5: Retrieve knowledge
    L6: Build response
    L7: Translate to user's language
    L8: Cache + return
    """
    from backend.routers.smart_legal import SmartResponse

    # L1: Validate
    try:
        clean_text = _validate_input(query)
    except ValueError:
        return SmartResponse(
            scenario="empty",
            title="No Input",
            guidance="Please type or speak your legal question.",
            sections=[],
            outcome="",
            severity="low",
        )

    # L2: Language detection
    detected_lang = detect_language(clean_text, language)

    # L8 (early): Cache check — skip L3-L7 on hit
    cached = _cache.get(clean_text, detected_lang)
    if cached:
        return cached

    # L3: Classify (rules -> translate -> LLM)
    result, english_text = await _classify(clean_text, detected_lang)
    logger.info(
        "Pipeline: '%s' [%s] -> scenario=%s confidence=%.2f method=%s",
        clean_text[:50], detected_lang, result.scenario, result.confidence, result.method,
    )

    # L4: Route
    route = _route(result, clean_text)

    # L5: Retrieve knowledge
    retrieval = _retrieve(english_text, route, result.scenario, clean_text)

    # L6: Build response
    smart_resp = _build_response(retrieval)

    # L7: Translate to user's language
    if detected_lang != "en-IN":
        smart_resp = await translate_smart_response(smart_resp, detected_lang)

    # L8: Cache + return
    _cache.put(clean_text, detected_lang, smart_resp)
    return smart_resp


def get_pipeline_cache() -> PipelineCache:
    """Expose pipeline cache for diagnostics / testing."""
    return _cache
