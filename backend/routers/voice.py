"""Voice router — POST /api/voice for ASR + legal + TTS pipeline."""

from __future__ import annotations

import base64

from fastapi import APIRouter, File, Form, UploadFile

from backend.services.orchestrator import get_orchestrator
from backend.services.voice_service import get_voice_service

router = APIRouter(prefix="/api", tags=["voice"])


@router.post("/voice")
async def process_voice(
    audio: UploadFile = File(...),
    language: str = Form("hi-IN"),
) -> dict:
    """Process voice input: ASR → legal query → TTS response."""
    orchestrator = get_orchestrator()
    audio_bytes = await audio.read()
    content_type = audio.content_type or "audio/webm"
    result = await orchestrator.process_voice(audio_bytes, language, content_type=content_type)

    # Encode audio output as base64 if present
    if result.get("audio"):
        result["audio"] = base64.b64encode(result["audio"]).decode("utf-8")

    return {"success": True, "data": result}


@router.post("/transcribe")
async def transcribe_only(
    audio: UploadFile = File(...),
    language: str = Form("hi-IN"),
) -> dict:
    """Transcribe audio without legal processing."""
    voice = get_voice_service()
    audio_bytes = await audio.read()
    content_type = audio.content_type or "audio/webm"
    result = await voice.transcribe(audio_bytes, language, content_type=content_type)
    return {"success": True, "data": result.model_dump()}


@router.post("/tts")
async def text_to_speech(text: str = Form(...), language: str = Form("hi-IN")) -> dict:
    """Convert text to speech audio."""
    voice = get_voice_service()
    audio_bytes = await voice.synthesize(text, language)

    if audio_bytes is None:
        return {"success": False, "error": "TTS not available"}

    return {
        "success": True,
        "data": {
            "audio": base64.b64encode(audio_bytes).decode("utf-8"),
            "language": language,
        },
    }
