"""Test script to verify multi-provider LLM architecture and legal response generation."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import get_settings

TEST_SECTIONS = [
    {
        "section_id": "BNS-303",
        "law": "BNS",
        "title": "Theft",
        "description": (
            "Whoever, intending to take dishonestly any moveable property "
            "out of the possession of any person without that person's consent, "
            "moves that property in order to such taking, is said to commit theft."
        ),
        "punishment": "Imprisonment up to 3 years, or fine, or both",
        "cognizable": True,
        "bailable": False,
        "score": 0.85,
    }
]


def test_providers():
    """Test all configured LLM providers."""
    settings = get_settings()

    print(f"LLM Enabled:   {settings.llm_enabled}")
    print(f"Priority:      {settings.llm_priority}")
    print(f"Temperature:   {settings.llm_temperature}")
    print(f"Max Tokens:    {settings.llm_max_tokens}")
    print()

    # Show provider config
    providers = {
        "gemini": {"key": bool(settings.gemini_api_key), "model": settings.gemini_model},
        "mistral": {"key": bool(settings.mistral_api_key), "model": settings.mistral_model},
        "openrouter": {"key": bool(settings.openrouter_api_key), "model": settings.openrouter_model},
        "ollama": {"key": "N/A", "model": settings.ollama_model, "url": settings.ollama_base_url},
        "sarvam": {"key": bool(settings.sarvam_api_key), "model": settings.sarvam_llm_model},
    }

    print("Provider Configuration:")
    for name, cfg in providers.items():
        key_status = "SET" if cfg["key"] is True else ("N/A" if cfg["key"] == "N/A" else "NOT SET")
        extra = f" @ {cfg.get('url', '')}" if "url" in cfg else ""
        print(f"  {name:12s} | key: {key_status:7s} | model: {cfg['model']}{extra}")

    print()

    # Initialize the LLM router
    print("=" * 60)
    print("Initializing LLM Router...")
    print("=" * 60)

    from backend.services.llm import get_llm_service

    llm = get_llm_service()

    print()
    print(f"Active provider:     {llm.provider}")
    print(f"Available providers: {', '.join(llm.available_providers) or '(none)'}")
    print(f"LLM available:       {llm.is_available}")
    print()

    if not llm.is_available:
        print("NO LLM PROVIDERS AVAILABLE")
        print()
        print("To fix, set at least one API key in .env:")
        print("  GEMINI_API_KEY=...     (free: https://aistudio.google.com/apikey)")
        print("  MISTRAL_API_KEY=...    (free: https://console.mistral.ai/api-keys)")
        print("  OPENROUTER_API_KEY=... (free: https://openrouter.ai/keys)")
        print("  Or install Ollama:      https://ollama.com/download")
        return False

    # Test generation
    print("=" * 60)
    print(f"Testing legal response via '{llm.provider}'...")
    print("=" * 60)
    print()
    print(f"Query: 'Someone stole my phone from my pocket'")
    print()

    response = llm.generate(
        query="Someone stole my phone from my pocket",
        sections=TEST_SECTIONS,
        language="en-IN",
    )

    if response:
        print(f"Response ({len(response)} chars):")
        print("-" * 60)
        print(response[:600])
        if len(response) > 600:
            print(f"\n... ({len(response) - 600} more chars)")
        print("-" * 60)
        return True
    else:
        print("FAIL — Empty response from LLM")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Chakravyuha — Multi-Provider LLM Test")
    print("=" * 60)
    print()

    success = test_providers()

    print()
    if success:
        print("LLM TEST PASSED")
    else:
        print("LLM TEST FAILED — check errors above")

    sys.exit(0 if success else 1)
