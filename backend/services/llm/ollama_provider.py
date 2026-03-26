"""Ollama LLM provider — free, local or remote, fully offline capable."""

from __future__ import annotations

import logging

import httpx

from backend.config import get_settings
from backend.services.llm.base import BaseLLMProvider, build_messages

logger = logging.getLogger("chakravyuha")


class OllamaProvider(BaseLLMProvider):
    """Ollama via /api/chat endpoint (local or remote device)."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._available = False
        self._check_connection()

    def _check_connection(self) -> None:
        """Verify Ollama server is reachable."""
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                self._available = True
                logger.debug(
                    "Ollama connected at %s — models: %s",
                    self._base_url,
                    ", ".join(models) if models else "(none)",
                )
                base_names = [m.split(":")[0] for m in models]
                if models and self._model not in models and self._model not in base_names:
                    logger.warning(
                        "Model '%s' not on Ollama. Available: %s. Run: ollama pull %s",
                        self._model, ", ".join(models), self._model,
                    )
        except httpx.ConnectError:
            logger.debug("Ollama not reachable at %s", self._base_url)
        except Exception as e:
            logger.debug("Ollama check failed: %s", e)

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        return self._available

    def generate(self, query: str, sections: list[dict], language: str = "en-IN") -> str | None:
        if not self._available:
            return None

        messages = build_messages(query, sections, language)

        try:
            resp = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": get_settings().llm_temperature,
                        "num_predict": get_settings().llm_max_tokens,
                    },
                },
                timeout=120.0,
            )
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "")
            if content:
                logger.info("Ollama response: %d chars, model=%s", len(content), self._model)
                return content

            logger.warning("Ollama returned empty response")
            return None

        except httpx.TimeoutException:
            logger.error("Ollama timed out (120s) — model may be loading")
            return None
        except Exception as e:
            logger.error("Ollama generation failed: %s", e)
            return None
