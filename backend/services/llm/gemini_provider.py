"""Google Gemini LLM provider — free tier, excellent Indian language support."""

from __future__ import annotations

import logging

import httpx

from backend.config import get_settings
from backend.services.llm.base import BaseLLMProvider, build_messages

logger = logging.getLogger("chakravyuha")

# Gemini API endpoint (v1beta for free tier)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(BaseLLMProvider):
    """Google Gemini via REST API (no SDK needed)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model
        self._available = bool(self._api_key)
        if self._available:
            logger.debug("Gemini provider ready (model: %s)", self._model)
        else:
            logger.debug("Gemini provider disabled — no GEMINI_API_KEY")

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return self._available

    def generate(self, query: str, sections: list[dict], language: str = "en-IN") -> str | None:
        if not self._available:
            return None

        messages = build_messages(query, sections, language)

        # Gemini uses a different format: system instruction + contents
        system_text = messages[0]["content"]
        user_text = messages[1]["content"]

        payload = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {
                "temperature": get_settings().llm_temperature,
                "maxOutputTokens": get_settings().llm_max_tokens,
            },
        }

        try:
            url = f"{GEMINI_API_URL}/{self._model}:generateContent?key={self._api_key}"
            resp = httpx.post(url, json=payload, timeout=60.0)
            resp.raise_for_status()

            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if content:
                    logger.info("Gemini response: %d chars", len(content))
                    return content

            logger.warning("Gemini returned empty response")
            return None

        except httpx.HTTPStatusError as e:
            logger.error("Gemini API error %d: %s", e.response.status_code, e.response.text[:200])
            return None
        except Exception as e:
            logger.error("Gemini generation failed: %s", e)
            return None
