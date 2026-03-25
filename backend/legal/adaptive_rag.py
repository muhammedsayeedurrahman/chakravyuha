"""Adaptive RAG -- route queries by complexity to the right retrieval strategy."""

from __future__ import annotations

import logging
import re

from backend.config import RAG_TOP_K
from backend.legal.hybrid_retriever import HybridRetriever
from backend.legal.query_expander import QueryExpander
from backend.legal.rag import LegalRAG

logger = logging.getLogger("chakravyuha")

# Pattern for direct section references (e.g., "BNS 100", "IPC-302")
SECTION_REF_PATTERN = re.compile(
    r"\b(BNS|IPC)\s*[-\u2013]?\s*(\d+[A-Za-z]*)\b", re.IGNORECASE
)


def classify_query_complexity(query: str) -> str:
    """Classify query complexity: ``'simple'``, ``'moderate'``, or ``'complex'``.

    - **simple** -- direct section lookup (e.g., "What is BNS 100?")
    - **moderate** -- single-concept query (e.g., "punishment for theft")
    - **complex** -- multi-faceted or vague (e.g., "neighbor threatened me and stole my car")
    """
    if SECTION_REF_PATTERN.search(query):
        return "simple"

    words = query.split()

    if len(words) > 20:
        return "complex"
    if query.count("?") > 1:
        return "complex"

    complex_phrases = [
        "what should i do",
        "help me",
        "i don't know",
        "multiple",
        "several",
        "and also",
        "as well as",
        "in addition",
    ]
    if any(phrase in query.lower() for phrase in complex_phrases):
        return "complex"

    return "moderate"


class AdaptiveRAG:
    """Adaptive retrieval: routes to the best strategy based on query complexity."""

    def __init__(self) -> None:
        self._rag = LegalRAG()
        self._hybrid = HybridRetriever()
        self._expander = QueryExpander()

    def retrieve(self, query: str) -> dict:
        """Retrieve sections using a complexity-adaptive strategy.

        Returns:
            Dict with keys: sections, confidence, strategy, fallback, message.
        """
        complexity = classify_query_complexity(query)
        logger.info("Query complexity: %s for: %.80s", complexity, query)

        if complexity == "simple":
            return self._simple_retrieve(query)
        if complexity == "moderate":
            return self._moderate_retrieve(query)
        return self._complex_retrieve(query)

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _simple_retrieve(self, query: str) -> dict:
        """Direct section lookup or basic semantic search."""
        match = SECTION_REF_PATTERN.search(query)
        if match:
            law = match.group(1).upper()
            num = match.group(2)
            section_id = f"{law}-{num}"

            from backend.legal.sections import SectionLookup

            lookup = SectionLookup()
            section = lookup.lookup_section(section_id)
            if section:
                return {
                    "sections": [section],
                    "confidence": "high",
                    "strategy": "direct_lookup",
                    "fallback": False,
                    "message": None,
                }

        result = self._rag.retrieve_with_correction(query)
        return {**result, "strategy": "semantic"}

    def _moderate_retrieve(self, query: str) -> dict:
        """Synonym-expanded hybrid retrieval."""
        queries = self._expander.expand(query, use_hyde=False)
        sections = self._hybrid.retrieve(queries[0], top_k=RAG_TOP_K)

        if len(queries) > 1:
            extra = self._hybrid.retrieve(queries[1], top_k=3)
            seen = {s["section_id"] for s in sections}
            for s in extra:
                if s["section_id"] not in seen:
                    sections.append(s)
                    seen.add(s["section_id"])

        if not sections:
            return {
                "sections": [],
                "confidence": "none",
                "strategy": "hybrid_expanded",
                "fallback": True,
                "message": "No relevant sections found. Try rephrasing your question.",
            }

        confidence = "high" if sections[0].get("rrf_score", 0) > 0.02 else "medium"
        return {
            "sections": sections[:RAG_TOP_K],
            "confidence": confidence,
            "strategy": "hybrid_expanded",
            "fallback": False,
            "message": None,
        }

    def _complex_retrieve(self, query: str) -> dict:
        """Full expansion (synonyms + HyDE) + hybrid retrieval."""
        queries = self._expander.expand(query, use_hyde=True)

        all_sections: dict[str, tuple[float, dict]] = {}

        for q in queries:
            results = self._hybrid.retrieve(q, top_k=RAG_TOP_K)
            for s in results:
                sid = s["section_id"]
                score = s.get("rrf_score", 0)
                if sid not in all_sections or score > all_sections[sid][0]:
                    all_sections[sid] = (score, s)

        ranked = sorted(all_sections.values(), key=lambda x: x[0], reverse=True)
        sections = [s for _, s in ranked[:RAG_TOP_K]]

        if not sections:
            return {
                "sections": [],
                "confidence": "none",
                "strategy": "full_expansion",
                "fallback": True,
                "message": "No relevant sections found. Try breaking your question into simpler parts.",
            }

        return {
            "sections": sections,
            "confidence": "medium",
            "strategy": "full_expansion",
            "fallback": False,
            "message": "Multiple relevant sections found covering different aspects of your question.",
        }
