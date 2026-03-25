"""Orchestrator — connects voice, legal, escalation, and case services."""

from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

from backend.models.schemas import (
    GuidedFlowState,
    QueryResponse,
    VoiceResponse,
)
from backend.services.case_service import CaseService, get_case_service
from backend.services.escalation_service import EscalationService, get_escalation_service
from backend.services.legal_service import LegalService, get_legal_service
from backend.services.voice_service import VoiceService, get_voice_service
from backend.utils.disclaimer import append_disclaimer

logger = logging.getLogger("chakravyuha")


class Orchestrator:
    """Main pipeline orchestrator — voice→ASR→legal→TTS→response."""

    def __init__(
        self,
        legal: LegalService | None = None,
        voice: VoiceService | None = None,
        escalation: EscalationService | None = None,
        cases: CaseService | None = None,
    ) -> None:
        self._legal = legal or get_legal_service()
        self._voice = voice or get_voice_service()
        self._escalation = escalation or get_escalation_service()
        self._cases = cases or get_case_service()

    async def process_voice(
        self, audio_bytes: bytes, language: str | None = None, content_type: str = "audio/wav"
    ) -> dict:
        """Full voice pipeline: ASR → legal query → TTS → response."""
        # Step 1: ASR
        transcription = await self._voice.transcribe(audio_bytes, language, content_type=content_type)

        if transcription.mode == "fallback" or not transcription.text:
            return {
                "transcription": transcription.model_dump(),
                "message": "Could not understand audio. Please type your question instead.",
                "audio": None,
            }

        # Step 2: Legal query (run sync call in executor to avoid blocking)
        loop = asyncio.get_running_loop()
        legal_response = await loop.run_in_executor(
            None, self._legal.query_rag, transcription.text
        )

        # Step 3: Check escalation
        section_ids = [r.section.section_id for r in legal_response.sections]
        severity = self._escalation.classify_severity(transcription.text, section_ids)
        escalation = self._escalation.get_escalation_info(severity, transcription.text)

        # Step 4: TTS on summary
        audio_bytes_out = None
        if transcription.language != "en-IN":
            tts_text = legal_response.summary[:300]
            audio_bytes_out = await self._voice.synthesize(
                tts_text, transcription.language
            )

        return {
            "transcription": transcription.model_dump(),
            "legal_response": legal_response.model_dump(),
            "escalation": escalation.model_dump() if escalation.should_escalate else None,
            "audio": audio_bytes_out,
        }

    async def process_text(self, text: str, language: str = "en-IN") -> dict:
        """Text query pipeline: legal query → escalation check → response."""
        loop = asyncio.get_running_loop()
        legal_response = await loop.run_in_executor(
            None, self._legal.query_rag, text
        )

        section_ids = [r.section.section_id for r in legal_response.sections]
        severity = self._escalation.classify_severity(text, section_ids)
        escalation = self._escalation.get_escalation_info(severity, text)

        return {
            "legal_response": legal_response.model_dump(),
            "escalation": escalation.model_dump() if escalation.should_escalate else None,
        }

    async def process_guided(self, state: dict, answer: str) -> dict:
        """Guided flow step → next step or result."""
        flow_state = GuidedFlowState(**state)

        if answer:
            step = self._legal.process_guided_answer(flow_state, answer)
        else:
            step = self._legal.get_guided_step(flow_state)

        result = step.model_dump()

        if step.is_leaf and step.matched_sections:
            section_ids = [s.section_id for s in step.matched_sections]
            severity = step.severity or self._escalation.classify_severity(
                answer, section_ids
            )
            escalation = self._escalation.get_escalation_info(severity)
            result["escalation"] = escalation.model_dump() if escalation.should_escalate else None

        return result


# Thread-safe singleton via lru_cache
@lru_cache(maxsize=1)
def get_orchestrator() -> Orchestrator:
    """Get or create the Orchestrator singleton (thread-safe)."""
    return Orchestrator()
