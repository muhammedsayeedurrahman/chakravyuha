"""Sarvam AI LLM provider — Indian language specialist, cloud API."""

from __future__ import annotations

import logging

from backend.config import get_settings
from backend.services.llm.base import BaseLLMProvider, build_messages

logger = logging.getLogger("chakravyuha")


class SarvamProvider(BaseLLMProvider):
    """Sarvam AI Chat Completion API."""

    def __init__(self) -> None:
        self._client = None
        self._available = False
        settings = get_settings()
        if not settings.sarvam_api_key:
            logger.debug("Sarvam LLM provider disabled — no SARVAM_API_KEY")
            return
        try:
            from sarvamai import SarvamAI

            self._client = SarvamAI(api_subscription_key=settings.sarvam_api_key)
            self._available = True
            logger.debug("Sarvam LLM provider ready (model: %s)", settings.sarvam_llm_model)
        except ImportError:
            logger.debug("Sarvam provider disabled — sarvamai not installed")
        except Exception as e:
            logger.info("Sarvam init failed: %s", e)

    @property
    def name(self) -> str:
        return "sarvam"

    @property
    def is_available(self) -> bool:
        return self._available

    def generate(self, query: str, sections: list[dict], language: str = "en-IN") -> str | None:
        if not self._available:
            return None

        settings = get_settings()
        messages = build_messages(query, sections, language)

        try:
            response = self._client.chat.completions(
                messages=messages,
                model=settings.sarvam_llm_model,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

            if hasattr(response, "choices") and response.choices:
                content = response.choices[0].message.content
                if content:
                    logger.info("Sarvam response: %d chars", len(content))
                    return content

            logger.warning("Sarvam returned empty response")
            return None

        except Exception as e:
            logger.error("Sarvam generation failed: %s", e)
            return None
