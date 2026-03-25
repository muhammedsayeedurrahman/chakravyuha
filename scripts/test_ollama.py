"""Quick test script to verify Ollama LLM connection and legal response generation."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import get_settings


def test_connection():
    """Test basic Ollama server connectivity."""
    settings = get_settings()
    print(f"LLM Provider:  {settings.llm_provider}")
    print(f"LLM Model:     {settings.llm_model}")
    print(f"Ollama URL:    {settings.ollama_base_url}")
    print()

    import httpx

    url = settings.ollama_base_url.rstrip("/")

    # Test 1: Server reachable?
    print("[1/4] Checking Ollama server...")
    try:
        resp = httpx.get(f"{url}/api/tags", timeout=5.0)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        print(f"  OK — Server reachable. Models installed: {', '.join(models) or '(none)'}")
    except httpx.ConnectError:
        print(f"  FAIL — Cannot connect to {url}")
        print(f"  Fix: Start Ollama with: OLLAMA_HOST=0.0.0.0 ollama serve")
        return False
    except Exception as e:
        print(f"  FAIL — {e}")
        return False

    # Test 2: Model available?
    print(f"\n[2/4] Checking model '{settings.llm_model}'...")
    base_names = [m.split(":")[0] for m in models]
    if settings.llm_model in models or settings.llm_model in base_names:
        print(f"  OK — Model '{settings.llm_model}' is available")
    else:
        print(f"  FAIL — Model '{settings.llm_model}' not found")
        print(f"  Fix: Run on Ollama device: ollama pull {settings.llm_model}")
        return False

    # Test 3: Simple chat request
    print(f"\n[3/4] Testing basic chat request...")
    try:
        resp = httpx.post(
            f"{url}/api/chat",
            json={
                "model": settings.llm_model,
                "messages": [{"role": "user", "content": "Say 'hello' in Hindi"}],
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 50},
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")
        print(f"  OK — Response: {content[:100]}")
    except httpx.TimeoutException:
        print(f"  FAIL — Timed out (model may be loading, try again)")
        return False
    except Exception as e:
        print(f"  FAIL — {e}")
        return False

    # Test 4: Legal response via LegalLLM service
    print(f"\n[4/4] Testing legal response generation...")
    try:
        from backend.services.llm_service import get_llm_service

        llm = get_llm_service()
        print(f"  Provider: {llm.provider}, Available: {llm.is_available}")

        if not llm.is_available:
            print(f"  FAIL — LLM service not available")
            return False

        test_sections = [
            {
                "section_id": "BNS-303",
                "law": "BNS",
                "title": "Theft",
                "description": "Whoever, intending to take dishonestly any moveable property out of the possession of any person without that person's consent, moves that property in order to such taking, is said to commit theft.",
                "punishment": "Imprisonment up to 3 years, or fine, or both",
                "cognizable": True,
                "bailable": False,
                "score": 0.85,
            }
        ]

        response = llm.generate(
            query="Someone stole my phone from my pocket",
            sections=test_sections,
            language="en-IN",
        )

        if response:
            print(f"  OK — Legal response generated ({len(response)} chars)")
            print(f"\n{'='*60}")
            print("SAMPLE RESPONSE:")
            print(f"{'='*60}")
            print(response[:500])
            if len(response) > 500:
                print(f"\n... ({len(response) - 500} more chars)")
            print(f"{'='*60}")
            return True
        else:
            print(f"  FAIL — Empty response from LLM")
            return False

    except Exception as e:
        print(f"  FAIL — {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Chakravyuha — Ollama LLM Connection Test")
    print("=" * 60)
    print()

    success = test_connection()

    print()
    if success:
        print("ALL TESTS PASSED — Ollama is ready!")
    else:
        print("SOME TESTS FAILED — check the errors above")

    sys.exit(0 if success else 1)
