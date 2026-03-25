"""Hybrid retriever -- RRF fusion of semantic (ChromaDB) + keyword (BM25)."""

from __future__ import annotations

import logging

from backend.config import RAG_TOP_K
from backend.legal.bm25_index import BM25Index
from backend.legal.rag import LegalRAG
from backend.legal.sections import SectionLookup

logger = logging.getLogger("chakravyuha")


class HybridRetriever:
    """Fuse semantic search (ChromaDB) and keyword search (BM25) using RRF.

    Reciprocal Rank Fusion:  ``score(d) = sum( 1 / (k + rank_i(d)) )``
    over each ranking system *i*.
    """

    def __init__(self) -> None:
        self._rag = LegalRAG()
        self._section_lookup = SectionLookup()
        all_sections = list(self._section_lookup._bns) + list(self._section_lookup._ipc)
        self._bm25 = BM25Index(all_sections)

    def retrieve(
        self, query: str, top_k: int = RAG_TOP_K, rrf_k: int = 60
    ) -> list[dict]:
        """Retrieve sections using hybrid RRF fusion.

        Args:
            query: Natural-language question.
            top_k: Number of results to return.
            rrf_k: RRF constant (higher = less aggressive rank weighting).

        Returns:
            List of section dicts augmented with ``rrf_score``.
        """
        semantic_results = self._rag.retrieve_sections(query, top_k=top_k * 2)
        bm25_results = self._bm25.search(query, top_k=top_k * 2)

        rrf_scores: dict[str, tuple[float, dict]] = {}

        for rank, section in enumerate(semantic_results):
            sid = section["section_id"]
            rrf_score = 1.0 / (rrf_k + rank + 1)
            if sid in rrf_scores:
                prev_score, prev_data = rrf_scores[sid]
                rrf_scores[sid] = (prev_score + rrf_score, prev_data)
            else:
                rrf_scores[sid] = (rrf_score, section)

        for rank, section in enumerate(bm25_results):
            sid = section["section_id"]
            rrf_score = 1.0 / (rrf_k + rank + 1)
            if sid in rrf_scores:
                prev_score, prev_data = rrf_scores[sid]
                rrf_scores[sid] = (prev_score + rrf_score, prev_data)
            else:
                # Build a normalised section dict from BM25 result
                section_data = {
                    "section_id": sid,
                    "title": section.get("title", ""),
                    "law": section.get("law", ""),
                    "description": section.get("description", ""),
                    "score": 0.0,
                    "punishment": section.get("punishment", ""),
                    "cognizable": section.get("cognizable", ""),
                    "bailable": section.get("bailable", ""),
                }
                rrf_scores[sid] = (rrf_score, section_data)

        ranked = sorted(rrf_scores.values(), key=lambda x: x[0], reverse=True)

        results = []
        for rrf_score, section_data in ranked[:top_k]:
            results.append({**section_data, "rrf_score": round(rrf_score, 4)})

        return results
