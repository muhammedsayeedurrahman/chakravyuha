"""BM25 keyword search index for legal sections."""

from __future__ import annotations

import math
import re
from collections import Counter


class BM25Index:
    """Okapi BM25 keyword search over legal section corpus."""

    def __init__(self, sections: list[dict]):
        self._sections = sections
        self._corpus: list[list[str]] = []
        self._avgdl = 0.0
        self._idf: dict[str, float] = {}
        self._build_index()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase, split on non-word chars, drop short tokens."""
        return [t for t in re.findall(r"\w+", text.lower()) if len(t) > 1]

    def _build_index(self) -> None:
        for section in self._sections:
            doc_text = " ".join([
                section.get("title", ""),
                section.get("description", ""),
                " ".join(section.get("keywords", [])),
            ])
            self._corpus.append(self._tokenize(doc_text))

        n = len(self._corpus)
        if n == 0:
            return

        self._avgdl = sum(len(d) for d in self._corpus) / n

        # Document frequency per term
        df: Counter = Counter()
        for doc in self._corpus:
            for term in set(doc):
                df[term] += 1

        self._idf = {
            term: math.log((n - freq + 0.5) / (freq + 0.5) + 1)
            for term, freq in df.items()
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> list[dict]:
        """Search the index with BM25 scoring.

        Args:
            query: Natural-language search string.
            top_k: Max results to return.
            k1: Term-frequency saturation parameter.
            b: Length normalisation parameter.

        Returns:
            List of section dicts augmented with ``bm25_score``.
        """
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        scored: list[tuple[int, float]] = []

        for i, doc in enumerate(self._corpus):
            score = 0.0
            doc_len = len(doc)
            tf = Counter(doc)

            for term in query_terms:
                if term not in self._idf:
                    continue
                term_freq = tf.get(term, 0)
                if term_freq == 0:
                    continue
                idf = self._idf[term]
                numerator = term_freq * (k1 + 1)
                denominator = term_freq + k1 * (1 - b + b * doc_len / max(self._avgdl, 1))
                score += idf * numerator / denominator

            if score > 0:
                scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, bm25_score in scored[:top_k]:
            section = self._sections[idx]
            results.append({**section, "bm25_score": round(bm25_score, 4)})

        return results
