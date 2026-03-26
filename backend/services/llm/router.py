"""LLM Router — tries providers in priority order with auto-fallback.

Two priority chains:
- Q&A (generate): Cloud-first for speed and broad knowledge.
    Default: mistral → gemini → openrouter → ollama → sarvam
- Document generation (generate_raw): Ollama-first for privacy + no refusals.
    Default: ollama → mistral → gemini → openrouter → sarvam

Legal complaints contain PII (names, addresses, phone numbers). Preferring
Ollama for document generation keeps sensitive data on the local network,
avoids cloud content filtering that may refuse legal drafting, and is free.
"""

from __future__ import annotations

import logging

from functools import lru_cache

from backend.config import get_settings
from backend.services.llm.base import BaseLLMProvider

logger = logging.getLogger("chakravyuha")

# Provider priority order (first available wins)
DEFAULT_PRIORITY = ["gemini", "mistral", "openrouter", "ollama", "sarvam"]

# Document generation prefers local/private (Ollama) for PII safety
DEFAULT_DOC_GEN_PRIORITY = ["ollama", "mistral", "gemini", "openrouter", "sarvam"]


def _create_provider(name: str) -> BaseLLMProvider | None:
    """Lazily import and create a provider by name."""
    try:
        if name == "gemini":
            from backend.services.llm.gemini_provider import GeminiProvider
            return GeminiProvider()
        elif name == "mistral":
            from backend.services.llm.mistral_provider import MistralProvider
            return MistralProvider()
        elif name == "openrouter":
            from backend.services.llm.openrouter_provider import OpenRouterProvider
            return OpenRouterProvider()
        elif name == "ollama":
            from backend.services.llm.ollama_provider import OllamaProvider
            return OllamaProvider()
        elif name == "sarvam":
            from backend.services.llm.sarvam_provider import SarvamProvider
            return SarvamProvider()
        else:
            logger.warning("Unknown LLM provider: %s", name)
            return None
    except Exception as e:
        logger.warning("Failed to create provider '%s': %s", name, e)
        return None


class LegalLLM:
    """Unified LLM interface — routes to providers in priority order.

    Tries each provider in the configured priority list. On failure,
    falls through to the next provider. If all fail, returns None
    (caller falls back to template-based response).
    """

    def __init__(self) -> None:
        settings = get_settings()
        priority = settings.llm_priority.split(",") if settings.llm_priority else DEFAULT_PRIORITY
        priority = [p.strip() for p in priority]

        self._providers: list[BaseLLMProvider] = []
        self._providers_by_name: dict[str, BaseLLMProvider] = {}
        self._active_provider: BaseLLMProvider | None = None

        logger.debug("LLM Q&A priority: %s", " -> ".join(priority))

        for name in priority:
            provider = _create_provider(name)
            if provider and provider.is_available:
                self._providers.append(provider)
                self._providers_by_name[provider.name] = provider
                logger.debug("  [OK] %s — available", provider.name)
            else:
                logger.debug("  [--] %s — unavailable", name)

        if self._providers:
            self._active_provider = self._providers[0]
            logger.info("LLM ready: primary=%s, available=%s",
                        self._active_provider.name,
                        ", ".join(p.name for p in self._providers))
        else:
            logger.warning("No LLM providers available — will use template fallback")

        # Build document-generation priority (Ollama first for PII privacy)
        self._doc_gen_providers = self._build_doc_gen_chain()

    def _build_doc_gen_chain(self) -> list[BaseLLMProvider]:
        """Build Ollama-first provider chain for document generation.

        Uses DOC_GEN_LLM_PRIORITY from config (defaults to ollama-first).
        Rationale: legal complaints contain PII → prefer local processing.
        """
        settings = get_settings()
        doc_priority = settings.doc_gen_llm_priority.split(",")
        doc_priority = [p.strip() for p in doc_priority]

        chain = []
        for name in doc_priority:
            provider = self._providers_by_name.get(name)
            if provider:
                chain.append(provider)
        if chain:
            logger.debug(
                "Doc-gen priority (PII-safe): %s",
                " -> ".join(p.name for p in chain),
            )
        return chain

    @property
    def is_available(self) -> bool:
        return len(self._providers) > 0

    @property
    def provider(self) -> str:
        """Name of the currently active (primary) provider."""
        return self._active_provider.name if self._active_provider else "none"

    @property
    def available_providers(self) -> list[str]:
        """Names of all available providers in priority order."""
        return [p.name for p in self._providers]

    def generate(
        self, query: str, sections: list[dict], language: str = "en-IN"
    ) -> str | None:
        """Generate a legal response, trying providers in priority order.

        Args:
            query: User's legal question.
            sections: Retrieved legal sections from RAG.
            language: User's language code (e.g., 'hi-IN').

        Returns:
            LLM-generated response, or None if all providers fail.
        """
        for provider in self._providers:
            try:
                result = provider.generate(query, sections, language)
                if result:
                    return result
                logger.info("Provider '%s' returned empty, trying next...", provider.name)
            except Exception as e:
                logger.warning("Provider '%s' failed: %s, trying next...", provider.name, e)

        logger.warning("All LLM providers failed — falling back to template")
        return None

    def generate_raw(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
    ) -> str | None:
        """Send custom system+user prompts directly (bypasses Q&A template).

        Uses Ollama-first priority for document generation:
        - PII stays on local network (legal complaints have names, addresses)
        - No cloud content filtering (never refuses legal drafting)
        - Free, no rate limits
        - Falls back to cloud providers if Ollama is unavailable

        Args:
            system_prompt: Custom system-level instruction.
            user_prompt: The user-facing prompt content.
            max_tokens: Override max tokens for longer outputs.

        Returns:
            Raw LLM response text, or None if all providers fail.
        """
        # Use doc-gen chain (Ollama-first) with fallback to main chain
        providers = self._doc_gen_providers or self._providers

        for provider in providers:
            try:
                if not provider.is_available:
                    continue

                result = _call_provider_raw(
                    provider, system_prompt, user_prompt,
                    temperature=0.15,  # Lower temp for deterministic legal documents
                    max_tokens=max_tokens,
                )
                if result:
                    logger.info(
                        "generate_raw via '%s': %d chars (doc-gen chain)",
                        provider.name, len(result),
                    )
                    return result
                logger.info("Provider '%s' returned empty for raw, trying next...", provider.name)
            except Exception as e:
                logger.warning("Provider '%s' raw failed: %s, trying next...", provider.name, e)

        logger.warning("All LLM providers failed for raw generation")
        return None


def _call_provider_raw(
    provider: BaseLLMProvider,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str | None:
    """Dispatch raw prompt to a specific provider type."""
    import httpx

    name = provider.name

    if name == "gemini":
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{provider._model}:generateContent?key={provider._api_key}"
        )
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        resp = httpx.post(url, json=payload, timeout=90.0)
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if candidates:
            return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

    elif name == "mistral":
        url = "https://api.mistral.ai/v1/chat/completions"
        payload = {
            "model": provider._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {provider._api_key}"},
            timeout=90.0,
        )
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")

    elif name == "openrouter":
        payload = {
            "model": provider._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {provider._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/lexaro",
                "X-Title": "Lexaro Legal AI",
            },
            timeout=90.0,
        )
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")

    elif name == "ollama":
        payload = {
            "model": provider._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        resp = httpx.post(
            f"{provider._base_url}/api/chat",
            json=payload,
            timeout=120.0,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")

    return None


# Thread-safe singleton via lru_cache
@lru_cache(maxsize=1)
def get_llm_service() -> LegalLLM:
    """Get or create the LegalLLM singleton (thread-safe)."""
    return LegalLLM()
