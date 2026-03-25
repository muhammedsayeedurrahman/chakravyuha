"""Unit tests for voice I/O (ASR + TTS) services."""

import pytest
from unittest.mock import patch, MagicMock
from backend.voice.asr import transcribe, _transcribe_sarvam, _transcribe_indicwhisper
from backend.voice.tts import synthesize, _synthesize_sarvam, _synthesize_piper


class TestASR:
    """Tests for speech-to-text transcription."""

    def test_transcribe_empty_audio(self):
        """Empty audio should return error response."""
        result = transcribe(b"")
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert result["status"] == "fallback"
        assert "Empty audio" in result.get("error", "")

    @patch("backend.voice.asr._transcribe_sarvam")
    def test_transcribe_cascade_fallback(self, mock_sarvam):
        """Low Sarvam confidence should trigger IndicWhisper fallback."""
        # Mock Sarvam to return low confidence
        mock_sarvam.return_value = {
            "text": "partial",
            "confidence": 0.5,
            "source": "sarvam",
        }

        with patch("backend.voice.asr._transcribe_indicwhisper") as mock_indicwhisper:
            mock_indicwhisper.return_value = {
                "text": "complete transcript",
                "confidence": 0.85,
                "source": "indicwhisper",
            }

            result = transcribe(b"audio_data", "hi", use_cascade=True)

            # Should use fallback result (IndicWhisper)
            assert result["text"] == "complete transcript"
            assert result["source"] == "indicwhisper"
            assert result["status"] == "accepted"  # conf >= 0.85

    @patch("backend.voice.asr._transcribe_sarvam")
    def test_transcribe_cascade_disabled(self, mock_sarvam):
        """With cascade disabled, should accept Sarvam result as-is."""
        mock_sarvam.return_value = {
            "text": "low confidence",
            "confidence": 0.6,
            "source": "sarvam",
        }

        result = transcribe(b"audio_data", "hi", use_cascade=False)

        assert result["source"] == "sarvam"
        assert result["text"] == "low confidence"
        # Status should be adjusted by confidence
        assert result["status"] in ["confirm", "fallback"]

    def test_transcribe_status_thresholds(self):
        """Test status classification based on confidence thresholds."""
        from backend.config import ASR_ACCEPT_THRESHOLD, ASR_CONFIRM_THRESHOLD

        with patch("backend.voice.asr._transcribe_sarvam") as mock_sarvam:
            # High confidence (>= ASR_ACCEPT_THRESHOLD)
            mock_sarvam.return_value = {
                "text": "hello",
                "confidence": ASR_ACCEPT_THRESHOLD + 0.01,
                "source": "sarvam",
            }
            result = transcribe(b"audio", use_cascade=False)
            assert result["status"] == "accepted"

            # Medium confidence
            mock_sarvam.return_value = {
                "text": "hello",
                "confidence": (ASR_ACCEPT_THRESHOLD + ASR_CONFIRM_THRESHOLD) / 2,
                "source": "sarvam",
            }
            result = transcribe(b"audio", use_cascade=False)
            assert result["status"] == "confirm"

            # Low confidence
            mock_sarvam.return_value = {
                "text": "hello",
                "confidence": ASR_CONFIRM_THRESHOLD - 0.01,
                "source": "sarvam",
            }
            result = transcribe(b"audio", use_cascade=False)
            assert result["status"] == "fallback"


class TestTTS:
    """Tests for text-to-speech synthesis."""

    def test_synthesize_empty_text(self):
        """Empty text should return None."""
        result = synthesize("")
        assert result is None

    def test_synthesize_whitespace_only(self):
        """Whitespace-only text should return None."""
        result = synthesize("   \n\t  ")
        assert result is None

    @patch("backend.voice.tts._synthesize_sarvam")
    def test_synthesize_sarvam_success(self, mock_sarvam):
        """Successful Sarvam synthesis should return audio bytes."""
        expected_audio = b"audio_data_wav"
        mock_sarvam.return_value = expected_audio

        result = synthesize("hello world", "hi-IN")

        assert result == expected_audio
        mock_sarvam.assert_called_once()

    @patch("backend.voice.tts._synthesize_sarvam")
    @patch("backend.voice.tts._synthesize_piper")
    def test_synthesize_cascade_to_piper(self, mock_piper, mock_sarvam):
        """Sarvam failure should cascade to Piper."""
        mock_sarvam.return_value = None
        expected_audio = b"piper_audio"
        mock_piper.return_value = expected_audio

        result = synthesize("hello", "hi-IN", use_cascade=True)

        assert result == expected_audio
        mock_piper.assert_called_once()

    @patch("backend.voice.tts._synthesize_sarvam")
    @patch("backend.voice.tts._synthesize_piper")
    @patch("backend.voice.tts._synthesize_espeak")
    def test_synthesize_full_cascade(self, mock_espeak, mock_piper, mock_sarvam):
        """Failed Sarvam + Piper should try eSpeak."""
        mock_sarvam.return_value = None
        mock_piper.return_value = None
        expected_audio = b"espeak_audio"
        mock_espeak.return_value = expected_audio

        result = synthesize("hello", "hi-IN", use_cascade=True)

        assert result == expected_audio
        mock_espeak.assert_called_once()

    @patch("backend.voice.tts._synthesize_sarvam")
    def test_synthesize_cascade_disabled(self, mock_sarvam):
        """With cascade disabled, should not try fallbacks."""
        mock_sarvam.return_value = None

        result = synthesize("hello", "hi-IN", use_cascade=False)

        assert result is None

    def test_synthesize_language_codes(self):
        """Should handle various language code formats."""
        with patch("backend.voice.tts._synthesize_sarvam") as mock_sarvam:
            mock_sarvam.return_value = b"audio"

            # Test various formats
            for lang in ["hi", "hi-IN", "ta", "te", "kn"]:
                result = synthesize("hello", lang, use_cascade=False)
                assert result == b"audio"


class TestVoiceIntegration:
    """Integration tests for ASR + TTS pipeline."""

    @patch("backend.voice.asr._transcribe_sarvam")
    @patch("backend.voice.tts._synthesize_sarvam")
    def test_voice_query_pipeline(self, mock_tts, mock_asr):
        """Test end-to-end voice query (transcribe → synthesize)."""
        # Mock ASR
        mock_asr.return_value = {
            "text": "I was hit",
            "confidence": 0.9,
            "source": "sarvam",
        }

        # Mock TTS
        mock_tts.return_value = b"response_audio"

        # Transcribe
        asr_result = transcribe(b"audio_input", "hi", use_cascade=False)
        assert asr_result["text"] == "I was hit"
        assert asr_result["status"] == "accepted"

        # Synthesize response
        response_text = "यह धारा 323 है"  # Hindi: "This is Section 323"
        tts_result = synthesize(response_text, "hi-IN", use_cascade=False)
        assert tts_result == b"response_audio"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
