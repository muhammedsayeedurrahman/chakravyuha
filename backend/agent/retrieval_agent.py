"""Retrieval agent -- tool-using agent that orchestrates retrieval tools."""

from __future__ import annotations

import logging

from backend.agent.hallucination_guard import sanitize_response
from backend.agent.tools import ToolResult, make_error, make_success
from backend.legal.adaptive_rag import AdaptiveRAG
from backend.legal.defence import DefenceAdvisor
from backend.legal.sections import SectionLookup

logger = logging.getLogger("chakravyuha")


class RetrievalAgent:
    """Agent that chains retrieval tools to answer legal queries.

    Pipeline: adaptive-retrieve -> LLM-generate -> hallucination-guard.
    """

    def __init__(self) -> None:
        self._adaptive_rag = AdaptiveRAG()
        self._section_lookup = SectionLookup()
        self._defence = DefenceAdvisor()
        self._rag = self._adaptive_rag._rag  # reuse the LegalRAG instance

    def retrieve_and_respond(
        self,
        query: str,
        language: str = "en-IN",
        conversation: list[dict] | None = None,
    ) -> ToolResult:
        """Full retrieval pipeline: search -> rank -> generate -> guard.

        Args:
            query: User's legal question.
            language: User's language code.
            conversation: Prior turns (for context).

        Returns:
            A ``ToolResult`` containing the final response and section data.
        """
        # Step 1: Adaptive retrieval
        rag_result = self._run_retrieval(query)
        if rag_result.status == "error":
            return rag_result

        sections = rag_result.data.get("sections", [])

        # Step 2: Generate LLM response
        gen_result = self._run_generation(query, sections, language)

        # Step 3: Hallucination guard
        if gen_result.status == "success":
            response_text = gen_result.data.get("response", "")
            guarded = sanitize_response(response_text, sections)
            return make_success(
                tool_name="retrieval_agent",
                data={
                    "response": guarded,
                    "sections": sections,
                    "strategy": rag_result.data.get("strategy", "unknown"),
                    "confidence": rag_result.data.get("confidence", "unknown"),
                },
                summary=f"Retrieved {len(sections)} sections, generated response",
            )

        return gen_result

    # ------------------------------------------------------------------
    # Individual tools
    # ------------------------------------------------------------------

    def _run_retrieval(self, query: str) -> ToolResult:
        """Tool: adaptive retrieval."""
        try:
            result = self._adaptive_rag.retrieve(query)
            sections = result.get("sections", [])

            if not sections:
                return make_error(
                    "adaptive_rag",
                    result.get("message", "No sections found."),
                )

            return make_success(
                tool_name="adaptive_rag",
                data={
                    "sections": sections,
                    "confidence": result["confidence"],
                    "strategy": result["strategy"],
                },
                summary=(
                    f"Found {len(sections)} sections via {result['strategy']} "
                    f"(confidence: {result['confidence']})"
                ),
                next_actions=["generate_response"],
            )
        except Exception as exc:
            logger.error("Retrieval failed: %s", exc)
            return make_error("adaptive_rag", str(exc))

    def _run_generation(
        self, query: str, sections: list[dict], language: str
    ) -> ToolResult:
        """Tool: LLM response generation with template fallback."""
        try:
            response = self._rag.generate_response(query, sections, language)

            return make_success(
                tool_name="llm_generate",
                data={"response": response, "sections": sections},
                summary="Generated LLM response",
                next_actions=["hallucination_check"],
            )
        except Exception as exc:
            logger.error("Generation failed: %s", exc)
            return make_error("llm_generate", str(exc))

    def lookup_section(self, section_id: str) -> ToolResult:
        """Tool: direct section lookup by ID."""
        section = self._section_lookup.lookup_section(section_id)
        if not section:
            return make_error("section_lookup", f"Section {section_id} not found.")

        cross_ref = self._section_lookup.get_both_laws(section_id)
        defence = self._defence.get_defence_strategy(section_id)

        return make_success(
            tool_name="section_lookup",
            data={
                "section": section,
                "cross_reference": cross_ref,
                "defence": defence,
            },
            summary=f"{section_id}: {section.get('title', '')}",
        )
