"""Mistral AI LLM provider — free tier, strong reasoning and multilingual."""

from __future__ import annotations

import logging

import httpx

from backend.config import get_settings
from backend.services.llm.base import BaseLLMProvider, build_messages

logger = logging.getLogger("chakravyuha")

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


class MistralProvider(BaseLLMProvider):
    """Mistral AI via REST API (OpenAI-compatible format)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.mistral_api_key
        self._model = settings.mistral_model
        self._available = bool(self._api_key)
        if self._available:
            logger.info("Mistral provider ready (model: %s)", self._model)
        else:
            logger.info("Mistral provider disabled — no MISTRAL_API_KEY")

    @property
    def name(self) -> str:
        return "mistral"

    @property
    def is_available(self) -> bool:
        return self._available

    def generate(self, query: str, sections: list[dict], language: str = "en-IN") -> str | None:
        if not self._available:
            return None

        messages = build_messages(query, sections, language)
        settings = get_settings()

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }

        try:
            resp = httpx.post(
                MISTRAL_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
            resp.raise_for_status()

            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    logger.info("Mistral response: %d chars", len(content))
                    return content

            logger.warning("Mistral returned empty response")
            return None

        except httpx.HTTPStatusError as e:
            logger.error("Mistral API error %d: %s", e.response.status_code, e.response.text[:200])
            return None
        except Exception as e:
            logger.error("Mistral generation failed: %s", e)
            return None
