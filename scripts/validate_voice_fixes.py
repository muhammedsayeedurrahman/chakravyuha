#!/usr/bin/env python3
"""Validation script for ASR/TTS bug fixes.

Tests:
1. ASR method calling pattern (._transcribe_sarvam)
2. TTS method calling pattern (_synthesize_sarvam)
3. Error handling for both services
4. Cascade fallback logic
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from unittest.mock import MagicMock, patch

logging.basicConfig(level=logging.DEBUG)

def test_asr_sarvam_method_pattern():
    """Verify ASR calls client.speech_to_text.transcribe() correctly."""
    print("\n✓ Testing ASR Sarvam method calling pattern...")
    
    from backend.voice import asr
    
    with patch.dict("os.environ", {"SARVAM_API_KEY": "test-key"}):
        with patch("sarvamai.SarvamAI") as mock_sarvam:
            # Setup mock client with correct structure
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.transcript = "Namaste"
            mock_response.language_probability = 0.95
            mock_response.language_code = "hi"
            
            # This is the CORRECT way the SDK is called
            mock_client.speech_to_text.transcribe.return_value = mock_response
            mock_sarvam.return_value = mock_client
            
            # Test transcription
            result = asr._transcribe_sarvam(b"fake audio data", "hi")
            
            # Verify method was called correctly
            mock_client.speech_to_text.transcribe.assert_called_once()
            call_kwargs = mock_client.speech_to_text.transcribe.call_args[1]
            
            assert "file" in call_kwargs, "Missing 'file' parameter"
            assert "model" in call_kwargs, "Missing 'model' parameter"
            assert "language_code" in call_kwargs, "Missing 'language_code' parameter"
            
            assert result is not None, "Should return result dict"
            assert result["source"] == "sarvam", "Should have sarvam source"
            assert "confidence" in result, "Should have confidence in result"
            assert "text" in result, "Should have text in result"
            
            print("  ✅ ASR correctly calls client.speech_to_text.transcribe()")
            print(f"     Result: confidence={result['confidence']:.2f}, text='{result['text']}'")


def test_tts_sarvam_method_pattern():
    """Verify TTS calls client.text_to_speech.convert() correctly."""
    print("\n✓ Testing TTS Sarvam method calling pattern...")
    
    from backend.voice import tts
    
    with patch.dict("os.environ", {"SARVAM_API_KEY": "test-key"}):
        with patch("sarvamai.SarvamAI") as mock_sarvam:
            # Setup mock client with correct structure
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.audios = ["aGVsbG8gd29ybGQ="]  # base64 of "hello world"
            
            # This is the CORRECT way the SDK is called
            mock_client.text_to_speech.convert.return_value = mock_response
            mock_sarvam.return_value = mock_client
            
            # Test synthesis
            result = tts._synthesize_sarvam("Hello world", "hi-IN")
            
            # Verify method was called correctly
            mock_client.text_to_speech.convert.assert_called_once()
            call_kwargs = mock_client.text_to_speech.convert.call_args[1]
            
            assert "text" in call_kwargs, "Missing 'text' parameter"
            assert "target_language_code" in call_kwargs, "Missing 'target_language_code' parameter"
            assert "model" in call_kwargs, "Missing 'model' parameter"
            
            assert result is not None, "Should return audio bytes"
            assert isinstance(result, bytes), "Should return bytes"
            
            print("  ✅ TTS correctly calls client.text_to_speech.convert()")
            print(f"     Result: {len(result)} bytes of audio")


def test_asr_error_handling():
    """Verify ASR catches TypeError for incorrect API usage."""
    print("\n✓ Testing ASR error handling...")
    
    from backend.voice import asr
    
    with patch.dict("os.environ", {"SARVAM_API_KEY": "test-key"}):
        with patch("sarvamai.SarvamAI") as mock_sarvam:
            # Simulate the error: client(audio) instead of client.speech_to_text.transcribe(audio)
            mock_client = MagicMock()
            mock_client.speech_to_text.transcribe.side_effect = TypeError("'SpeechToTextClient' object is not callable")
            mock_sarvam.return_value = mock_client
            
            # Should gracefully return error dict
            result = asr._transcribe_sarvam(b"audio data", "hi")
            
            assert result is not None, "Should return dict with error"
            assert "error" in result, "Should include error key"
            assert result["text"] == "", "Should have empty text on error"
            assert result["confidence"] == 0.0, "Should have zero confidence on error"
            print("  ✅ ASR gracefully handles TypeError from API method")


def test_tts_error_handling():
    """Verify TTS catches TypeError for incorrect API usage."""
    print("\n✓ Testing TTS error handling...")
    
    from backend.voice import tts
    
    with patch.dict("os.environ", {"SARVAM_API_KEY": "test-key"}):
        with patch("sarvamai.SarvamAI") as mock_sarvam:
            # Simulate the error: client(text) instead of client.text_to_speech.convert(text=...)
            mock_client = MagicMock()
            mock_client.text_to_speech.convert.side_effect = TypeError("'TextToSpeechClient' object is not callable")
            mock_sarvam.return_value = mock_client
            
            # Should gracefully return None
            result = tts._synthesize_sarvam("Hello", "hi-IN")
            
            assert result is None, "Should return None on TypeError"
            print("  ✅ TTS gracefully handles TypeError from API method")


def test_cascade_fallback():
    """Verify cascade fallback works when primary fails."""
    print("\n✓ Testing cascade fallback...")
    
    from backend.voice import asr
    
    # Mock both layers
    with patch("backend.voice.asr._transcribe_sarvam") as mock_sarvam:
        with patch("backend.voice.asr._transcribe_indicwhisper") as mock_whisper:
            # Sarvam fails (low confidence), IndicWhisper succeeds
            mock_sarvam.return_value = {
                "text": "bad transcription",
                "confidence": 0.3,  # Below threshold
                "language": "hi",
                "source": "sarvam"
            }
            mock_whisper.return_value = {
                "text": "Namaste",
                "confidence": 0.82,
                "language": "hi",
                "source": "indicwhisper"
            }
            
            result = asr.transcribe(b"audio data", "hi", use_cascade=True)
            
            assert result is not None, "Should have result"
            assert result["text"] == "Namaste", "Should use IndicWhisper result"
            assert result["source"] == "indicwhisper", "Should mark source as indicwhisper"
            
            mock_whisper.assert_called_once()
            print("  ✅ ASR cascade fallback works correctly")


def test_empty_input_handling():
    """Verify both services handle empty input gracefully."""
    print("\n✓ Testing empty input handling...")
    
    from backend.voice import asr, tts
    
    # TTS with empty text (early return before API)
    result_tts = tts._synthesize_sarvam("", "hi-IN")
    assert result_tts is None, "Should return None for empty text"
    
    # TTS with whitespace-only text (early return before API)
    result_tts_ws = tts._synthesize_sarvam("   ", "hi-IN")
    assert result_tts_ws is None, "Should return None for whitespace-only text"
    
    # ASR empty input goes through API call (which is caught by exception handler)
    # It will fail with BadRequestError from API, but that's ok as it's handled
    with patch.dict("os.environ", {"SARVAM_API_KEY": "test-key"}):
        with patch("sarvamai.SarvamAI") as mock_sarvam:
            # Simulate empty audio causing API error
            mock_client = MagicMock()
            mock_client.speech_to_text.transcribe.side_effect = Exception("Empty or invalid audio")
            mock_sarvam.return_value = mock_client
            
            result_asr = asr._transcribe_sarvam(b"", "hi")
            assert result_asr is not None, "Should return error dict for invalid audio"
            assert result_asr["text"] == "", "Should have empty text on error"
            assert "error" in result_asr, "Should have error key"
    
    print("  ✅ Both services handle empty input correctly")


def test_response_format_variations():
    """Verify defensive response parsing handles API variations."""
    print("\n✓ Testing response format variations...")
    
    from backend.voice import asr, tts
    
    with patch.dict("os.environ", {"SARVAM_API_KEY": "test-key"}):
        # Test ASR with dict-like response (some SDK versions return dicts)
        with patch("sarvamai.SarvamAI") as mock_sarvam:
            mock_client = MagicMock()
            # Simulate SDK returning a dict instead of object
            mock_response = {
                "transcript": "Test",
                "language_probability": 0.9,
                "language_code": "hi"
            }
            mock_client.speech_to_text.transcribe.return_value = mock_response
            mock_sarvam.return_value = mock_client
            
            result = asr._transcribe_sarvam(b"audio", "hi")
            assert result is not None, "Should handle dict-like response"
            assert result["text"] == "Test", "Should extract transcript"
            print("  ✅ ASR handles dict-like response objects")
        
        # Test TTS with dict-like response (some SDK versions return dicts)
        with patch("sarvamai.SarvamAI") as mock_sarvam:
            mock_client = MagicMock()
            # Simulate SDK returning a dict instead of object
            mock_response = {
                "audios": ["aGVsbG8="]
            }
            mock_client.text_to_speech.convert.return_value = mock_response
            mock_sarvam.return_value = mock_client
            
            result = tts._synthesize_sarvam("Test", "hi-IN")
            assert result is not None, "Should handle dict-like response"
            print("  ✅ TTS handles dict-like response objects")


if __name__ == "__main__":
    print("=" * 60)
    print("CHAKRAVYUHA VOICE SERVICE VALIDATION")
    print("=" * 60)
    
    try:
        test_asr_sarvam_method_pattern()
        test_tts_sarvam_method_pattern()
        test_asr_error_handling()
        test_tts_error_handling()
        test_cascade_fallback()
        test_empty_input_handling()
        test_response_format_variations()
        
        print("\n" + "=" * 60)
        print("✅ ALL VALIDATION TESTS PASSED")
        print("=" * 60)
        print("\nKey Fixes Verified:")
        print("  1. ASR calls client.speech_to_text.transcribe() correctly")
        print("  2. TTS calls client.text_to_speech.convert() correctly")
        print("  3. TypeError handling for incorrect API usage")
        print("  4. Cascade fallback works when primary fails")
        print("  5. Empty input handled gracefully")
        print("  6. Defensive response parsing for SDK variations")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
