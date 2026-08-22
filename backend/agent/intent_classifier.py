"""Intent classifier -- regex-first, LLM-fallback intent detection."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("chakravyuha")

# ── Intent labels ────────────────────────────────────────────────────────────
INTENT_LEGAL_QUERY = "legal_query"
INTENT_SECTION_LOOKUP = "section_lookup"
INTENT_GUIDED_FLOW = "guided_flow"
INTENT_GREETING = "greeting"
INTENT_FOLLOWUP = "followup"
INTENT_ESCALATION = "escalation"
INTENT_GENERAL = "general"
INTENT_COMPLAINT_DRAFT = "complaint_draft"
INTENT_RTI = "rti"
INTENT_SCHEME_ELIGIBILITY = "scheme_eligibility"
INTENT_CPGRAMS = "cpgrams"
INTENT_CIVIC_QUERY = "civic_query"


@dataclass(frozen=True)
class IntentResult:
    """Immutable classification result."""

    intent: str
    confidence: float
    method: str  # "regex" or "llm"
    entities: dict = field(default_factory=dict)


# ── Regex patterns ───────────────────────────────────────────────────────────
_SECTION_PATTERN = re.compile(
    r"\b(BNS|IPC)\s*[-\u2013]?\s*(\d+[A-Za-z]*)\b", re.IGNORECASE
)

_GREETING_PATTERNS = [
    re.compile(
        r"^\s*(hi|hello|hey|namaste|namaskar|good\s*(morning|afternoon|evening))\b",
        re.IGNORECASE,
    ),
]

_ESCALATION_PATTERNS = [
    re.compile(
        r"\b(murder|kill|rape|sexual assault|kidnap|abduct|"
        r"suicide|self.?harm|bomb|gun|acid attack|death threat|"
        r"domestic violence|imminent danger|life in danger)",
        re.IGNORECASE,
    ),
]

_GUIDED_PATTERNS = [
    re.compile(
        r"\b(guide|guided|step.?by.?step|help me decide|what should i do|what happened)\b",
        re.IGNORECASE,
    ),
]

_RTI_PATTERNS = [
    re.compile(
        r"\b(rti|right\s+to\s+information|public\s+authority\s+records?|"
        r"file\s+(?:an?\s+)?information\s+request)\b",
        re.IGNORECASE,
    ),
]

_SCHEME_PATTERNS = [
    re.compile(
        r"\b(government\s+schemes?|welfare\s+schemes?|scheme\s+eligib\w*|"
        r"eligible\s+for\s+[^?.!]*(?:scheme|yojana)|"
        r"(?:find|search|discover|which|what)\s+(?:government\s+)?schemes?|"
        r"yojana|pm[-\s]?kisan|pm[-\s]?sym|atal\s+pension\s+yojana)\b",
        re.IGNORECASE,
    ),
]

_CPGRAMS_PATTERNS = [
    re.compile(
        r"\b(cpgrams|centrali[sz]ed\s+public\s+grievance|"
        r"public\s+grievance\s+portal|government\s+grievance)\b",
        re.IGNORECASE,
    ),
]

_CIVIC_PATTERNS = [
    re.compile(
        r"\b(civic\s+issue|municipal(?:ity)?\s+(?:service|complaint)|"
        r"panchayat\s+service|potholes?|street\s*lights?|garbage\s+collection|"
        r"public\s+road\s+repair|water\s+supply\s+complaint)\b",
        re.IGNORECASE,
    ),
]

_COMPLAINT_DRAFT_PATTERNS = [
    re.compile(
        r"\b(draft|write|generate|create|prepare|file)\s+"
        r"(a\s+)?(?:(?:police|consumer|formal|written)\s+)?"
        r"(complaint|fir|legal\s+notice|petition|notice)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(complaint|fir|legal\s+notice|petition)\s+"
        r"(draft|write|generate|create|prepare|file|likhna|banao)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(i\s+want\s+to\s+file|help\s+me\s+file|help\s+me\s+draft|"
        r"mujhe\s+likhna|shikayat\s+likhna)\b",
        re.IGNORECASE,
    ),
]

_FOLLOWUP_PATTERNS = [
    re.compile(
        r"^\s*(what about|and also|tell me more|explain|elaborate|can you clarify)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*(yes|no|okay|ok|thanks|thank you)\s*$", re.IGNORECASE),
]


# ── Public API ───────────────────────────────────────────────────────────────


def classify_intent(
    query: str, conversation_history: list[dict] | None = None
) -> IntentResult:
    """Classify user intent using regex rules first, LLM fallback for ambiguous cases.

    Args:
        query: Raw user input.
        conversation_history: Previous turns (used to detect follow-ups).

    Returns:
        An ``IntentResult`` with the classified intent, confidence, and method.
    """
    q = query.strip()

    # 1. Direct section reference
    section_match = _SECTION_PATTERN.search(q)
    if section_match:
        law = section_match.group(1).upper()
        num = section_match.group(2)
        return IntentResult(
            intent=INTENT_SECTION_LOOKUP,
            confidence=0.95,
            method="regex",
            entities={"section_id": f"{law}-{num}"},
        )

    # 2. Escalation (high priority)
    for pat in _ESCALATION_PATTERNS:
        if pat.search(q):
            return IntentResult(
                intent=INTENT_ESCALATION, confidence=0.9, method="regex"
            )

    # 3. Civic workflows (before generic complaint drafting)
    civic_patterns = (
        (_RTI_PATTERNS, INTENT_RTI, "rti"),
        (_SCHEME_PATTERNS, INTENT_SCHEME_ELIGIBILITY, "scheme_eligibility"),
        (_CPGRAMS_PATTERNS, INTENT_CPGRAMS, "cpgrams"),
        (_CIVIC_PATTERNS, INTENT_CIVIC_QUERY, "civic"),
    )
    for patterns, intent_name, journey in civic_patterns:
        if any(pattern.search(q) for pattern in patterns):
            return IntentResult(
                intent=intent_name,
                confidence=0.9,
                method="regex",
                entities={"journey": journey},
            )

    # 4. Complaint drafting request
    for pat in _COMPLAINT_DRAFT_PATTERNS:
        if pat.search(q):
            return IntentResult(
                intent=INTENT_COMPLAINT_DRAFT, confidence=0.9, method="regex"
            )

    # 5. Greeting
    for pat in _GREETING_PATTERNS:
        if pat.search(q):
            return IntentResult(
                intent=INTENT_GREETING, confidence=0.9, method="regex"
            )

    # 6. Follow-up (only when there is conversation history)
    if conversation_history:
        for pat in _FOLLOWUP_PATTERNS:
            if pat.search(q):
                return IntentResult(
                    intent=INTENT_FOLLOWUP, confidence=0.8, method="regex"
                )

    # 7. Guided-flow request
    for pat in _GUIDED_PATTERNS:
        if pat.search(q):
            return IntentResult(
                intent=INTENT_GUIDED_FLOW, confidence=0.7, method="regex"
            )

    # 8. LLM fallback
    llm_result = _llm_classify(q)
    if llm_result:
        return llm_result

    # 9. Default: treat as legal query
    return IntentResult(intent=INTENT_LEGAL_QUERY, confidence=0.6, method="regex")


# ── Private helpers ──────────────────────────────────────────────────────────


def _llm_classify(query: str) -> IntentResult | None:
    """Use an LLM provider for intent classification (slow path)."""
    try:
        from backend.config import LLM_ENABLED

        if not LLM_ENABLED:
            return None

        from backend.services.llm import get_llm_service

        llm = get_llm_service()
        if not llm.is_available:
            return None

        prompt = (
            "Classify this user message into exactly ONE category. "
            "Reply with ONLY the category name.\n\n"
            "Categories:\n"
            "- legal_query (asking about law, crime, punishment, rights)\n"
            "- section_lookup (asking about a specific legal section)\n"
            "- complaint_draft (wants to draft/file a complaint, FIR, or legal notice)\n"
            "- rti (wants public records or an RTI application)\n"
            "- scheme_eligibility (asks to find or check a government scheme)\n"
            "- cpgrams (wants help with a government grievance on CPGRAMS)\n"
            "- civic_query (municipal or other civic-service issue)\n"
            "- greeting (hello, hi, namaste)\n"
            "- followup (continuing a previous conversation)\n"
            "- general (not related to law)\n\n"
            f'Message: "{query}"\n\nCategory:'
        )

        for provider in llm._providers:
            try:
                result = provider.generate(prompt, [], "en-IN")
                if result:
                    category = result.strip().lower()
                    valid = {
                        INTENT_LEGAL_QUERY,
                        INTENT_SECTION_LOOKUP,
                        INTENT_COMPLAINT_DRAFT,
                        INTENT_RTI,
                        INTENT_SCHEME_ELIGIBILITY,
                        INTENT_CPGRAMS,
                        INTENT_CIVIC_QUERY,
                        INTENT_GREETING,
                        INTENT_FOLLOWUP,
                        INTENT_GENERAL,
                    }
                    if category in valid:
                        return IntentResult(
                            intent=category, confidence=0.75, method="llm"
                        )
                    break
            except Exception:
                continue
    except Exception as exc:
        logger.debug("LLM intent classification failed: %s", exc)

    return None
