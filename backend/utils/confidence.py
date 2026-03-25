"""Confidence scoring utilities for ASR and RAG outputs."""

from __future__ import annotations

from backend.config import get_settings


def classify_asr_confidence(score: float) -> str:
    """Classify ASR confidence into action tiers.

    Returns:
        "accept" — high confidence, use transcription as-is
        "confirm" — medium confidence, ask user to verify
        "fallback" — low confidence, switch to text input
    """
    settings = get_settings()
    if score >= settings.asr_accept_threshold:
        return "accept"
    if score >= settings.asr_confirm_threshold:
        return "confirm"
    return "fallback"


def classify_rag_confidence(score: float) -> str:
    """Classify RAG retrieval confidence.

    Returns:
        "high" — confident match, use directly
        "medium" — partial match, supplement with guided flow
        "low" — poor match, suggest guided flow instead
    """
    settings = get_settings()
    if score >= settings.rag_confidence_high:
        return "high"
    if score >= settings.rag_score_threshold:
        return "medium"
    return "low"
