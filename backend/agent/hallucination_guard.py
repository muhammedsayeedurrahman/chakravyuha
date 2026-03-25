"""Hallucination guard -- verify LLM output only references provided sections."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("chakravyuha")

_SECTION_PATTERN = re.compile(
    r"\b(BNS|IPC)\s*[-\u2013]?\s*(\d+[A-Za-z]*)\b", re.IGNORECASE
)

# Year references that should NOT be treated as section IDs
_LAW_YEARS = {"1860", "1861", "1872", "1973", "2023", "2024"}


def extract_cited_sections(response: str) -> set[str]:
    """Extract all section IDs (e.g. ``BNS-100``) mentioned in *response*.

    Excludes law-year references like "IPC 1860" or "BNS 2023".
    """
    cited: set[str] = set()
    for match in _SECTION_PATTERN.finditer(response):
        law = match.group(1).upper()
        num = match.group(2)
        if num in _LAW_YEARS:
            continue
        cited.add(f"{law}-{num}")
    return cited


def check_hallucination(response: str, provided_sections: list[dict]) -> dict:
    """Check whether *response* references sections not in *provided_sections*.

    Returns:
        Dict with ``is_valid``, ``hallucinated_sections``, ``cited_sections``,
        and ``provided_ids``.
    """
    provided_ids = {s.get("section_id", "") for s in provided_sections}
    cited = extract_cited_sections(response)
    hallucinated = cited - provided_ids

    return {
        "is_valid": len(hallucinated) == 0,
        "hallucinated_sections": hallucinated,
        "cited_sections": cited,
        "provided_ids": provided_ids,
    }


def sanitize_response(response: str, provided_sections: list[dict]) -> str:
    """Remove or flag hallucinated section references.

    If the LLM invented section numbers that were not in the provided context,
    those references are replaced with a ``[section removed]`` marker and a
    short note is appended.
    """
    check = check_hallucination(response, provided_sections)

    if check["is_valid"]:
        return response

    logger.warning(
        "Hallucination detected! LLM cited sections not in context: %s",
        check["hallucinated_sections"],
    )

    sanitized = response
    for section_id in check["hallucinated_sections"]:
        law, num = section_id.split("-", 1)
        # Build a flexible regex that matches "BNS 100", "BNS-100", "BNS\u2013100"
        flexible = rf"\b{re.escape(law)}\s*[-\u2013]?\s*{re.escape(num)}\b"
        sanitized = re.sub(flexible, "[section removed]", sanitized, flags=re.IGNORECASE)

    sanitized += (
        "\n\n*Note: Some section references were removed because they could not "
        "be verified against our database. Please consult a lawyer for accurate "
        "section numbers.*"
    )

    return sanitized
