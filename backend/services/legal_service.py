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
    CivicKnowledgeRecord,
    CivicLegalQueryRequest,
    CivicLegalQueryResponse,
    ConfidenceLevel,
    GuidedFlowState,
    GuidedFlowStep,
    GuidedOption,
    JurisdictionCompleteness,
    LegalSection,
    QueryResponse,
    SectionResult,
    KnowledgeStatus,
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
        self._civic_retriever = None
        logger.info(
            "LegalService initialized: %d sections, %d keywords",
            len(self._section_index),
            len(self._keyword_index),
        )

    # ── Guided Flow (Deterministic — 100% accuracy) ──────────────────────────

    @staticmethod
    def _canonical_guided_node(node_key: str | None) -> str:
        """Accept the legacy ``root`` value while using the real tree root."""
        return "start" if not node_key or node_key == "root" else node_key

    def get_guided_step(self, state: GuidedFlowState) -> GuidedFlowStep:
        """Return the current guided flow step based on state."""
        node_key = self._canonical_guided_node(state.current_node)
        node = self._guided_tree.get(node_key)

        if node is None:
            return GuidedFlowStep(
                node_key=node_key,
                question="Sorry, this path is not available. Please start over.",
                is_leaf=True,
            )

        if node.get("terminal"):
            section_ids = [*node.get("sections", []), *node.get("ipc_sections", [])]
            matched = [
                self._section_index[section_id]
                for section_id in dict.fromkeys(section_ids)
                if section_id in self._section_index
            ]
            return GuidedFlowStep(
                node_key=node_key,
                question=node.get("summary", "Relevant legal information"),
                question_hi=node.get("summary_hi", ""),
                is_leaf=True,
                matched_sections=matched,
                severity=node.get("severity") or ("high" if node.get("escalation") else None),
                summary=node.get("summary"),
                summary_hi=node.get("summary_hi"),
                next_steps=node.get("next_steps", []),
            )

        if node.get("type") in {"free_text", "handoff"}:
            prompt = node.get("prompt", "Please describe your issue.")
            return GuidedFlowStep(
                node_key=node_key,
                question=prompt,
                question_hi=node.get("prompt_hi", ""),
                is_leaf=False,
                type=node.get("type"),
                prompt=prompt,
                prompt_hi=node.get("prompt_hi"),
                handler=node.get("handler"),
                journey=node.get("journey"),
                summary=node.get("summary"),
                summary_hi=node.get("summary_hi"),
                next_steps=node.get("next_steps", []),
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
        node_key = self._canonical_guided_node(state.current_node)
        node = self._guided_tree.get(node_key)
        if node is None:
            return GuidedFlowStep(
                node_key=node_key,
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
            answer_lower = answer.strip().lower()
            for opt in node.get("options", []):
                if answer_lower and answer_lower in opt.get("label", "").lower():
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
                node_key=node_key,
                question="Here are the relevant legal sections:",
                is_leaf=True,
                matched_sections=matched,
                severity=selected.get("severity"),
            )

        # Navigate to next node
        next_key = selected.get("next", "start")
        new_state = GuidedFlowState(
            current_node=next_key,
            path=[*state.path, node_key],
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
        lines.append(
            "Verification note: legacy BNS/IPC summaries in this repository must be "
            "checked against the current official statute before reliance.\n"
        )
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

    # -- Provenance-aware civic/legal retrieval ------------------------------

    def query_civic(self, request: CivicLegalQueryRequest) -> CivicLegalQueryResponse:
        """Query consumer, tenant, or labour records without criminal templates."""
        if self._civic_retriever is None:
            from backend.legal.adaptive_rag import AdaptiveRAG

            self._civic_retriever = AdaptiveRAG()

        state = next(
            (
                value.strip()
                for value in (request.state, request.jurisdiction)
                if JurisdictionCompleteness.is_known_value(value)
            ),
            None,
        )
        jurisdiction = JurisdictionCompleteness.from_values(
            state=state,
            district=request.district,
            city=request.city,
            locality=request.locality,
            authority=request.authority_hint,
        )
        domain = request.domain or self._infer_civic_domain(request.query)
        retrieval = self._civic_retriever.retrieve_civic(
            request.query,
            domain=domain,
            jurisdiction=state,
            top_k=request.top_k,
        )
        results = [CivicKnowledgeRecord(**record) for record in retrieval["records"]]
        missing: list[str] = []

        if domain == "tenant" and not jurisdiction.state_known:
            missing.append("State or Union Territory where the rented premises are located")
            confidence = ConfidenceLevel.REQUIRES_JURISDICTION
            status = KnowledgeStatus.REQUIRES_JURISDICTION
        elif not results:
            confidence = ConfidenceLevel.LOW
            status = KnowledgeStatus.UNAVAILABLE
        else:
            confidence = ConfidenceLevel.MEDIUM
            status = (
                KnowledgeStatus.REQUIRES_VERIFICATION
                if any(result.status != KnowledgeStatus.VERIFIED for result in results)
                else KnowledgeStatus.VERIFIED
            )

        next_steps = self._build_civic_next_steps(
            domain,
            results,
            jurisdiction,
            state=state,
            city=request.city,
        )
        answer = self._build_civic_answer(domain, results, missing, next_steps)
        return CivicLegalQueryResponse(
            query=request.query,
            domain=domain,
            jurisdiction=state,
            jurisdiction_completeness=jurisdiction,
            confidence=confidence,
            status=status,
            results=results,
            missing_information=missing,
            next_steps=next_steps,
            answer=answer,
            disclaimer=(
                "This response provides source-linked legal information, not legal advice. "
                "Coverage, jurisdiction, current rules, and the facts must be verified before action."
            ),
        )

    @staticmethod
    def _infer_civic_domain(query: str) -> str | None:
        from backend.agent.intent_classifier import infer_rights_domain

        return infer_rights_domain(query)

    @staticmethod
    def _build_civic_answer(
        domain: str | None,
        results: list[CivicKnowledgeRecord],
        missing: list[str],
        next_steps: list[str],
    ) -> str:
        if not results:
            if missing:
                return f"No verified source record matched this issue. Provide: {', '.join(missing)}."
            return (
                "No verified source record matched this issue. Clarify whether it is a "
                "consumer, tenant, or workplace matter and add more factual detail."
            )
        lead = results[0]
        parts = [lead.summary]
        if missing:
            parts.append(f"Before relying on a rule, provide: {', '.join(missing)}.")
        if next_steps:
            parts.append(f"Practical next step: {next_steps[0]}")
        parts.append(f"Primary source: {lead.source}.")
        return " ".join(parts)

    @staticmethod
    def _build_civic_next_steps(
        domain: str | None,
        results: list[CivicKnowledgeRecord],
        jurisdiction: JurisdictionCompleteness,
        *,
        state: str | None,
        city: str | None,
    ) -> list[str]:
        steps: list[str] = []
        if domain == "tenant":
            city_label = (city or "").strip()
            if jurisdiction.state_known and jurisdiction.city_known:
                steps.append(
                    f"{state} and {city_label} identified; verify the locally applicable "
                    "tenancy rule and forum before relying on it."
                )
            elif jurisdiction.state_known:
                steps.append(
                    f"{state} identified; city/local jurisdiction may still be required "
                    "before relying on a tenancy rule."
                )
            else:
                steps.append(
                    "Provide the State or Union Territory where the rented premises are "
                    "located; city/local jurisdiction may also be required."
                )

        for result in results:
            for step in result.guidance:
                if (
                    domain == "tenant"
                    and "provide the state or union territory" in step.casefold()
                ):
                    continue
                if step not in steps:
                    steps.append(step)
        return steps


# Thread-safe singleton via lru_cache
@lru_cache(maxsize=1)
def get_legal_service() -> LegalService:
    """Get or create the LegalService singleton (thread-safe)."""
    return LegalService()
