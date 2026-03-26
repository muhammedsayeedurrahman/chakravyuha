"""Legal service — guided flow, RAG pipeline, section lookup, defence strategies."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from backend.config import get_settings
from backend.data.loader import (
    build_keyword_index,
    build_section_index,
    load_bns_to_ipc_map,
    load_defence_strategies,
    load_guided_tree,
    load_ipc_to_bns_map,
)
from backend.models.schemas import (
    GuidedFlowState,
    GuidedFlowStep,
    GuidedOption,
    LegalSection,
    QueryResponse,
    SectionResult,
)
from backend.utils.confidence import classify_rag_confidence
from backend.utils.disclaimer import append_disclaimer

logger = logging.getLogger("chakravyuha")


class LegalService:
    """Core legal service — deterministic guided flow + RAG fallback."""

    def __init__(self) -> None:
        self._section_index = build_section_index()
        self._keyword_index = build_keyword_index(self._section_index)
        self._guided_tree = load_guided_tree()
        self._defence_strategies = load_defence_strategies()
        self._ipc_to_bns = load_ipc_to_bns_map()
        self._bns_to_ipc = load_bns_to_ipc_map()
        self._retriever = None  # Initialized lazily via init_rag()
        logger.info(
            "LegalService initialized: %d sections, %d keywords",
            len(self._section_index),
            len(self._keyword_index),
        )

    # ── Guided Flow (Deterministic — 100% accuracy) ──────────────────────────

    def get_guided_step(self, state: GuidedFlowState) -> GuidedFlowStep:
        """Return the current guided flow step based on state."""
        node_key = state.current_node
        node = self._guided_tree.get(node_key)

        if node is None:
            return GuidedFlowStep(
                node_key=node_key,
                question="Sorry, this path is not available. Please start over.",
                is_leaf=True,
            )

        options = []
        for opt in node.get("options", []):
            options.append(
                GuidedOption(
                    label=opt.get("label", ""),
                    label_hi=opt.get("label_hi", ""),
                    next=opt.get("next"),
                    sections=opt.get("sections", []),
                    severity=opt.get("severity"),
                )
            )

        return GuidedFlowStep(
            node_key=node_key,
            question=node.get("question", ""),
            question_hi=node.get("question_hi", ""),
            options=options,
        )

    def process_guided_answer(
        self, state: GuidedFlowState, answer: str
    ) -> GuidedFlowStep:
        """Process user answer and advance to next step or return matched sections."""
        node = self._guided_tree.get(state.current_node)
        if node is None:
            return GuidedFlowStep(
                node_key=state.current_node,
                question="Invalid state. Please start over.",
                is_leaf=True,
            )

        # Find matching option
        selected = None
        for opt in node.get("options", []):
            if opt.get("label") == answer or opt.get("label_hi") == answer:
                selected = opt
                break

        if selected is None:
            # Try partial match
            answer_lower = answer.lower()
            for opt in node.get("options", []):
                if answer_lower in opt.get("label", "").lower():
                    selected = opt
                    break

        if selected is None:
            return self.get_guided_step(state)

        # If leaf node (has sections), return matched sections
        if selected.get("sections"):
            matched = [
                self._section_index[sid]
                for sid in selected["sections"]
                if sid in self._section_index
            ]
            return GuidedFlowStep(
                node_key=state.current_node,
                question="Here are the relevant legal sections:",
                is_leaf=True,
                matched_sections=matched,
                severity=selected.get("severity"),
            )

        # Navigate to next node
        next_key = selected.get("next", "root")
        new_state = GuidedFlowState(
            current_node=next_key,
            path=[*state.path, state.current_node],
        )
        return self.get_guided_step(new_state)

    # ── Section Lookup ───────────────────────────────────────────────────────

    def lookup_section(self, section_id: str) -> LegalSection | None:
        """Direct section lookup by ID (e.g., 'BNS-103' or 'IPC-302')."""
        return self._section_index.get(section_id)

    def get_corresponding_section(self, section_id: str) -> LegalSection | None:
        """Get the BNS equivalent of an IPC section or vice versa."""
        if section_id.startswith("IPC-"):
            bns_id = self._ipc_to_bns.get(section_id)
            return self._section_index.get(bns_id) if bns_id else None
        elif section_id.startswith("BNS-"):
            ipc_id = self._bns_to_ipc.get(section_id)
            return self._section_index.get(ipc_id) if ipc_id else None
        return None

    # ── Defence Strategies ───────────────────────────────────────────────────

    def get_defence_strategy(self, section_id: str) -> dict | None:
        """Get defence strategies for a given section."""
        for entry in self._defence_strategies:
            if entry.get("section_id") == section_id:
                return entry
        return None

    # ── Keyword-Based Search (Fallback before RAG) ───────────────────────────

    # Shared stemmer + synonym map for consistent normalization
    from backend.utils.stemmer import STEM_MAP as _WORD_STEMS_BASE, SYNONYM_MAP as _SYNONYM_MAP

    def keyword_search(self, text: str, top_k: int = 5) -> list[SectionResult]:
        """Simple keyword matching against section keywords and descriptions."""
        text_lower = text.lower()
        raw_words = set(text_lower.split())
        # Expand words with stems + synonyms (shared module)
        combined_stems = {**self._WORD_STEMS_BASE, **self._SYNONYM_MAP}
        words = set()
        for w in raw_words:
            words.add(w)
            if w in combined_stems:
                words.add(combined_stems[w])
        scores: dict[str, float] = {}

        # Check keyword index
        for word in words:
            if word in self._keyword_index:
                for sid in self._keyword_index[word]:
                    scores[sid] = scores.get(sid, 0) + 1.0

        # Check section titles and descriptions
        for sid, section in self._section_index.items():
            title_lower = section.title.lower()
            desc_lower = section.description.lower()
            for word in words:
                if word in title_lower:
                    scores[sid] = scores.get(sid, 0) + 2.0
                if word in desc_lower:
                    scores[sid] = scores.get(sid, 0) + 0.5

        if not scores:
            return []

        # Normalize scores
        max_score = max(scores.values())
        results = []
        sorted_sections = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        for sid, raw_score in sorted_sections[:top_k]:
            section = self._section_index.get(sid)
            if section is None:
                continue
            normalized = raw_score / max_score
            results.append(
                SectionResult(
                    section=section,
                    score=round(normalized, 3),
                    confidence=classify_rag_confidence(normalized),
                )
            )
        return results

    # ── RAG Pipeline ─────────────────────────────────────────────────────────

    def init_rag(self, persist_dir: str | None = None) -> None:
        """Initialize the RAG retriever from ChromaDB."""
        try:
            from langchain_community.vectorstores import Chroma
            from langchain_community.embeddings import HuggingFaceEmbeddings

            settings = get_settings()
            directory = persist_dir or settings.chroma_persist_dir

            embeddings = HuggingFaceEmbeddings(
                model_name=settings.embedding_model,
            )
            vectorstore = Chroma(
                persist_directory=directory,
                embedding_function=embeddings,
            )
            self._retriever = vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "k": settings.rag_top_k,
                    "score_threshold": settings.rag_score_threshold,
                },
            )
            logger.info("RAG retriever initialized from %s", directory)
        except Exception as e:
            logger.debug("RAG unavailable (keyword search active): %s", e)
            self._retriever = None

    def query_rag(self, text: str, top_k: int = 5) -> QueryResponse:
        """Query the RAG pipeline; fall back to keyword search if unavailable."""
        settings = get_settings()
        results: list[SectionResult] = []

        # Try RAG first
        if self._retriever is not None:
            try:
                docs = self._retriever.invoke(text)
                seen: set[str] = set()
                for doc in docs[:top_k]:
                    sid = doc.metadata.get("section_id", "")
                    if sid and sid not in seen:
                        seen.add(sid)
                        section = self._section_index.get(sid)
                        if section:
                            score = doc.metadata.get("score", 0.5)
                            results.append(
                                SectionResult(
                                    section=section,
                                    score=round(score, 3),
                                    confidence=classify_rag_confidence(score),
                                )
                            )
            except Exception as e:
                logger.warning("RAG query failed, falling back to keywords: %s", e)

        # Fall back to keyword search
        if not results:
            results = self.keyword_search(text, top_k)

        # Build response
        overall_confidence = "low"
        if results:
            best_score = max(r.score for r in results)
            overall_confidence = classify_rag_confidence(best_score)

        summary = self._build_summary(text, results)

        return QueryResponse(
            query=text,
            sections=results,
            summary=append_disclaimer(summary),
            disclaimer=settings.disclaimer_text,
            confidence=overall_confidence,
        )

    def _build_summary(self, query: str, results: list[SectionResult]) -> str:
        """Build a human-readable summary from search results."""
        if not results:
            return (
                "I could not find specific legal sections matching your query. "
                "Please try the Guided Legal Help feature for step-by-step assistance, "
                "or rephrase your question with more specific details."
            )

        lines = [f"Based on your query about \"{query}\", here are the relevant legal sections:\n"]
        for i, result in enumerate(results, 1):
            s = result.section
            lines.append(f"**{i}. {s.section_id} — {s.title}** (Act: {s.act})")
            lines.append(f"   {s.description[:200]}...")
            if s.punishment:
                lines.append(f"   *Punishment*: {s.punishment}")
            bailable = "Yes" if s.bailable else "No"
            cognizable = "Yes" if s.cognizable else "No"
            lines.append(f"   *Bailable*: {bailable} | *Cognizable*: {cognizable}")

            # Show cross-reference
            corresponding = self.get_corresponding_section(s.section_id)
            if corresponding:
                direction = "replaces" if s.section_id.startswith("BNS") else "replaced by"
                lines.append(
                    f"   *{direction.title()}*: {corresponding.section_id} — {corresponding.title}"
                )
            lines.append("")

        return "\n".join(lines)


# Thread-safe singleton via lru_cache
@lru_cache(maxsize=1)
def get_legal_service() -> LegalService:
    """Get or create the LegalService singleton (thread-safe)."""
    return LegalService()
