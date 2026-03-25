"""Query expansion -- synonym injection + HyDE (Hypothetical Document Embeddings)."""

from __future__ import annotations

import logging

logger = logging.getLogger("chakravyuha")

# Legal synonym map for Indian criminal law
LEGAL_SYNONYMS: dict[str, list[str]] = {
    "theft": ["stealing", "larceny", "robbery", "burglary", "shoplifting", "chori"],
    "murder": ["killing", "homicide", "manslaughter", "culpable homicide", "hatya"],
    "assault": ["attack", "beating", "battery", "hitting", "punch", "marpeet"],
    "rape": ["sexual assault", "sexual offence", "molestation", "balatkar"],
    "kidnap": ["abduction", "kidnapping", "hostage", "forced taking", "agharan"],
    "fraud": ["cheating", "deception", "scam", "forgery", "misrepresentation", "dhokha"],
    "bribe": ["corruption", "bribery", "kickback", "gratification", "rishvat"],
    "accident": ["crash", "collision", "road accident", "hit and run", "durghatna"],
    "domestic violence": ["wife beating", "cruelty by husband", "dowry harassment", "gharelu hinsa"],
    "defamation": ["slander", "libel", "character assassination", "maan hani"],
    "trespass": ["encroachment", "unlawful entry", "intrusion", "atikraman"],
    "extortion": ["blackmail", "threatening", "ransom", "vasuli"],
    "dowry": ["dowry death", "dowry demand", "bride burning", "dahej"],
    "cybercrime": ["hacking", "online fraud", "identity theft", "phishing"],
}


def expand_with_synonyms(query: str) -> str:
    """Expand a query by injecting relevant legal synonyms.

    Looks for known legal terms in *query* and appends close synonyms that
    are not already present.  Returns the enriched query string.
    """
    query_lower = query.lower()
    expansions: list[str] = []

    for key, synonyms in LEGAL_SYNONYMS.items():
        if key in query_lower:
            for syn in synonyms:
                if syn not in query_lower:
                    expansions.append(syn)
        else:
            for syn in synonyms:
                if syn in query_lower:
                    expansions.append(key)
                    break

    if expansions:
        return f"{query} ({' '.join(expansions[:5])})"
    return query


def generate_hyde_query(query: str) -> str:
    """Generate a Hypothetical Document Embedding query for improved retrieval.

    Creates a short hypothetical legal-section description whose embedding is
    closer to the real matching section than the raw user query.
    """
    try:
        from backend.config import LLM_ENABLED

        if LLM_ENABLED:
            from backend.services.llm import get_llm_service

            llm = get_llm_service()
            if llm.is_available:
                hyde_prompt = (
                    f"Write a 2-3 sentence hypothetical Indian criminal law section "
                    f"description that would answer: '{query}'. "
                    f"Include likely offence type and punishment range. "
                    f"Do NOT use real section numbers."
                )
                for provider in llm._providers:
                    try:
                        result = provider.generate(hyde_prompt, [], "en-IN")
                        if result:
                            return result
                    except Exception:
                        continue
    except Exception as exc:
        logger.debug("HyDE LLM generation failed: %s", exc)

    # Template-based fallback
    return (
        f"This section deals with offences related to {query}. "
        f"Under the Bharatiya Nyaya Sanhita (BNS) 2023, this offence is "
        f"punishable with imprisonment and/or fine."
    )


class QueryExpander:
    """Expands user queries for improved retrieval via synonyms and HyDE."""

    def expand(self, query: str, use_hyde: bool = False) -> list[str]:
        """Return a list of expanded query variants.

        Args:
            query: Original user query.
            use_hyde: Whether to include a HyDE expansion (slower, uses LLM).

        Returns:
            List of query strings: ``[original, synonym-expanded, (optional) hyde]``.
        """
        variants = [query]

        expanded = expand_with_synonyms(query)
        if expanded != query:
            variants.append(expanded)

        if use_hyde:
            hyde = generate_hyde_query(query)
            if hyde:
                variants.append(hyde)

        return variants
