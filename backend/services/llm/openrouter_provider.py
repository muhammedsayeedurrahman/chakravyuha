"""OpenRouter LLM provider — access Qwen, Llama, and other models via single API."""

from __future__ import annotations

import logging

import httpx

from backend.config import get_settings
from backend.services.llm.base import BaseLLMProvider, build_messages

logger = logging.getLogger("chakravyuha")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter — unified API for Qwen, Llama, DeepSeek, etc."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model
        self._available = bool(self._api_key)
        if self._available:
            logger.info("OpenRouter provider ready (model: %s)", self._model)
        else:
            logger.info("OpenRouter provider disabled — no OPENROUTER_API_KEY")

    @property
    def name(self) -> str:
        return "openrouter"

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
                OPENROUTER_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/chakravyuha",
                    "X-Title": "Chakravyuha Legal AI",
                },
                timeout=60.0,
            )
            resp.raise_for_status()

            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    logger.info("OpenRouter response: %d chars (model: %s)", len(content), self._model)
                    return content

            logger.warning("OpenRouter returned empty response")
            return None

        except httpx.HTTPStatusError as e:
            logger.error("OpenRouter API error %d: %s", e.response.status_code, e.response.text[:200])
            return None
        except Exception as e:
            logger.error("OpenRouter generation failed: %s", e)
            return None
