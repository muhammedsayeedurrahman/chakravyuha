"""Voice service — Sarvam AI ASR + TTS with confidence-based fallback."""

from __future__ import annotations

import base64
import io
import logging

from backend.config import SUPPORTED_LANGUAGES, get_settings
from backend.models.schemas import TranscriptionResult
from backend.utils.confidence import classify_asr_confidence

logger = logging.getLogger("chakravyuha")


def _convert_to_wav(audio_bytes: bytes, source_format: str = "webm") -> bytes:
    """Convert audio bytes (webm/ogg/mp3) to WAV using pydub + ffmpeg."""
    try:
        import imageio_ffmpeg
        from pydub import AudioSegment

        # Point pydub to the bundled ffmpeg binary
        AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=source_format)
        # Sarvam ASR: mono 16kHz 16-bit WAV works best
        audio = audio.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        wav_bytes = buf.getvalue()
        logger.info("Converted %s -> wav: %d -> %d bytes", source_format, len(audio_bytes), len(wav_bytes))
        return wav_bytes
    except Exception as e:
        logger.warning("Audio conversion failed (%s): %s — sending raw bytes", source_format, e)
        return audio_bytes


class VoiceService:
    """ASR and TTS via Sarvam AI SDK with graceful degradation."""

    def __init__(self) -> None:
        self._client = None
        self._available = False
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Sarvam AI client if API key is available."""
        settings = get_settings()
        if not settings.sarvam_api_key:
            logger.warning("Sarvam API key not set — voice features disabled")
            return
        try:
            from sarvamai import SarvamAI
            self._client = SarvamAI(api_subscription_key=settings.sarvam_api_key)
            self._available = True
            logger.info("Sarvam AI client initialized")
        except ImportError:
            logger.warning("sarvamai package not installed — voice features disabled")
        except Exception as e:
            logger.warning("Sarvam AI init failed: %s", e)

    @property
    def is_available(self) -> bool:
        """Check if voice features are available."""
        return self._available

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        content_type: str = "audio/wav",
    ) -> TranscriptionResult:
        """Transcribe audio to text using Sarvam ASR.

        Retries once on empty/fallback result. Returns TranscriptionResult with
        confidence-based mode:
        - accept: high confidence, use as-is
        - confirm: medium confidence, ask user to verify
        - fallback: low confidence, switch to text input
        """
        if not self._available:
            return TranscriptionResult(
                text="",
                language=language or "en-IN",
                confidence=0.0,
                mode="fallback",
            )

        max_attempts = 2
        last_result = TranscriptionResult(
            text="", language=language or "hi-IN", confidence=0.0, mode="fallback",
        )

        for attempt in range(1, max_attempts + 1):
            try:
                result = self._transcribe_once(audio_bytes, language, content_type)
                if result.text and result.mode != "fallback":
                    return result
                last_result = result
                if attempt < max_attempts:
                    logger.info("ASR attempt %d returned empty/fallback, retrying...", attempt)
            except Exception as e:
                logger.error("ASR attempt %d failed: %s", attempt, e)
                if attempt < max_attempts:
                    logger.info("Retrying ASR...")

        return last_result

    def _transcribe_once(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        content_type: str = "audio/wav",
    ) -> TranscriptionResult:
        """Single ASR attempt (synchronous Sarvam call)."""
        # Sarvam ASR expects language code
        lang_code = language or "hi-IN"
        if lang_code not in SUPPORTED_LANGUAGES:
            lang_code = "hi-IN"

        # Convert non-WAV formats to WAV for Sarvam compatibility
        wav_bytes = audio_bytes
        if content_type and "wav" not in content_type:
            fmt = "webm" if "webm" in content_type else "ogg" if "ogg" in content_type else "mp3"
            wav_bytes = _convert_to_wav(audio_bytes, source_format=fmt)

        # Call Sarvam speech_to_text
        response = self._client.speech_to_text.transcribe(
            file=("audio.wav", wav_bytes, "audio/wav"),
            language_code=lang_code,
            model="saarika:v2.5",
        )

        transcript = getattr(response, "transcript", "") or ""
        # language_probability is the confidence score
        confidence = getattr(response, "language_probability", None)
        if confidence is None:
            # Heuristic: longer transcripts with real words are higher confidence
            confidence = min(0.9, max(0.3, len(transcript.split()) * 0.1))

        detected_lang = getattr(response, "language_code", lang_code)

        mode = classify_asr_confidence(confidence)
        logger.info(
            "ASR result: lang=%s, confidence=%.2f, mode=%s, text=%s",
            detected_lang, confidence, mode, transcript[:50],
        )

        return TranscriptionResult(
            text=transcript,
            language=detected_lang,
            confidence=round(confidence, 3),
            mode=mode,
        )

    async def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
    ) -> bytes | None:
        """Convert text to speech using Sarvam TTS (Bulbul V2).

        Returns audio bytes (WAV format) or None if unavailable.
        """
        if not self._available:
            return None

        try:
            lang_code = language if language in SUPPORTED_LANGUAGES else "hi-IN"

            response = self._client.text_to_speech.convert(
                text=text[:500],  # Limit text length
                target_language_code=lang_code,
                model="bulbul:v2",
                enable_preprocessing=True,
            )

            # Response contains base64-encoded audio
            audio_b64 = getattr(response, "audios", None)
            if audio_b64 and len(audio_b64) > 0:
                audio_bytes = base64.b64decode(audio_b64[0])
                logger.info("TTS generated: %d bytes for lang=%s", len(audio_bytes), lang_code)
                return audio_bytes

            return None

        except Exception as e:
            logger.error("TTS failed: %s", e)
            return None

    async def translate(
        self,
        text: str,
        source_lang: str = "en-IN",
        target_lang: str = "hi-IN",
    ) -> str:
        """Translate text between languages using Sarvam."""
        if not self._available:
            return text

        try:
            response = self._client.text.translate(
                input=text,
                source_language_code=source_lang,
                target_language_code=target_lang,
            )
            return getattr(response, "translated_text", text) or text
        except Exception as e:
            logger.warning("Translation failed: %s", e)
            return text


# Module-level singleton
_voice_service: VoiceService | None = None


def get_voice_service() -> VoiceService:
    """Get or create the VoiceService singleton."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
