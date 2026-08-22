"""Hybrid retriever -- RRF fusion of semantic (ChromaDB) + keyword (BM25)."""

from __future__ import annotations

import logging

from backend.config import RAG_TOP_K
from backend.legal.bm25_index import BM25Index
from backend.legal.corpus_loader import CorpusLoader
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
        self._civic_records = [record.to_dict() for record in CorpusLoader.load_civic_records()]
        self._civic_bm25 = BM25Index(self._civic_records)

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

    def retrieve_civic(
        self,
        query: str,
        domain: str | None = None,
        jurisdiction: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """Retrieve civic records without applying criminal query expansion.

        The current civic corpus is intentionally small and source-controlled,
        so BM25 is deterministic and every result retains its provenance.  The
        score is lexical relevance, not legal certainty or eligibility.
        """
        records = self._civic_records
        if domain:
            records = [record for record in records if record["domain"] == domain]
        records = self.filter_civic_records(records, jurisdiction)
        index = self._civic_bm25 if records is self._civic_records else BM25Index(records)
        results = index.search(query, top_k=top_k)

        # General India and State/UT-dependent orientation records remain useful
        # after a State is supplied; they do not assert a State-specific rule.
        output: list[dict] = []
        for result in results:
            raw_score = float(result.pop("bm25_score", 0.0))
            result["score"] = round(raw_score / (raw_score + 1.0), 3)
            result["query_jurisdiction"] = jurisdiction
            output.append(result)
        return output

    @staticmethod
    def filter_civic_records(
        records: list[dict], jurisdiction: str | None
    ) -> list[dict]:
        """Keep national/orientation records and only the requested local rules.

        A concrete State/UT record is never returned for a different or missing
        jurisdiction.  Generic ``State/UT-specific`` warnings remain available
        because they contain no local substantive rule.
        """
        general_prefixes = ("india", "state/ut-specific")
        if not jurisdiction:
            return [
                record
                for record in records
                if record.get("jurisdiction", "").casefold().startswith(general_prefixes)
            ]
        requested = jurisdiction.casefold().strip()
        return [
            record
            for record in records
            if record.get("jurisdiction", "").casefold().startswith(general_prefixes)
            or requested in record.get("jurisdiction", "").casefold()
        ]
