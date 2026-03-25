"""Main pipeline orchestrator -- intent-routed agentic pipeline.

Flow: Voice/Text -> Intent -> Route -> Adaptive RAG -> LLM -> Hallucination Guard -> Response.
"""

from __future__ import annotations

import logging

from backend.agent.escalation import check_escalation_needed, get_escalation_info
from backend.agent.hallucination_guard import sanitize_response
from backend.agent.complaint_drafter_agent import ComplaintDrafterAgent
from backend.agent.intent_classifier import (
    INTENT_COMPLAINT_DRAFT,
    INTENT_ESCALATION,
    INTENT_GREETING,
    INTENT_GUIDED_FLOW,
    INTENT_SECTION_LOOKUP,
    classify_intent,
)
from backend.agent.retrieval_agent import RetrievalAgent
from backend.config import DISCLAIMER, NALSA_HELPLINE
from backend.legal.defence import DefenceAdvisor
from backend.legal.guided_flow import GuidedFlow
from backend.legal.rag import LegalRAG
from backend.legal.sections import SectionLookup
from backend.tracker.case_tracker import CaseTracker
from backend.voice.asr import transcribe
from backend.voice.tts import synthesize

logger = logging.getLogger("chakravyuha")


class Orchestrator:
    """Main agentic pipeline: input -> intent -> retrieve -> generate -> guard -> respond."""

    def __init__(self) -> None:
        self._guided_flow = GuidedFlow()
        self._rag = LegalRAG()
        self._sections = SectionLookup()
        self._defence = DefenceAdvisor()
        self._tracker = CaseTracker()
        self._retrieval_agent = RetrievalAgent()
        self._complaint_agent = ComplaintDrafterAgent()

    # ------------------------------------------------------------------
    # Voice input
    # ------------------------------------------------------------------

    def process_voice_input(self, audio_bytes: bytes, session_state: dict) -> dict:
        """Process voice input: ASR -> text pipeline -> optional TTS.

        Returns:
            Dict with text_response, audio_response, asr_result, sections, session_state.
        """
        language = session_state.get("language", "hi-IN")
        asr_result = transcribe(audio_bytes, language=language)

        if asr_result["status"] == "fallback":
            return {
                "text_response": asr_result.get(
                    "error", "Could not transcribe audio. Please type your query."
                ),
                "audio_response": None,
                "asr_result": asr_result,
                "sections": [],
                "session_state": session_state,
            }

        if asr_result["status"] == "confirm":
            return {
                "text_response": (
                    f'Did you say: "{asr_result["text"]}"? '
                    "Please confirm or try again."
                ),
                "audio_response": None,
                "asr_result": asr_result,
                "sections": [],
                "session_state": {
                    **session_state,
                    "pending_confirmation": asr_result["text"],
                },
            }

        # Accepted -- run through the text pipeline and merge asr_result
        text_result = self.process_text_input(asr_result["text"], session_state)
        return {**text_result, "asr_result": asr_result}

    # ------------------------------------------------------------------
    # Text input (intent-routed)
    # ------------------------------------------------------------------

    def process_text_input(self, text: str, session_state: dict) -> dict:
        """Process text input through the intent-routed agentic pipeline.

        Args:
            text: User's text query.
            session_state: Current session state dict.

        Returns:
            Dict with text_response, audio_response, sections, session_state.
        """
        language = session_state.get("language", "en-IN")
        conversation = session_state.get("conversation", [])

        # Classify intent
        intent = classify_intent(text, conversation)
        logger.info(
            "Intent: %s (confidence=%.2f, method=%s)",
            intent.intent,
            intent.confidence,
            intent.method,
        )

        # Route by intent
        if intent.intent == INTENT_GREETING:
            return self._handle_greeting(text, language, session_state)

        if intent.intent == INTENT_SECTION_LOOKUP:
            section_id = intent.entities.get("section_id", "")
            return self._handle_section_lookup(section_id, text, language, session_state)

        if intent.intent == INTENT_ESCALATION:
            return self._handle_escalation(text, language, session_state)

        if intent.intent == INTENT_GUIDED_FLOW:
            return self._handle_guided_suggestion(text, language, session_state)

        if intent.intent == INTENT_COMPLAINT_DRAFT:
            return self._handle_complaint_draft(text, language, session_state)

        # Default: legal query (also handles followup, general)
        return self._handle_legal_query(text, language, session_state)

    # ------------------------------------------------------------------
    # Intent handlers
    # ------------------------------------------------------------------

    def _handle_greeting(
        self, text: str, language: str, session_state: dict
    ) -> dict:
        greeting = (
            "Namaste! I'm Chakravyuha, your AI legal assistant for India. "
            "Ask me about any legal question -- criminal law sections, punishments, "
            "or your rights. You can also try the **Guided Legal Help** tab for "
            "step-by-step guidance."
        )
        return self._build_response(greeting, [], language, session_state, text)

    def _handle_section_lookup(
        self, section_id: str, text: str, language: str, session_state: dict
    ) -> dict:
        result = self._retrieval_agent.lookup_section(section_id)

        if result.status == "error":
            # Section not found -- fall back to normal legal query
            return self._handle_legal_query(text, language, session_state)

        section = result.data["section"]
        sections = [section]

        # Include cross-reference (IPC/BNS equivalent) so the LLM can cite it
        cross_ref = result.data.get("cross_reference", {})
        for key in ("bns", "ipc"):
            ref = cross_ref.get(key)
            if ref and ref.get("section_id") != section.get("section_id"):
                sections.append(ref)

        # Generate a conversational LLM response
        response = self._rag.generate_response(text, sections, language)
        response = sanitize_response(response, sections)

        # Check escalation
        if check_escalation_needed(text, sections):
            esc = get_escalation_info()
            response += (
                f"\n\n**Important:** {esc['message']}\n"
                f"Police: {esc['contacts'][0]['number']} | "
                f"NALSA: {esc['contacts'][1]['number']}"
            )

        return self._build_response(response, sections, language, session_state, text)

    def _handle_escalation(
        self, text: str, language: str, session_state: dict
    ) -> dict:
        # Still retrieve legal info for context
        agent_result = self._retrieval_agent.retrieve_and_respond(text, language)
        esc = get_escalation_info()

        if agent_result.status == "success":
            response = agent_result.data.get("response", "")
            sections = agent_result.data.get("sections", [])
        else:
            response = ""
            sections = []

        urgency = (
            f"**This appears to be an emergency.**\n"
            f"Please contact: **Police ({esc['contacts'][0]['number']})**, "
            f"**NALSA ({esc['contacts'][1]['number']})**\n\n"
        )
        response = urgency + response

        return self._build_response(response, sections, language, session_state, text)

    def _handle_guided_suggestion(
        self, text: str, language: str, session_state: dict
    ) -> dict:
        suggestion = (
            "It sounds like you need step-by-step guidance. "
            "Please switch to the **Guided Legal Help** tab above -- "
            "it will walk you through simple questions to find the exact "
            "legal sections that apply to your situation.\n\n"
            "Or, you can ask me a specific legal question right here."
        )
        return self._build_response(suggestion, [], language, session_state, text)

    def _handle_complaint_draft(
        self, text: str, language: str, session_state: dict
    ) -> dict:
        """Handle complaint drafting intent via the agentic pipeline."""
        result = self._complaint_agent.auto_draft(
            narrative=text,
            language=language,
        )

        if result.status == "error":
            response = (
                "I'd like to help you draft a legal document, but I need more details "
                "about the incident. Please describe:\n\n"
                "- What happened?\n"
                "- When and where did it occur?\n"
                "- Who is involved?\n\n"
                "You can also use the **Document Drafting** feature directly "
                "via the API at `/api/documents/auto-draft`."
            )
            return self._build_response(response, [], language, session_state, text)

        # Build informative response with the draft
        sections_info = ", ".join(result.applicable_sections) if result.applicable_sections else "None identified"
        extracted = result.extracted_info

        response_parts = [
            f"I've drafted a **{result.document_type}** for you based on your description.\n",
            f"**Offense detected:** {extracted.offense.title()} "
            f"(confidence: {extracted.offense_confidence:.0%})\n"
            f"**Applicable sections:** {sections_info}\n"
            f"**Jurisdiction:** {extracted.jurisdiction}\n",
        ]

        if result.missing_fields:
            missing_labels = ", ".join(f.replace("_", " ") for f in result.missing_fields)
            response_parts.append(
                f"\n**Missing information:** {missing_labels} "
                f"— please provide these for a more complete document.\n"
            )

        response_parts.append(f"\n---\n\n{result.content}")

        if result.strategy_summary:
            strategy = result.strategy_summary
            response_parts.append(
                f"\n\n---\n**Next steps:** {strategy.get('next_immediate_action', '')}\n"
                f"**Estimated timeline:** {strategy.get('total_timeline', '')}\n"
                f"**Estimated cost:** {strategy.get('total_estimated_cost', '')}"
            )

        full_response = "\n".join(response_parts)

        # Build sections list for the response
        sections = []
        if extracted:
            for bns_code in extracted.bns_sections:
                sections.append({"section_id": bns_code, "law": "BNS"})

        return self._build_response(full_response, sections, language, session_state, text)

    def _handle_legal_query(
        self, text: str, language: str, session_state: dict
    ) -> dict:
        """Handle general legal queries via the retrieval agent."""
        agent_result = self._retrieval_agent.retrieve_and_respond(text, language)

        if agent_result.status == "error":
            error_msg = (
                "I couldn't find relevant legal sections for your query. "
                "Try rephrasing your question, or use the **Guided Legal Help** "
                "tab for step-by-step guidance. "
                f"You can also call NALSA ({NALSA_HELPLINE}) for free legal aid."
            )
            return self._build_response(error_msg, [], language, session_state, text)

        response = agent_result.data.get("response", "")
        sections = agent_result.data.get("sections", [])

        # Check escalation on legal queries too
        if check_escalation_needed(text, sections):
            esc = get_escalation_info()
            response += (
                f"\n\n**Important:** {esc['message']}\n"
                f"Police: {esc['contacts'][0]['number']} | "
                f"NALSA: {esc['contacts'][1]['number']}"
            )

        return self._build_response(response, sections, language, session_state, text)

    # ------------------------------------------------------------------
    # Response builder
    # ------------------------------------------------------------------

    def _build_response(
        self,
        text_response: str,
        sections: list[dict],
        language: str,
        session_state: dict,
        user_text: str,
    ) -> dict:
        """Build final response dict with disclaimer, optional TTS, and session update."""
        # Append disclaimer if not already present
        if DISCLAIMER not in text_response:
            text_response += f"\n\n---\n*{DISCLAIMER}*"

        # Generate TTS for non-English languages
        audio_response = None
        if language != "en-IN" and sections:
            summary = sections[0].get("title", "")
            audio_response = synthesize(summary, language=language)

        # Immutable conversation update
        conversation = list(session_state.get("conversation", []))
        conversation.append({"role": "user", "content": user_text})
        conversation.append({"role": "assistant", "content": text_response})

        return {
            "text_response": text_response,
            "audio_response": audio_response,
            "sections": sections,
            "session_state": {
                **session_state,
                "conversation": conversation,
                "last_sections": [s.get("section_id", "") for s in sections],
            },
        }

    # ------------------------------------------------------------------
    # Guided flow (unchanged)
    # ------------------------------------------------------------------

    def process_guided_answer(self, answer_index: int, session_state: dict) -> dict:
        """Process a guided flow button selection.

        Args:
            answer_index: Zero-based index of selected option.
            session_state: Current session state with 'guided_state' key.

        Returns:
            Dict with next question or final result.
        """
        guided_state = session_state.get("guided_state", self._guided_flow.reset())
        result = self._guided_flow.process_answer(guided_state, answer_index)

        if "error" in result:
            return {"error": result["error"], "session_state": session_state}

        new_session = {**session_state, "guided_state": result.get("state", guided_state)}

        if result.get("terminal"):
            enriched_sections = []
            for sid in result.get("sections", []):
                section_data = self._sections.lookup_section(sid)
                if section_data:
                    enriched_sections.append(section_data)

            defence_info = None
            if result.get("sections"):
                defence_info = self._defence.get_defence_strategy(result["sections"][0])

            return {
                "terminal": True,
                "summary": result.get("summary", ""),
                "summary_hi": result.get("summary_hi", ""),
                "sections": enriched_sections,
                "ipc_sections": result.get("ipc_sections", []),
                "next_steps": result.get("next_steps", []),
                "escalation": result.get("escalation", False),
                "defence": defence_info,
                "disclaimer": DISCLAIMER,
                "session_state": new_session,
            }

        if result.get("type") == "free_text":
            return {
                "terminal": False,
                "type": "free_text",
                "prompt": result.get("prompt", ""),
                "prompt_hi": result.get("prompt_hi", ""),
                "session_state": new_session,
            }

        return {
            "terminal": False,
            "question": result.get("question", ""),
            "question_hi": result.get("question_hi", ""),
            "options": result.get("options", []),
            "session_state": new_session,
        }

    def get_initial_question(self) -> dict:
        """Get the first question of the guided flow."""
        state = self._guided_flow.reset()
        result = self._guided_flow.get_current_question(state)
        return {**result, "guided_state": state}

    def get_section_details(self, section_id: str) -> dict:
        """Get full details for a section including cross-reference."""
        return self._sections.get_both_laws(section_id)
