"""Legal RAG pipeline — ChromaDB retrieval with corrective re-query."""

from __future__ import annotations

import logging

from backend.config import (
    CHROMA_PERSIST_DIR,
    DISCLAIMER,
    EMBEDDING_MODEL,
    NALSA_HELPLINE,
    RAG_CONFIDENCE_HIGH,
    RAG_SIMILARITY_THRESHOLD,
    RAG_TOP_K,
)

logger = logging.getLogger("chakravyuha")


class LegalRAG:
    """Retrieval-Augmented Generation for legal section lookup."""

    COLLECTION_NAME = "legal_sections"

    def __init__(self, persist_dir: str | None = None):
        self._persist_dir = persist_dir or CHROMA_PERSIST_DIR
        self._collection = None
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self._ef,
            )
        except ImportError:
            logger.warning("chromadb not installed — RAG disabled, using keyword search")
        except Exception:
            logger.warning("ChromaDB collection not found — RAG disabled")

    @property
    def is_ready(self) -> bool:
        return self._collection is not None and self._collection.count() > 0

    def retrieve_sections(
        self, query: str, top_k: int = RAG_TOP_K, threshold: float = RAG_SIMILARITY_THRESHOLD
    ) -> list[dict]:
        """Retrieve relevant legal sections for a query.

        Args:
            query: User's legal question in natural language.
            top_k: Number of results to return.
            threshold: Minimum similarity score (lower distance = more similar).

        Returns:
            List of dicts with keys: section_id, title, description, score, metadata.
        """
        if not self.is_ready:
            return []

        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        sections = []
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i]
            # ChromaDB returns L2 distance; convert to similarity score
            similarity = 1.0 / (1.0 + distance)
            if similarity < threshold:
                continue
            metadata = results["metadatas"][0][i]
            sections.append({
                "section_id": metadata.get("section_id", ""),
                "title": metadata.get("title", ""),
                "law": metadata.get("law", ""),
                "description": doc,
                "score": round(similarity, 3),
                "punishment": metadata.get("punishment", ""),
                "cognizable": metadata.get("cognizable", ""),
                "bailable": metadata.get("bailable", ""),
            })

        return sections

    def retrieve_with_correction(self, query: str) -> dict:
        """Corrective RAG: retrieve, check confidence, re-query if needed.

        Returns:
            Dict with keys: sections, confidence, fallback, message.
        """
        sections = self.retrieve_sections(query)

        if not sections:
            return {
                "sections": [],
                "confidence": "none",
                "fallback": True,
                "message": (
                    "I couldn't find a matching legal section for your query. "
                    f"Please try describing your issue differently, or call NALSA ({NALSA_HELPLINE}) "
                    "for free legal aid."
                ),
            }

        top_score = sections[0]["score"]

        if top_score >= RAG_CONFIDENCE_HIGH:
            return {
                "sections": sections,
                "confidence": "high",
                "fallback": False,
                "message": None,
            }

        # Corrective step: re-query with a more specific prompt
        refined_query = f"Indian criminal law section for: {query}. What BNS or IPC section applies?"
        refined_sections = self.retrieve_sections(refined_query)

        if refined_sections and refined_sections[0]["score"] >= RAG_SIMILARITY_THRESHOLD:
            # Merge results, preferring higher scores
            seen = set()
            merged = []
            for s in refined_sections + sections:
                if s["section_id"] not in seen:
                    seen.add(s["section_id"])
                    merged.append(s)
            merged.sort(key=lambda x: x["score"], reverse=True)
            return {
                "sections": merged[:RAG_TOP_K],
                "confidence": "medium",
                "fallback": False,
                "message": "Results have moderate confidence. Please verify with a legal professional.",
            }

        return {
            "sections": sections,
            "confidence": "low",
            "fallback": True,
            "message": (
                "The results have low confidence. We recommend consulting a lawyer "
                f"or calling NALSA ({NALSA_HELPLINE}) for guidance."
            ),
        }

    def generate_response(
        self, query: str, sections: list[dict], language: str = "en-IN"
    ) -> str:
        """Generate a response for retrieved sections — LLM-powered with template fallback.

        Args:
            query: Original user query.
            sections: List of retrieved section dicts.
            language: User's language code (e.g., 'hi-IN').

        Returns:
            Formatted response string.
        """
        if not sections:
            return (
                "**Status**: No matching legal sections found.\n\n"
                "**What to do**: Please describe your issue in more detail, "
                f"or contact NALSA ({NALSA_HELPLINE}) for free legal aid.\n\n"
                "**Law**: Unable to determine applicable sections.\n\n"
                f"{DISCLAIMER}"
            )

        # Try LLM-powered generation first
        from backend.config import LLM_ENABLED

        if LLM_ENABLED:
            try:
                from backend.services.llm import get_llm_service

                llm = get_llm_service()
                llm_response = llm.generate(query, sections, language)
                if llm_response:
                    return llm_response
            except Exception as e:
                logger.warning("LLM generation failed, falling back to template: %s", e)

        # Template fallback (structured format)
        try:
            return self._template_response(query, sections)
        except Exception as e:
            logger.error("Template response failed: %s — using emergency fallback", e)
            # Emergency fallback when both LLM and template fail
            return (
                "**Status**: Your legal issue has been noted.\n\n"
                "**What to do**: Please choose a category: "
                "Theft, Assault, Fraud, Property, Family, Consumer, Employment, Emergency. "
                f"Or contact NALSA ({NALSA_HELPLINE}) for free legal aid.\n\n"
                "**Law**: Please provide more details for specific legal sections.\n\n"
                f"{DISCLAIMER}"
            )

    def _template_response(self, query: str, sections: list[dict]) -> str:
        """Format retrieved sections into a structured template response (fallback).

        Uses Status / What to do / Law format for zero-hallucination output.

        Args:
            query: Original user query.
            sections: List of retrieved section dicts.

        Returns:
            Formatted response string.
        """
        top = sections[0] if sections else {}
        bail_status = "Bailable" if top.get("bailable") else "Non-bailable"
        cog_status = "Cognizable" if top.get("cognizable") else "Non-cognizable"

        # Status line
        status = top.get("title", "Legal issue identified")

        # What to do
        actions = []
        if cog_status == "Cognizable":
            actions.append("File an FIR at the nearest police station — police must register it.")
        else:
            actions.append("File a complaint with a magistrate under CrPC Section 200.")
        if bail_status == "Non-bailable":
            actions.append("Consult a lawyer immediately for bail application.")
        else:
            actions.append("Bail is available as a matter of right.")
        actions.append(f"Contact NALSA ({NALSA_HELPLINE}) for free legal aid.")

        # Law lines
        law_lines = []
        for s in sections:
            law_label = "BNS 2023" if s.get("law") == "BNS" else "IPC 1860"
            punishment = s.get("punishment", "Not specified")
            law_lines.append(f"{s['section_id']} ({law_label}): {s['title']} — Punishment: {punishment}")

        parts = [
            f"**Status**: {status} ({cog_status}, {bail_status})",
            f"**What to do**: " + " ".join(actions),
            f"**Law**: " + "; ".join(law_lines),
        ]

        parts.append(f"\n{DISCLAIMER}")
        return "\n\n".join(parts)


# Module-level singleton
_rag_instance: LegalRAG | None = None


def get_rag() -> LegalRAG:
    """Get or create the LegalRAG singleton."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = LegalRAG()
    return _rag_instance
