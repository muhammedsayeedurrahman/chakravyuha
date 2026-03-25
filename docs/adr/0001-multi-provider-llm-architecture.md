# ADR-0001: Multi-Provider LLM Architecture with Auto-Fallback

**Date**: 2026-03-24
**Status**: accepted
**Deciders**: Project team

## Context

Chakravyuha needs LLM-powered response generation to explain Indian legal sections in plain language. The original implementation used template-based responses (static string formatting). For a hackathon demo and beyond, we need intelligent, contextual explanations grounded in retrieved RAG sections.

Constraints:
- Must work with free-tier APIs (hackathon budget = $0)
- Must support Indian languages (Hindi, Tamil, Bengali, etc.)
- Must degrade gracefully if any provider is unavailable
- Should work offline (Ollama) or online (cloud APIs)
- 7 GB RAM on dev machine limits local model size

## Decision

We use a **multi-provider LLM architecture** with a priority-based fallback chain:

```
Gemini (free) → Mistral (free) → Qwen/OpenRouter → Ollama (local) → Sarvam → Template fallback
```

Each provider implements a common `BaseLLMProvider` interface. The `LegalLLM` router tries providers in configured priority order and falls through on failure.

## Alternatives Considered

### Alternative 1: Single Provider (Sarvam only)
- **Pros**: Simple, one SDK, good Indian language support
- **Cons**: Single point of failure, API limits, no offline mode
- **Why not**: Too fragile for demo day; if Sarvam is down, the entire LLM feature breaks

### Alternative 2: OpenAI-compatible proxy (LiteLLM)
- **Pros**: One interface for all providers, mature library
- **Cons**: Extra dependency (600+ MB), complex config, overkill for 4-5 providers
- **Why not**: Adds unnecessary weight; our provider abstraction is ~30 lines per backend

### Alternative 3: Ollama only (local)
- **Pros**: Free, private, no API keys needed
- **Cons**: Needs 4-8 GB RAM, slow on CPU-only machines, no cloud fallback
- **Why not**: Dev machine has 7 GB RAM — tight for llama3.1; need cloud fallback

## Consequences

### Positive
- Zero-cost LLM responses via free-tier APIs
- Automatic failover — demo never breaks due to one provider being down
- Supports both online (Gemini, Mistral) and offline (Ollama) usage
- Easy to add new providers (implement ~30 lines)

### Negative
- Multiple API keys to manage
- Response quality varies between providers
- More code to maintain (one module per provider)

### Risks
- Free-tier rate limits during high-traffic demo (mitigation: fallback chain)
- Provider API changes (mitigation: each provider is isolated, easy to fix independently)
