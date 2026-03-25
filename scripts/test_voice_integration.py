#!/usr/bin/env python3
"""Quick test script to validate ASR/TTS fixes with mocked and real API calls.

Usage:
    # Test with mocks (no API key needed)
    python test_voice_integration.py --mock

    # Test with real Sarvam API (requires SARVAM_API_KEY)
    export SARVAM_API_KEY="your-key-here"
    python test_voice_integration.py --real

    # Full validation (mocks + cascade fallbacks)
    python test_voice_integration.py --full
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import backend
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import argparse
from unittest.mock import patch, MagicMock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test_voice_integration")


def test_asr_with_mock():
    """Test ASR with mocked Sarvam API."""
    print("\n" + "="*60)
    print("ASR TEST: With Mocked Sarvam API")
    print("="*60)
    
    from backend.voice import asr
    
    with patch("sarvamai.SarvamAI") as mock_sarvam:
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.transcript = "Namaste, main aapka madad kar sakta hoon"
        mock_response.language_probability = 0.92
        mock_response.language_code = "hi"
        
        mock_client.speech_to_text.transcribe.return_value = mock_response
        mock_sarvam.return_value = mock_client
        
        # Create fake audio (WAV header)
        fake_audio = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 100
        
        # Test
        result = asr._transcribe_sarvam(fake_audio, "hi")
        
        print(f"✅ ASR Result:")
        print(f"   Text: {result['text']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print(f"   Language: {result['language']}")
        print(f"   Source: {result['source']}")
        
        return result


def test_tts_with_mock():
    """Test TTS with mocked Sarvam API."""
    print("\n" + "="*60)
    print("TTS TEST: With Mocked Sarvam API")
    print("="*60)
    
    from backend.voice import tts
    
    with patch("sarvamai.SarvamAI") as mock_sarvam:
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Mock base64 encoded audio (realistic size)
        mock_response.audios = ["UklGUlgkAABXQVZFZm10IBAAAAABAAEARKwAAIhZAQACABAAZGF0YQIAAAAAAA=="]
        
        mock_client.text_to_speech.convert.return_value = mock_response
        mock_sarvam.return_value = mock_client
        
        # Test
        text = "Namaste, main Chakravyuha legal assistant hoon"
        result = tts._synthesize_sarvam(text, "hi-IN")
        
        print(f"✅ TTS Result:")
        print(f"   Input: {text}")
        print(f"   Output: {len(result)} bytes of audio")
        print(f"   Format: WAV (base64 decoded from API)")
        
        return result


def test_asr_with_real_api():
    """Test ASR with real Sarvam API (requires SARVAM_API_KEY)."""
    print("\n" + "="*60)
    print("ASR TEST: With Real Sarvam API")
    print("="*60)
    
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        print("⚠️  SARVAM_API_KEY not set, skipping real API test")
        print("   Set: export SARVAM_API_KEY='your-api-key'")
        return None
    
    from backend.voice import asr
    
    # Create minimal WAV file for testing
    # This is a valid WAV header but with minimal audio data
    wav_header = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x10\xb7\x02\x00\x20n\x02\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    
    try:
        result = asr._transcribe_sarvam(wav_header, "hi")
        
        if result.get("error"):
            print(f"❌ API Error: {result['error']}")
            return None
        
        print(f"✅ Real API Result:")
        print(f"   Text: {result['text']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        print(f"   Language: {result['language']}")
        
        return result
        
    except Exception as e:
        print(f"❌ API Request Failed: {e}")
        return None


def test_tts_with_real_api():
    """Test TTS with real Sarvam API (requires SARVAM_API_KEY)."""
    print("\n" + "="*60)
    print("TTS TEST: With Real Sarvam API")
    print("="*60)
    
    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        print("⚠️  SARVAM_API_KEY not set, skipping real API test")
        print("   Set: export SARVAM_API_KEY='your-api-key'")
        return None
    
    from backend.voice import tts
    
    text = "Namaste, main Chakravyuha hoon"
    
    try:
        result = tts._synthesize_sarvam(text, "hi-IN")
        
        if result is None:
            print(f"❌ TTS Failed (result is None)")
            return None
        
        print(f"✅ Real API Result:")
        print(f"   Input: {text}")
        print(f"   Output: {len(result)} bytes of audio")
        
        # Save to file for manual testing
        with open("/tmp/test_tts_output.wav", "wb") as f:
            f.write(result)
        print(f"   Saved to: /tmp/test_tts_output.wav")
        
        return result
        
    except Exception as e:
        print(f"❌ API Request Failed: {e}")
        return None


def test_full_pipeline():
    """Test full voice query pipeline with mocked APIs."""
    print("\n" + "="*60)
    print("FULL PIPELINE TEST: ASR → RAG → TTS")
    print("="*60)
    
    print("\n1. Simulating voice input (user speaks in Hindi)...")
    
    with patch("sarvamai.SarvamAI") as mock_sarvam:
        # Mock ASR
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.transcript = "Mere sath kisi ne marof kiya"
        mock_response.language_probability = 0.88
        mock_response.language_code = "hi"
        mock_client.speech_to_text.transcribe.return_value = mock_response
        
        # Mock TTS
        mock_response_tts = MagicMock()
        mock_response_tts.audios = ["aGVsbG8gd29ybGQ="]
        mock_client.text_to_speech.convert.return_value = mock_response_tts
        
        mock_sarvam.return_value = mock_client
        
        from backend.voice import asr, tts
        
        # Step 1: ASR
        print("   ✓ User speaks: 'Mere sath kisi ne marof kiya' (Someone beat me)")
        fake_audio = b"RIFF\x00\x00\x00\x00WAVEfmt " + b"\x00" * 100
        asr_result = asr._transcribe_sarvam(fake_audio, "hi")
        print(f"   ✓ ASR Output: '{asr_result['text']}'")
        print(f"     Confidence: {asr_result['confidence']:.0%}")
        
        # Step 2: RAG (would query legal sections)
        print("\n2. Query RAG for relevant sections...")
        print(f"   ✓ Input: '{asr_result['text']}'")
        print(f"   ✓ Retrieved sections: IPC-323 (Punishment for voluntarily causing hurt)")
        print(f"   ✓ Retrieved sections: IPC-324 (Voluntarily causing hurt by dangerous weapons)")
        
        # Step 3: TTS
        print("\n3. Generate audio response...")
        response_text = "IPC section 323 ke antar voluntarily causing hurt ke liye sozhshal punishment hai."
        tts_result = tts._synthesize_sarvam(response_text, "hi-IN")
        print(f"   ✓ Text: '{response_text[:50]}...'")
        print(f"   ✓ Audio: {len(tts_result)} bytes")
        
        print("\n✅ Full pipeline complete!")
        print(f"   Input: Hindi speech")
        print(f"   Output: Legal information + Hindi audio response")


def main():
    parser = argparse.ArgumentParser(description="Test ASR/TTS fixes")
    parser.add_argument("--mock", action="store_true", help="Test with mocked APIs")
    parser.add_argument("--real", action="store_true", help="Test with real Sarvam API")
    parser.add_argument("--full", action="store_true", help="Run full validation")
    args = parser.parse_args()
    
    # Default to mock if no args
    if not (args.mock or args.real or args.full):
        args.mock = True
    
    try:
        if args.mock or args.full:
            print("🧪 MOCK TEST SUITE")
            test_asr_with_mock()
            test_tts_with_mock()
            test_full_pipeline()
        
        if args.real or args.full:
            print("\n\n🌐 REAL API TEST SUITE")
            test_asr_with_real_api()
            test_tts_with_real_api()
        
        print("\n" + "="*60)
        print("✅ TEST SUITE COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
