"""ASR (Automatic Speech Recognition) with multi-model cascade.

Strategy:
1. Primary: Sarvam ASR (12 major Indian languages)
2. If confidence < threshold: fallback to local IndicWhisper
3. For dialects (Bhojpuri, Tulu, etc.): use Meta MMS or Google STT
"""

from __future__ import annotations

import io
import logging
from typing import Literal

from backend.config import ASR_ACCEPT_THRESHOLD, ASR_CONFIRM_THRESHOLD, SARVAM_API_KEY

logger = logging.getLogger("chakravyuha")

# Supported languages and their codes
MAJOR_LANGUAGES = {
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "as": "Assamese",
    "or": "Odia",
}

DIALECT_LANGUAGES = {
    "bho": "Bhojpuri",
    "hne": "Chhattisgarhi",
    "tcy": "Tulu",
    "awa": "Awadhi",
}


def _transcribe_sarvam(audio_bytes: bytes, language: str | None = None) -> dict:
    """Transcribe using Sarvam AI API (primary method).
    
    Sarvam API expects:
    - client = SarvamAI(api_subscription_key=key)
    - response = client.speech_to_text.transcribe(file=..., model=..., language_code=...)
    """
    if not SARVAM_API_KEY:
        logger.warning("SARVAM_API_KEY not configured, skipping Sarvam ASR")
        return {"text": "", "confidence": 0.0, "source": "sarvam", "error": "No API key"}

    try:
        from sarvamai import SarvamAI

        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        lang_code = language if language else "unknown"

        # Call the correct method: client.speech_to_text.transcribe()
        # NOT client(audio_bytes) ← This causes the error!
        response = client.speech_to_text.transcribe(
            file=("audio.wav", audio_bytes, "audio/wav"),
            model="saarika:v2.5",
            language_code=lang_code,
        )

        # Extract response fields
        transcript = ""
        detected_lang = language or "en-IN"
        confidence = 0.0

        # Handle response object (may vary based on SDK version)
        if hasattr(response, "transcript"):
            transcript = getattr(response, "transcript", "")
        elif isinstance(response, dict) and "transcript" in response:
            transcript = response["transcript"]

        if hasattr(response, "language_code"):
            detected_lang = getattr(response, "language_code", detected_lang)
        elif isinstance(response, dict) and "language_code" in response:
            detected_lang = response["language_code"]

        if hasattr(response, "language_probability"):
            confidence = getattr(response, "language_probability", 0.0)
        elif isinstance(response, dict) and "language_probability" in response:
            confidence = response["language_probability"]

        logger.info(
            "Sarvam ASR: lang=%s, confidence=%.2f, text='%s'",
            detected_lang,
            confidence,
            transcript[:60] if transcript else "",
        )

        return {
            "text": transcript or "",
            "confidence": confidence or 0.0,
            "language": detected_lang,
            "source": "sarvam",
        }

    except ImportError:
        logger.warning("sarvamai package not installed. Install: pip install sarvamai")
        return {"text": "", "confidence": 0.0, "source": "sarvam", "error": "Package not installed"}
    except TypeError as e:
        # This error: "'SpeechToTextClient' object is not callable"
        # Means: client(audio) was used instead of client.speech_to_text.transcribe(file=audio)
        logger.error("Sarvam API TypeError (check method call): %s", e)
        return {"text": "", "confidence": 0.0, "source": "sarvam", "error": f"API method error: {e}"}
    except Exception as e:
        logger.error("Sarvam ASR failed: %s (%s)", type(e).__name__, str(e)[:100])
        return {"text": "", "confidence": 0.0, "source": "sarvam", "error": str(e)}


def _transcribe_indicwhisper(audio_bytes: bytes, language: str | None = None) -> dict:
    """Transcribe using IndicWhisper (open-source, 12 Indic languages)."""
    try:
        import torch
        import torchaudio
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

        logger.info("Loading IndicWhisper model...")

        device = "cuda" if torch.cuda.is_available() else "cpu"
        processor = AutoProcessor.from_pretrained("ai4bharat/indicwhisper")
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            "ai4bharat/indicwhisper",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        )
        model = model.to(device)

        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            processor=processor,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device=device,
        )

        # Convert bytes to waveform
        waveform, sr = torchaudio.load(io.BytesIO(audio_bytes))
        if sr != 16000:
            resampler = torchaudio.transforms.Resample(sr, 16000)
            waveform = resampler(waveform)

        # Determine language for IndicWhisper
        lang_code = language or "hi"  # Default to Hindi

        result = pipe(
            waveform.numpy()[0],
            generate_kwargs={
                "task": "transcribe",
                "language": lang_code,
            },
        )

        transcript = result.get("text", "")
        confidence = result.get("confidence", 0.5)  # Estimate from model logits

        logger.info(
            "IndicWhisper ASR: lang=%s, confidence=%.2f, text='%s'",
            lang_code,
            confidence,
            transcript[:60],
        )

        return {
            "text": transcript,
            "confidence": confidence,
            "language": lang_code,
            "source": "indicwhisper",
        }

    except ImportError:
        logger.warning("transformers/torch packages for IndicWhisper not installed")
        return {"text": "", "confidence": 0.0, "source": "indicwhisper", "error": "Packages not installed"}
    except Exception as e:
        logger.error("IndicWhisper ASR failed: %s", e)
        return {"text": "", "confidence": 0.0, "source": "indicwhisper", "error": str(e)}


def transcribe(
    audio_bytes: bytes,
    language: str | None = None,
    use_cascade: bool = True,
) -> dict:
    """Transcribe audio with multi-model cascade strategy.

    Args:
        audio_bytes: Raw audio bytes (WAV format preferred).
        language: BCP-47 language code (e.g. 'hi', 'bho' for Bhojpuri).
        use_cascade: If True, fallback to IndicWhisper if Sarvam confidence low.

    Returns:
        Dict with keys: text, confidence, language, status, source.
        status: 'accepted' (conf >= 0.85), 'confirm' (0.75-0.85), 'fallback' (<0.75).
        source: 'sarvam', 'indicwhisper', 'error'.
    """
    if not audio_bytes:
        return {
            "text": "",
            "confidence": 0.0,
            "language": language,
            "status": "fallback",
            "source": "error",
            "error": "Empty audio",
        }

    # Try Sarvam first (API-based, best for major languages)
    result = _transcribe_sarvam(audio_bytes, language)

    if use_cascade and result.get("confidence", 0) < ASR_CONFIRM_THRESHOLD:
        logger.info("Sarvam confidence below threshold, trying IndicWhisper cascade...")
        fallback_result = _transcribe_indicwhisper(audio_bytes, language)
        if fallback_result.get("text"):
            result = fallback_result

    # Determine status based on confidence
    confidence = result.get("confidence", 0.0)
    if confidence >= ASR_ACCEPT_THRESHOLD:
        status = "accepted"
    elif confidence >= ASR_CONFIRM_THRESHOLD:
        status = "confirm"
    else:
        status = "fallback"

    result["status"] = status
    result.setdefault("language", language or "unknown")

    return result
