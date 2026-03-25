"""Multi-provider LLM package for legal response generation."""

from backend.services.llm.router import LegalLLM, get_llm_service

__all__ = ["LegalLLM", "get_llm_service"]
