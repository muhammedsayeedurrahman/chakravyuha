"""TTS (Text-to-Speech) with multi-model cascade.

Strategy:
1. Primary: Sarvam Bulbul-V2 API (best quality, 11 Indian languages)
2. Fallback: Piper TTS (local, fast, offline-capable)
3. Last resort: eSpeak-ng (tiny, robotic, but works anywhere)
"""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path

from backend.config import SARVAM_API_KEY, SUPPORTED_LANGUAGES

logger = logging.getLogger("chakravyuha")

# Piper voice models (lightweight, pre-trained for Indic languages)
PIPER_VOICES = {
    "hi": "hi_IN-male-medium",  # Hindi
    "ta": "ta_IN-female-medium",  # Tamil
    "te": "te_IN-male-medium",  # Telugu
    "kn": "kn_IN-female-medium",  # Kannada
    "ml": "ml_IN-male-medium",  # Malayalam
}


def _synthesize_sarvam(text: str, language: str = "hi-IN") -> bytes | None:
    """Generate speech using Sarvam Bulbul-V2 API (primary).
    
    Correct usage:
    - client = SarvamAI(api_subscription_key=key)
    - response = client.text_to_speech.convert(text=..., target_language_code=..., model=...)
    
    NOT: client(text) ← This causes TypeError
    """
    if not SARVAM_API_KEY:
        logger.debug("SARVAM_API_KEY not configured, skipping Sarvam TTS")
        return None

    if not text or not text.strip():
        return None

    try:
        from sarvamai import SarvamAI

        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

        # Truncate long text (API limit ~500 chars per request)
        truncated = text[:500] if len(text) > 500 else text

        lang_code = language if language in SUPPORTED_LANGUAGES else "hi-IN"

        # Call the CORRECT method: client.text_to_speech.convert()
        # NOT client(text, language) ← This causes the error!
        response = client.text_to_speech.convert(
            text=truncated,
            target_language_code=lang_code,
            model="bulbul:v2",
            enable_preprocessing=True,
        )

        # Extract audio from response (may be object or dict)
        audio_b64 = None
        
        if hasattr(response, "audios"):
            audio_b64 = getattr(response, "audios", None)
        elif isinstance(response, dict) and "audios" in response:
            audio_b64 = response["audios"]

        if audio_b64 and len(audio_b64) > 0:
            audio_bytes = base64.b64decode(audio_b64[0])
            logger.info("Sarvam TTS: %d bytes, lang=%s", len(audio_bytes), lang_code)
            return audio_bytes

        logger.warning("Sarvam TTS returned empty audios list")
        return None

    except ImportError:
        logger.warning("sarvamai not installed — Sarvam TTS unavailable")
        return None
    except TypeError as e:
        # This error: "'TextToSpeechClient' object is not callable"
        # Means: client(text) was used instead of client.text_to_speech.convert(text=...)
        logger.error("Sarvam API TypeError (check method call): %s", e)
        return None
    except Exception as e:
        logger.error("Sarvam TTS failed: %s (%s)", type(e).__name__, str(e)[:100])
        return None


def _synthesize_piper(text: str, language: str = "hi-IN") -> bytes | None:
    """Generate speech using Piper TTS (local, offline-capable).
    
    Lightweight (~200MB models) local inference.
    Uses in-memory WAV buffer to avoid disk I/O.
    """
    if not text or not text.strip():
        return None

    try:
        from piper import PiperVoice

        # Map language code to Piper voice
        lang_short = language.split("-")[0] if "-" in language else language
        voice_name = PIPER_VOICES.get(lang_short, "hi_IN-male-medium")

        logger.debug("Loading Piper voice: %s", voice_name)
        voice = PiperVoice.load(voice_name)

        # Synthesize to in-memory WAV buffer
        wav_buffer = io.BytesIO()
        voice.synthesize(text, wav_file=wav_buffer)

        audio_bytes = wav_buffer.getvalue()
        if audio_bytes and len(audio_bytes) > 0:
            logger.info("Piper TTS: %d bytes, lang=%s", len(audio_bytes), language)
            return audio_bytes

        logger.warning("Piper TTS returned empty audio buffer")
        return None

    except ImportError:
        logger.warning("piper-tts not installed — Piper fallback unavailable")
        return None
    except FileNotFoundError as e:
        logger.warning("Piper voice model file not found: %s", e)
        return None
    except Exception as e:
        logger.error("Piper TTS failed: %s (%s)", type(e).__name__, str(e)[:100])
        return None


def _synthesize_espeak(text: str, language: str = "hi-IN") -> bytes | None:
    """Generate speech using eSpeak-ng (tiny, robotic, last resort).
    
    Smallest footprint (~2MB), works anywhere.
    Quality is poor but ensures no complete failure.
    """
    if not text or not text.strip():
        return None

    try:
        import subprocess

        # Map language to eSpeak language code
        lang_map = {
            "hi": "hi",  # Hindi
            "ta": "ta",  # Tamil
            "te": "te",  # Telugu
            "en": "en",  # English
        }
        lang_code = lang_map.get(language.split("-")[0], "en")

        # eSpeak command: espeak -v <lang> <text> --stdout
        result = subprocess.run(
            ["espeak", "-v", lang_code, text, "--stdout"],
            capture_output=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout and len(result.stdout) > 0:
            logger.info("eSpeak TTS: %d bytes, lang=%s", len(result.stdout), language)
            return result.stdout

        if result.returncode != 0:
            logger.warning("eSpeak returned non-zero exit code %d: %s", 
                         result.returncode, result.stderr.decode()[:100])
        else:
            logger.warning("eSpeak TTS returned empty audio")
        return None

    except FileNotFoundError:
        logger.warning("eSpeak-ng binary not found — install with: apt-get install espeak-ng")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("eSpeak TTS timeout after 10 seconds")
        return None
    except Exception as e:
        logger.error("eSpeak TTS failed: %s (%s)", type(e).__name__, str(e)[:100])
        return None


def synthesize(
    text: str,
    language: str = "hi-IN",
    voice: str | None = None,
    use_cascade: bool = True,
) -> bytes | None:
    """Convert text to speech with multi-model cascade.

    Args:
        text: Text to convert to speech.
        language: BCP-47 language code (e.g. 'hi-IN').
        voice: Optional voice name override.
        use_cascade: If True, fallback to Piper, then eSpeak if Sarvam fails.

    Returns:
        Audio bytes (WAV format) or None if all TTS methods fail.
    """
    if not text or not text.strip():
        return None

    # Try Sarvam first (best quality)
    audio_bytes = _synthesize_sarvam(text, language)
    if audio_bytes:
        return audio_bytes

    if not use_cascade:
        logger.warning("TTS cascade disabled, no fallback available")
        return None

    # Fallback to Piper (local, offline)
    logger.info("Sarvam TTS unavailable, trying Piper cascade...")
    audio_bytes = _synthesize_piper(text, language)
    if audio_bytes:
        return audio_bytes

    # Last resort: eSpeak-ng (tiny, robotic)
    logger.info("Piper TTS unavailable, trying eSpeak-ng last resort...")
    audio_bytes = _synthesize_espeak(text, language)
    if audio_bytes:
        return audio_bytes

    logger.error("All TTS methods failed for language=%s", language)
    return None


def get_available_languages() -> dict[str, str]:
    """Return dict of supported language codes and names."""
    return dict(SUPPORTED_LANGUAGES)
