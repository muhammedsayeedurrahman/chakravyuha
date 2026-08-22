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
INTENT_INFORMATION_REQUEST = "information_request"
INTENT_GOVERNMENT_SERVICE_GRIEVANCE = "government_service_grievance"
INTENT_SCHEME_ELIGIBILITY = "scheme_eligibility"
INTENT_RIGHTS_GUIDANCE = "rights_guidance"
INTENT_CRIMINAL_INCIDENT = "criminal_incident"

# Internal workflow navigation is allowed only for deterministic, high-confidence
# top-level matches.  This never authorizes an external filing or submission.
AUTOMATIC_CIVIC_HANDOFF_CONFIDENCE = 0.8

# Compatibility names used by older callers.  They intentionally resolve to
# the canonical top-level intents so there is still only one routing model.
INTENT_RTI = INTENT_INFORMATION_REQUEST
INTENT_CPGRAMS = INTENT_GOVERNMENT_SERVICE_GRIEVANCE
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

_IMMEDIATE_DANGER_PATTERN = re.compile(
    r"\b(?:(?:my|our|his|her|their|someone(?:'s)?)\s+life\s+is\s+in\s+danger|"
    r"i\s+am\s+in\s+imminent\s+danger|i\s+(?:am\s+)?(?:suicidal|about\s+to\s+"
    r"harm\s+myself)|i\s+want\s+to\s+kill\s+myself)\b",
    re.IGNORECASE,
)

_GUIDED_PATTERNS = [
    re.compile(
        r"\b(guide|guided|step.?by.?step|help me decide|what should i do|what happened)\b",
        re.IGNORECASE,
    ),
]

_EXPLICIT_RTI_PATTERNS = [
    re.compile(
        r"\b(rti|right\s+to\s+information|public\s+authority\s+records?|"
        r"file\s+(?:an?\s+)?information\s+request)\b",
        re.IGNORECASE,
    ),
]

_INFORMATION_ACCESS_SIGNAL = re.compile(
    r"\b(?:want|need|seek|request|obtain|get|find|locate|give|provide|show|inspect|access|"
    r"copies?|copy|details?\s+of|information\s+about|how\s+much)\b",
    re.IGNORECASE,
)

_PUBLIC_RECORD_SIGNAL = re.compile(
    r"\b(?:official\s+files?|file\s+notings?|work[ -]?orders?|tenders?|"
    r"documents?\s+(?:showing|recording|explaining)|"
    r"contractor\s+(?:details?|information)|"
    r"inspection\s+(?:reports?|records?)|expenditure|amounts?\s+sanctioned|"
    r"sanctioned\s+amounts?|money\s+(?:sanctioned|spent)|utilisation\s+certificates?|"
    r"measurement\s+books?)\b",
    re.IGNORECASE,
)

_GENERIC_RECORD_SIGNAL = re.compile(
    r"\b(?:records?|documents?|contracts?|case\s+files?|certified\s+copies?)\b",
    re.IGNORECASE,
)

_PUBLIC_CONTEXT_SIGNAL = re.compile(
    r"\b(?:government|public\s+(?:authority|office|department|road|works|service)|"
    r"municipal(?:ity)?|panchayat|ministry|department|official|police|court|"
    r"ipc|bns|civic|roads?|potholes?)\b",
    re.IGNORECASE,
)

_INFORMATION_QUESTION_SIGNAL = re.compile(
    r"(?:\b(?:who|which)\s+(?:was|is)\s+(?:the\s+)?contractor\b|"
    r"\b(?:what|which)\s+(?:was|is)\s+(?:the\s+)?(?:sanctioned\s+amount|"
    r"amount\s+sanctioned)\b|"
    r"\b(?:what|which)\s+(?:(?:was|is|are|were)\s+)?(?:the\s+)?(?:"
    r"work[ -]?orders?|inspection\s+(?:records?|reports?)|"
    r"contractor\s+(?:information|details?))\b|"
    r"\bwhat\s+(?:do|does|did)\s+(?:the\s+)?inspection\s+(?:record|report)s?\b|"
    r"\b(?:what|which)\s+[^?.!]{0,60}\b(?:records?|documents?)\s+"
    r"(?:are\s+|were\s+)?(?:available|held|maintained|exist)\b)",
    re.IGNORECASE,
)

_SCHEME_PATTERNS = [
    re.compile(
        r"\b(government\s+schemes?|welfare\s+schemes?|scheme\s+eligib\w*|"
        r"eligible\s+for\s+[^?.!]*(?:scheme|yojana)|"
        r"(?:find|search|discover|which|what)\s+(?:government\s+)?schemes?|"
        r"yojana|pm[-\s]?kisan|pm[-\s]?sym|atal\s+pension\s+yojana)\b",
        re.IGNORECASE,
    ),
]

_SCHEME_ELIGIBILITY_ACTION_PATTERNS = [
    re.compile(
        r"\b(?:scheme\s+eligib\w*|eligib\w*\s+for\s+[^?.!]*(?:scheme|yojana)|"
        r"(?:find|search|discover|which|what)\s+(?:government\s+)?schemes?|"
        r"looking\s+for\s+(?:government\s+)?schemes?|"
        r"(?:am|are|is|can|could|would)\s+[^?.!]{0,60}\beligib\w*)\b",
        re.IGNORECASE,
    ),
]

_APPLICATION_DOCUMENT_REQUIREMENT_SIGNAL = re.compile(
    r"\b(?:documents?|papers?)\b.{0,60}\b(?:need(?:ed)?|required|requirements?|"
    r"apply|applying|application)\b|\b(?:apply|applying|application)\b.{0,60}"
    r"\b(?:documents?|papers?)\b",
    re.IGNORECASE,
)

_CPGRAMS_PATTERNS = [
    re.compile(
        r"\b(cpgrams|centrali[sz]ed\s+public\s+grievance|"
        r"public\s+grievance\s+portal|government\s+grievance)\b",
        re.IGNORECASE,
    ),
]

_GOVERNMENT_SERVICE_PATTERNS = [
    re.compile(
        r"\b(?:civic\s+issue|municipal(?:ity)?\s+complaint|"
        r"water\s+supply\s+complaint|public\s+service\s+complaint)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:there\s+(?:is|are)|we\s+have)\b.{0,60}\b(?:potholes?|"
        r"broken\s+street\s*lights?|uncollected\s+garbage)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:roads?|streets?)\b.{0,80}\b(?:dangerous\s+)?(?:potholes?|"
        r"badly\s+damaged|broken|flooded|blocked)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:road|street|potholes?|drain|sewer|street\s*lights?|garbage|"
        r"sanitation|water\s+supply|electricity|ration(?:\s+(?:card|shop))?|"
        r"pension|certificate|passport|aadhaar|voter\s+id|driving\s+licen[cs]e|"
        r"land\s+record|tax\s+refund|government\s+(?:service|application|school|"
        r"hospital)|public\s+(?:service|transport|hospital)|municipal\s+road)\b"
        r".{0,140}\b(?:repair|fix|restore|resolve|redress|pending|delay(?:ed)?|"
        r"complain(?:ed|t)?|ignored|no\s+action|nothing\s+happened|not\s+(?:been\s+)?"
        r"(?:repaired|working|received|issued|paid|moved)|unpaid|refused|denied|failed)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:repair|fix|restore|resolve|redress|complain(?:ed|t)?|ignored|"
        r"no\s+action|nothing\s+happened|not\s+(?:been\s+)?(?:repaired|working|"
        r"received|issued|paid|moved)|unpaid|refused|denied|failed|delay(?:ed)?)\b"
        r".{0,140}\b(?:road|street|potholes?|drain|sewer|street\s*lights?|garbage|"
        r"sanitation|water\s+supply|electricity|ration|pension|certificate|passport|"
        r"aadhaar|voter\s+id|driving\s+licen[cs]e|land\s+record|tax\s+refund|"
        r"government\s+(?:service|application|school|hospital)|public\s+(?:service|"
        r"transport|hospital)|municipal\s+road)\b",
        re.IGNORECASE,
    ),
]

_GOVERNMENT_SERVICE_TOPIC_SIGNAL = re.compile(
    r"\b(?:roads?|streets?|potholes?|footpaths?|drains?|drainage|sewers?|"
    r"street\s*lights?|garbage|waste\s+collection|sanitation|public\s+toilets?|"
    r"bridges?|public\s+works?|municipal(?:ity)?|panchayat|water\s+supply|"
    r"tap\s+water|electricity|power\s+supply|public\s+distribution|ration\s+"
    r"(?:shop|card)|gas\s+connection|pension|social\s+welfare|benefit\s+payment|"
    r"scholarship|subsidy|certificates?|aadhaar|passport|driving\s+licen[cs]e|"
    r"voter\s+id|government\s+documents?|police(?:\s+station)?|public\s+safety|"
    r"income\s+tax|tax\s+refund|gst|customs|land\s+records?|mutation|tehsil|"
    r"patta|rto|transport\s+office|vehicle\s+registration|public\s+transport|"
    r"government\s+bus|permits?|challans?|government\s+schools?|public\s+schools?|"
    r"education\s+department|government\s+colleges?|public\s+universit(?:y|ies)|"
    r"school\s+admission|government\s+hospitals?|public\s+hospitals?|"
    r"primary\s+health\s+cent(?:re|er)s?|phc|public\s+health|ambulance\s+service|"
    r"government\s+dispensar(?:y|ies)|government\s+(?:service|application))\b",
    re.IGNORECASE,
)

_GOVERNMENT_SERVICE_FAILURE_SIGNAL = re.compile(
    r"\b(?:refus(?:e|es|ed|ing)|reject(?:s|ed|ing)?|den(?:y|ies|ied|ying)|"
    r"stuck|pending|delay(?:s|ed|ing)?|lost|missing|not\s+(?:been\s+)?collected|"
    r"uncollected|stopp(?:ed|ing)|closed|unavailable|not\s+(?:been\s+)?working|"
    r"not\s+(?:been\s+)?received|not\s+(?:been\s+)?issued|not\s+(?:been\s+)?"
    r"repaired|not\s+moved|will\s+not\s+respond|no\s+(?:action|response)|"
    r"nothing\s+happened|unpaid|complain(?:ed|t|ts)|ignored?|failed|broken|"
    r"dangerous\s+potholes?)\b",
    re.IGNORECASE,
)

_DEFINITIONAL_QUESTION_PATTERN = re.compile(
    r"^\s*(?:what|who|where|when|why|how)\s+(?:is|are|was|were|do|does)\b",
    re.IGNORECASE,
)

_RIGHTS_DOMAIN_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "tenant": (
        re.compile(
            r"\b(?:landlord|tenant|security\s+deposit|rent|rental|lease|"
            r"rented\s+premises|evict\w*)\b",
            re.IGNORECASE,
        ),
    ),
    "consumer": (
        re.compile(
            r"\b(?:consumer|seller|merchant|service\s+provider|warranty|refund|"
            r"purchase|product|goods?|item|defective\s+(?:phone|product|goods?|item)|"
            r"faulty\s+(?:phone|product|goods?|item))\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:replace|refund)\w*\b.{0,80}\b(?:purchase|seller|product|phone|goods?|item)\b", re.IGNORECASE),
    ),
    "labour": (
        re.compile(
            r"\b(?:employer|employee|salary|wages?|workplace|termination|terminated|"
            r"retrench(?:ed|ment)?|epf|esi|posh|unpaid\s+(?:salary|wages?))\b",
            re.IGNORECASE,
        ),
    ),
}

# These patterns describe a requested rights remedy, rather than merely a
# tenant/consumer/labour topic word.  They can therefore outrank competing
# public-service context (for example, unpaid wages at a government hospital)
# without allowing a stray word such as "landlord" to steal a road-repair
# grievance from the civic workflow.
_RIGHTS_ACTION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "tenant": (
        re.compile(r"\b(?:security\s+deposit|illegal\s+rent|rent\s+(?:increase|hike)|evict\w*|lease\s+(?:termination|terminated))\b", re.IGNORECASE),
        re.compile(r"\blandlord\b.{0,100}\b(?:deposit|rent|lease|evict\w*)\b", re.IGNORECASE),
    ),
    "consumer": (
        re.compile(r"\b(?:defective|faulty)\s+(?:phone|product|goods?|item)\b", re.IGNORECASE),
        re.compile(r"\b(?:seller|merchant|service\s+provider|warranty|purchase|product|goods?|item)\b.{0,100}\b(?:refund|replace\w*|repair|warranty|compensat\w*)\b", re.IGNORECASE),
        re.compile(r"\b(?:refund|replace\w*|warranty|compensat\w*)\b.{0,100}\b(?:seller|merchant|service\s+provider|purchase|product|goods?|item)\b", re.IGNORECASE),
    ),
    "labour": (
        re.compile(r"\b(?:unpaid|not\s+paid|has(?:n't|\s+not)\s+paid|have(?:n't|\s+not)\s+paid)\b.{0,80}\b(?:salary|wages?)\b", re.IGNORECASE),
        re.compile(r"\b(?:salary|wages?)\b.{0,80}\b(?:unpaid|not\s+paid|withheld|deducted)\b", re.IGNORECASE),
        re.compile(r"\b(?:employer|employee|workplace)\b.{0,100}\b(?:terminat\w*|retrench\w*|epf|esi|posh)\b", re.IGNORECASE),
    ),
}

_CRIMINAL_INCIDENT_PATTERNS = [
    re.compile(
        r"\b(?:stole|stolen|theft|robbed?|burglary|broke\s+into|assaulted?|"
        r"attacked?|stabbed?|shot|beaten|beat\s+me|hit\s+me|slapped?|punched?|kicked?|"
        r"mugg(?:ed|ing)|snatch(?:ed|ing)?|vandali[sz](?:e|ed|ing)?|"
        r"forg(?:e|ed|ing)(?:\s+my\s+signature)?|kidnapped?|abducted?|"
        r"murdered?|raped?|sexual\s+assault|extorted?|blackmail(?:ed|ing)?|"
        r"cheated\s+me|scamm(?:ed|ing)\s+(?:me|us)|defraud(?:ed|ing)\s+(?:me|us)|"
        r"threaten(?:ed|ing)?\s+(?:me\s+)?(?:to\s+kill|with\s+(?:a\s+)?(?:knife|"
        r"weapon|gun))|set\s+fire\s+to|arson|stalk(?:ed|ing)\s+(?:me|us))\b",
        re.IGNORECASE,
    ),
]

_COMPLAINT_DRAFT_PATTERNS = [
    re.compile(
        r"\b(draft|write|generate|create|prepare|file)\s+"
        r"(an?\s+)?(?:(?:police|consumer|formal|written)\s+)?"
        r"(complaint|fir|legal\s+notice|petition|notice)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(complaint|fir|legal\s+notice|petition)\s+"
        r"(draft|write|generate|create|prepare|file|likhna|banao)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:(?:i\s+want\s+to|help\s+me)\s+(?:file|draft)\s+(?:an?\s+)?"
        r"(?:(?:police|consumer|formal|written)\s+)?(?:complaint|fir|legal\s+notice|"
        r"petition|notice)|mujhe\s+likhna|shikayat\s+likhna)\b",
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
    query: str,
    conversation_history: list[dict] | None = None,
    *,
    allow_llm_fallback: bool = True,
) -> IntentResult:
    """Classify user intent using regex rules first, LLM fallback for ambiguous cases.

    Args:
        query: Raw user input.
        conversation_history: Previous turns (used to detect follow-ups).

    Returns:
        An ``IntentResult`` with the classified intent, confidence, and method.
    """
    q = query.strip()

    # Active danger is safety-critical even when the same message asks for
    # records.  Merely mentioning a past crime remains topic context below.
    if _IMMEDIATE_DANGER_PATTERN.search(q):
        return IntentResult(intent=INTENT_ESCALATION, confidence=0.98, method="regex")

    # 1. The requested action outranks topic-only legal or emergency words.
    # A request for murder-case records is still an information request.
    if _looks_like_information_request(q):
        return IntentResult(
            intent=INTENT_INFORMATION_REQUEST,
            confidence=0.95,
            method="regex",
            entities={"journey": "rti", "workflow": "rti"},
        )

    # 2. Direct section reference
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

    # 3. Escalation (high priority when no record-seeking action is present)
    for pat in _ESCALATION_PATTERNS:
        if pat.search(q):
            return IntentResult(
                intent=INTENT_ESCALATION, confidence=0.9, method="regex"
            )

    # Explicit drafting is an action and therefore outranks criminal, tenant,
    # consumer, labour, and civic topic words.
    for pat in _COMPLAINT_DRAFT_PATTERNS:
        if pat.search(q):
            return IntentResult(
                intent=INTENT_COMPLAINT_DRAFT,
                confidence=0.9,
                method="regex",
            )

    # A genuine criminal incident outranks the relationship or marketplace
    # topic.  Assault by a landlord remains a criminal incident, for example.
    if any(pattern.search(q) for pattern in _CRIMINAL_INCIDENT_PATTERNS):
        return IntentResult(
            intent=INTENT_CRIMINAL_INCIDENT,
            confidence=0.9,
            method="regex",
            entities={"workflow": "criminal"},
        )

    if any(pattern.search(q) for pattern in _SCHEME_ELIGIBILITY_ACTION_PATTERNS):
        return IntentResult(
            intent=INTENT_SCHEME_ELIGIBILITY,
            confidence=0.9,
            method="regex",
            entities={"journey": "scheme_eligibility", "workflow": "scheme_eligibility"},
        )

    rights_action_domain = infer_rights_action_domain(q)
    if rights_action_domain:
        return IntentResult(
            intent=INTENT_RIGHTS_GUIDANCE,
            confidence=0.92,
            method="regex",
            entities={
                "journey": "rights",
                "workflow": "rights_guidance",
                "domain": rights_action_domain,
            },
        )

    if any(pattern.search(q) for pattern in _CPGRAMS_PATTERNS):
        return IntentResult(
            intent=INTENT_GOVERNMENT_SERVICE_GRIEVANCE,
            confidence=0.9,
            method="regex",
            entities={"journey": "cpgrams", "workflow": "cpgrams"},
        )

    has_scheme_topic = any(pattern.search(q) for pattern in _SCHEME_PATTERNS)
    is_service_grievance = any(
        pattern.search(q) for pattern in _GOVERNMENT_SERVICE_PATTERNS
    ) or bool(
        (_GOVERNMENT_SERVICE_TOPIC_SIGNAL.search(q) or has_scheme_topic)
        and _GOVERNMENT_SERVICE_FAILURE_SIGNAL.search(q)
    )
    if not _DEFINITIONAL_QUESTION_PATTERN.search(q) and is_service_grievance:
        return IntentResult(
            intent=INTENT_GOVERNMENT_SERVICE_GRIEVANCE,
            confidence=0.9,
            method="regex",
            entities={"journey": "cpgrams", "workflow": "cpgrams"},
        )

    if has_scheme_topic:
        return IntentResult(
            intent=INTENT_SCHEME_ELIGIBILITY,
            confidence=0.85,
            method="regex",
            entities={"journey": "scheme_eligibility", "workflow": "scheme_eligibility"},
        )

    rights_domain = infer_rights_domain(q)
    if rights_domain:
        return IntentResult(
            intent=INTENT_RIGHTS_GUIDANCE,
            confidence=0.9,
            method="regex",
            entities={
                "journey": "rights",
                "workflow": "rights_guidance",
                "domain": rights_domain,
            },
        )

    if _DEFINITIONAL_QUESTION_PATTERN.search(q):
        return IntentResult(intent=INTENT_GENERAL, confidence=0.8, method="regex")

    # 4. Greeting
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
    if allow_llm_fallback:
        llm_result = _llm_classify(q)
        if llm_result:
            return llm_result

    # 9. Default: treat as legal query
    return IntentResult(intent=INTENT_LEGAL_QUERY, confidence=0.6, method="regex")


def infer_rights_domain(query: str) -> str | None:
    """Return the strongest tenant/consumer/labour domain signal, if any."""

    scores = {
        domain: sum(bool(pattern.search(query)) for pattern in patterns)
        for domain, patterns in _RIGHTS_DOMAIN_PATTERNS.items()
    }
    domain, score = max(scores.items(), key=lambda item: item[1])
    return domain if score else None


def infer_rights_action_domain(query: str) -> str | None:
    """Return a rights domain only when the message contains a remedy-level signal."""

    scores = {
        domain: sum(bool(pattern.search(query)) for pattern in patterns)
        for domain, patterns in _RIGHTS_ACTION_PATTERNS.items()
    }
    domain, score = max(scores.items(), key=lambda item: item[1])
    return domain if score else None


def civic_handoff_for(intent: IntentResult) -> dict | None:
    """Build the shared typed hand-off for a non-criminal top-level intent."""

    domain = intent.entities.get("domain")
    handoffs = {
        INTENT_INFORMATION_REQUEST: {
            "journey": "rti",
            "workflow": "rti",
            "handler": "rti_assistant",
            "message": (
                "Continue in the RTI assistant to turn this into a record-focused request "
                "and verify the responsible public authority."
            ),
        },
        INTENT_GOVERNMENT_SERVICE_GRIEVANCE: {
            "journey": "cpgrams",
            "workflow": "cpgrams",
            "handler": "cpgrams_assistant",
            "message": (
                "Continue in the CPGRAMS assistant to prepare and review a government "
                "service grievance before any human-confirmed portal action."
            ),
        },
        INTENT_SCHEME_ELIGIBILITY: {
            "journey": "scheme_eligibility",
            "workflow": "scheme_eligibility",
            "handler": "scheme_eligibility",
            "message": (
                "Continue in the scheme eligibility assistant for a deterministic, "
                "source-linked eligibility check."
            ),
        },
        INTENT_RIGHTS_GUIDANCE: {
            "journey": "rights",
            "workflow": "rights_guidance",
            "handler": "rights_navigator",
            "message": (
                f"Continue in Rights Navigator for jurisdiction-aware {domain or 'civic'} "
                "guidance and practical next steps."
            ),
        },
    }
    handoff = handoffs.get(intent.intent)
    if handoff is None:
        return None
    return {
        **handoff,
        "intent": intent.intent,
        **({"domain": domain} if domain else {}),
    }


def is_automatic_civic_handoff(
    intent: IntentResult,
    handoff: dict | None,
) -> bool:
    """Return whether a canonical hand-off may auto-open an internal workflow."""

    return bool(
        handoff
        and handoff.get("intent") == intent.intent
        and handoff.get("journey")
        and handoff.get("handler")
        and intent.confidence >= AUTOMATIC_CIVIC_HANDOFF_CONFIDENCE
    )


def _looks_like_information_request(query: str) -> bool:
    if any(pattern.search(query) for pattern in _EXPLICIT_RTI_PATTERNS):
        return True
    has_scheme_context = any(pattern.search(query) for pattern in _SCHEME_PATTERNS)
    has_public_context = bool(
        _PUBLIC_CONTEXT_SIGNAL.search(query)
        or _GOVERNMENT_SERVICE_TOPIC_SIGNAL.search(query)
        or has_scheme_context
    )
    has_specific_record_signal = bool(_PUBLIC_RECORD_SIGNAL.search(query))
    if (
        _APPLICATION_DOCUMENT_REQUIREMENT_SIGNAL.search(query)
        and not has_specific_record_signal
    ):
        return False
    if _INFORMATION_QUESTION_SIGNAL.search(query) and has_public_context:
        return True
    return bool(
        _INFORMATION_ACCESS_SIGNAL.search(query)
        and has_public_context
        and (
            has_specific_record_signal
            or _GENERIC_RECORD_SIGNAL.search(query)
        )
    )


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
            "- legal_query (asking a general legal question)\n"
            "- section_lookup (asking about a specific legal section)\n"
            "- complaint_draft (wants to draft/file a complaint, FIR, or legal notice)\n"
            "- information_request (wants public records or an RTI application)\n"
            "- scheme_eligibility (asks to find or check a government scheme)\n"
            "- government_service_grievance (wants a government service fixed or redressed)\n"
            "- rights_guidance (tenant, consumer, or labour rights and action guidance)\n"
            "- criminal_incident (describes a genuine criminal incident)\n"
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
                        INTENT_INFORMATION_REQUEST,
                        INTENT_SCHEME_ELIGIBILITY,
                        INTENT_GOVERNMENT_SERVICE_GRIEVANCE,
                        INTENT_RIGHTS_GUIDANCE,
                        INTENT_CRIMINAL_INCIDENT,
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
