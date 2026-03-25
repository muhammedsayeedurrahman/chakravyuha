"""Translator service — language detection and translation for the pipeline.

Extracted from routers/smart_legal.py for reuse across text + voice pipelines.
Uses Sarvam AI translate via VoiceService.
"""

from __future__ import annotations

import logging
import re

from backend.services.voice_service import get_voice_service

logger = logging.getLogger("chakravyuha")


# ── Script detection ─────────────────────────────────────────────────────────

# Regex to detect non-Latin scripts (Devanagari, Tamil, Telugu, Bengali, etc.)
_NON_LATIN_RE = re.compile(
    r"[\u0900-\u097F"   # Devanagari (Hindi, Marathi, Sanskrit)
    r"\u0980-\u09FF"    # Bengali
    r"\u0A00-\u0A7F"    # Gurmukhi (Punjabi)
    r"\u0A80-\u0AFF"    # Gujarati
    r"\u0B00-\u0B7F"    # Odia
    r"\u0B80-\u0BFF"    # Tamil
    r"\u0C00-\u0C7F"    # Telugu
    r"\u0C80-\u0CFF"    # Kannada
    r"\u0D00-\u0D7F]"   # Malayalam
)

# Map script Unicode ranges to Sarvam language codes
_SCRIPT_TO_LANG: list[tuple[int, int, str]] = [
    (0x0900, 0x097F, "hi-IN"),  # Devanagari -> Hindi
    (0x0980, 0x09FF, "bn-IN"),  # Bengali
    (0x0A00, 0x0A7F, "pa-IN"),  # Gurmukhi -> Punjabi
    (0x0A80, 0x0AFF, "gu-IN"),  # Gujarati
    (0x0B00, 0x0B7F, "od-IN"),  # Odia
    (0x0B80, 0x0BFF, "ta-IN"),  # Tamil
    (0x0C00, 0x0C7F, "te-IN"),  # Telugu
    (0x0C80, 0x0CFF, "kn-IN"),  # Kannada
    (0x0D00, 0x0D7F, "ml-IN"),  # Malayalam
]


def detect_indic_language(text: str) -> str | None:
    """Detect Indic language from script. Returns lang code or None if Latin."""
    for char in text:
        cp = ord(char)
        for start, end, lang in _SCRIPT_TO_LANG:
            if start <= cp <= end:
                return lang
    return None


def has_non_latin_script(text: str) -> bool:
    """Return True if the text contains non-Latin (Indic) script characters."""
    return bool(_NON_LATIN_RE.search(text))


def detect_language(text: str, declared_lang: str) -> str:
    """Detect actual language from script, overriding declared language if needed.

    Returns BCP-47 code (e.g. 'hi-IN', 'en-IN').
    """
    if declared_lang != "en-IN":
        return declared_lang

    if has_non_latin_script(text):
        detected = detect_indic_language(text)
        if detected:
            logger.info("Auto-detected Indic script: '%s' -> %s", text[:30], detected)
            return detected

    return "en-IN"


# ── Translation ──────────────────────────────────────────────────────────────

async def translate_to_english(text: str, source_lang: str) -> str:
    """Translate non-English text to English for classification.

    Returns original text if already English or translation fails.
    """
    if source_lang == "en-IN" or not text:
        return text

    voice = get_voice_service()
    if not voice.is_available:
        return text

    try:
        translated = await voice.translate(text, source_lang=source_lang, target_lang="en-IN")
        if translated and translated != text:
            logger.info("Translated [%s]: '%s' -> '%s'", source_lang, text[:50], translated[:50])
            return translated
    except Exception as e:
        logger.warning("Translation failed: %s", e)

    return text


async def _translate_text(voice: object, text: str, target_lang: str) -> str:
    """Translate a single string, returning original on failure."""
    if not text:
        return text
    try:
        result = await voice.translate(text, source_lang="en-IN", target_lang=target_lang)
        return result if result else text
    except Exception:
        return text


async def _translate_list(voice: object, items: list[str], target_lang: str) -> list[str]:
    """Translate a list of strings in sequence."""
    translated = []
    for item in items:
        translated.append(await _translate_text(voice, item, target_lang))
    return translated


async def translate_smart_response(
    response: object,
    target_lang: str,
) -> object:
    """Translate ALL user-facing fields of a SmartResponse to user's language.

    Translates: title, guidance, sections, outcome, helplines.
    Keeps English: scenario (internal ID), complaint_draft (legal template),
                   source (internal label), severity (internal label).

    Accepts and returns a SmartResponse (imported lazily to avoid circular imports).
    """
    if target_lang == "en-IN" or not target_lang:
        return response

    voice = get_voice_service()
    if not voice.is_available:
        return response

    try:
        translated_title = await _translate_text(voice, response.title, target_lang)
        translated_guidance = await _translate_text(voice, response.guidance, target_lang)
        translated_outcome = await _translate_text(voice, response.outcome, target_lang)
        translated_sections = await _translate_list(voice, response.sections, target_lang)
        translated_helplines = await _translate_list(voice, response.helplines, target_lang)

        # Import SmartResponse lazily to avoid circular imports
        from backend.routers.smart_legal import SmartResponse

        return SmartResponse(
            scenario=response.scenario,
            title=translated_title,
            guidance=translated_guidance,
            sections=translated_sections,
            outcome=translated_outcome,
            severity=response.severity,
            complaint_draft=response.complaint_draft,
            helplines=translated_helplines,
            source=response.source,
            response_language=target_lang,
        )
    except Exception as e:
        logger.warning("Response translation failed: %s", e)
        return response  # Graceful fallback to English
