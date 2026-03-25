"""Agentic Complaint Drafter — auto-drafts FIR / Legal Notice / Complaint from narrative.

Pipeline:
  1. Analyze narrative → extract entities (offense, sections, jurisdiction)
  2. Resolve statutes → IPC↔BNS mapping + punishment details
  3. Classify document type → FIR / Legal Notice / Complaint Petition
  4. Identify missing fields → prompt user for critical gaps
  5. Generate LLM-powered draft → professional, legally-sound document
  6. Attach strategy → next steps, evidence checklist, cost estimate
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from backend.legal.nyaya_extractor import NyayaEntityExtractor, EntityType
from backend.legal.statute_resolver import StatuteResolver
from backend.legal.strategy_generator import StrategyGenerator
from backend.legal.document_drafter import DocumentDrafter, DocumentType, PartyInfo, CaseContext

logger = logging.getLogger("chakravyuha")


# ── Verb-to-noun normalization (narratives use verbs, extractor expects nouns) ─

_VERB_TO_OFFENSE = {
    # Theft variants
    "stole": "theft", "stolen": "theft", "steal": "theft", "stealing": "theft",
    "robbed": "theft", "snatched": "theft", "pickpocketed": "theft",
    "looted": "theft", "burgled": "theft", "shoplifted": "theft",
    # Hurt variants
    "hit": "hurt", "hitting": "hurt", "beaten": "hurt", "beat": "hurt",
    "slapped": "hurt", "punched": "hurt", "kicked": "hurt", "attacked": "hurt",
    "injured": "hurt", "assaulted": "hurt",
    # Murder variants
    "killed": "murder", "murdered": "murder", "stabbed": "murder",
    # Cheating variants
    "cheated": "cheating", "scammed": "cheating", "conned": "cheating",
    "defrauded": "cheating", "swindled": "cheating", "duped": "cheating",
    "tricked": "cheating",
    # Rape variants
    "raped": "rape", "molested": "rape",
    # Cruelty variants
    "tortured": "cruelty", "harassed": "cruelty",
    # Kidnapping variants
    "kidnapped": "kidnapping", "abducted": "kidnapping",
    # Extortion
    "extorted": "extortion", "blackmailed": "extortion",
    # Robbery
    "robbed at gunpoint": "robbery", "mugged": "robbery",
}


def _normalize_narrative(text: str) -> str:
    """Inject offense noun keywords when narrative uses verb forms."""
    text_lower = text.lower()
    injected = set()
    for verb, noun in _VERB_TO_OFFENSE.items():
        if verb in text_lower and noun not in text_lower:
            injected.add(noun)
    if injected:
        return text + " [" + ", ".join(injected) + "]"
    return text


# ── Data models ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExtractedInfo:
    """Immutable extraction result from narrative analysis."""

    offense: str
    offense_confidence: float
    bns_sections: tuple[str, ...]
    ipc_sections: tuple[str, ...]
    jurisdiction: str
    punishment_summary: str
    cognizable: bool
    bailable: bool
    raw_entities: tuple


@dataclass(frozen=True)
class DraftResult:
    """Immutable result of the agentic drafting pipeline."""

    status: str  # "success" | "needs_info" | "error"
    document_type: str
    content: str
    extracted_info: Optional[ExtractedInfo]
    applicable_sections: tuple[str, ...]
    strategy_summary: Optional[dict]
    missing_fields: tuple[str, ...]
    confidence: float
    generated_at: str
    error: Optional[str] = None


# ── Complaint classification rules ──────────────────────────────────────────

_CRIMINAL_OFFENSES = frozenset({
    "murder", "hurt", "theft", "rape", "robbery", "kidnapping",
    "assault", "dacoity", "extortion", "criminal intimidation",
    "cruelty", "dowry death", "rioting",
})

_CIVIL_OFFENSES = frozenset({
    "cheating", "defamation", "breach of trust", "forgery",
    "consumer dispute", "property dispute", "contract breach",
    "negligence", "malpractice",
})

_NOTICE_KEYWORDS = re.compile(
    r"\b(warn|notice|demand|settle|compensation|refund|payment due)\b",
    re.IGNORECASE,
)


# ── Date extraction ─────────────────────────────────────────────────────────

_DATE_PATTERNS = [
    # "March 20, 2026" or "20 March 2026"
    re.compile(
        r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+(\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(january|february|march|april|may|june|july|august|"
        r"september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})\b",
        re.IGNORECASE,
    ),
    # "20/03/2026" or "2026-03-20"
    re.compile(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b"),
    re.compile(r"\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b"),
    # Relative: "last Tuesday", "yesterday", "last week"
    re.compile(r"\b(yesterday|last\s+\w+|today)\b", re.IGNORECASE),
]

_LOCATION_PATTERNS = [
    re.compile(r"\b(?:at|in|near|from|outside)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", re.UNICODE),
    re.compile(r"\b(?:at|in|near|from|outside)\s+(?:my|the|our)\s+(\w+(?:\s+\w+)?)", re.IGNORECASE),
]

_NAME_PATTERNS = [
    re.compile(
        r"\b(?:my\s+)?(?:neighbor|neighbour|friend|colleague|boss|employer|"
        r"husband|wife|brother|sister|relative|landlord|tenant|partner)\s+"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
    ),
    re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:stole|hit|attacked|cheated|threatened)\b"),
]


# ── Main agent class ────────────────────────────────────────────────────────

class ComplaintDrafterAgent:
    """Agentic pipeline: narrative → entities → sections → LLM draft → strategy."""

    def __init__(self) -> None:
        self._extractor = NyayaEntityExtractor()
        self._resolver = StatuteResolver()
        self._strategy = StrategyGenerator()
        self._drafter = DocumentDrafter()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def auto_draft(
        self,
        narrative: str,
        complainant_name: str = "",
        complainant_phone: str = "",
        complainant_address: str = "",
        complainant_email: str = "",
        accused_name: str = "",
        accused_phone: str = "",
        accused_address: str = "",
        preferred_doc_type: str = "",
        language: str = "en-IN",
    ) -> DraftResult:
        """Run the full agentic pipeline on a user narrative.

        Args:
            narrative: Free-text description of what happened.
            complainant_name: Name of the person filing.
            complainant_phone: Phone number of complainant.
            complainant_address: Address of complainant.
            complainant_email: Email of complainant (optional).
            accused_name: Name of accused (auto-extracted if empty).
            accused_phone: Phone of accused (optional).
            accused_address: Address of accused (optional).
            preferred_doc_type: Force FIR / LEGAL_NOTICE / COMPLAINT.
            language: Language code (e.g., 'hi-IN', 'en-IN').

        Returns:
            DraftResult with the generated document and metadata.
        """
        now = datetime.now().isoformat()

        # Step 1: Extract entities from narrative
        extracted = self._analyze_narrative(narrative, language)
        if extracted is None:
            return DraftResult(
                status="error",
                document_type="",
                content="",
                extracted_info=None,
                applicable_sections=(),
                strategy_summary=None,
                missing_fields=(),
                confidence=0.0,
                generated_at=now,
                error="Could not extract any legal entities from the narrative. "
                      "Please describe the incident in more detail.",
            )

        # Step 2: Classify document type
        doc_type = self._classify_document_type(
            extracted, narrative, preferred_doc_type
        )

        # Step 3: Extract contextual details from narrative
        incident_date = self._extract_date(narrative)
        incident_location = self._extract_location(narrative)
        extracted_accused = self._extract_accused_name(narrative)

        # Use extracted values as fallback for empty fields
        accused_name = accused_name or extracted_accused or "Unknown"

        # Step 4: Identify missing critical fields
        missing = self._identify_missing_fields(
            complainant_name=complainant_name,
            complainant_phone=complainant_phone,
            accused_name=accused_name,
            incident_date=incident_date,
            incident_location=incident_location,
        )

        # Step 5: Build case context
        context = CaseContext(
            complainant=PartyInfo(
                name=complainant_name or "To be provided",
                phone=complainant_phone or "To be provided",
                email=complainant_email or None,
                address=complainant_address or "To be provided",
            ),
            accused=PartyInfo(
                name=accused_name,
                phone=accused_phone or "Unknown",
                address=accused_address or "Unknown",
            ),
            case_type=extracted.offense.title(),
            incident_date=incident_date or datetime.now().strftime("%Y-%m-%d"),
            incident_location=incident_location or "To be provided",
            description=narrative,
            offense_sections=list(extracted.bns_sections),
            evidence=[],
            witnesses=[],
        )

        # Step 6: Generate document (LLM-enhanced or template)
        content = self._generate_document(doc_type, context, extracted, language)

        # Step 7: Generate strategy
        strategy_plan = self._strategy.generate_strategy(
            extracted.offense.title(), list(extracted.bns_sections)
        )
        strategy_summary = {
            "recommended_forum": strategy_plan.recommended_forum.value,
            "total_timeline": strategy_plan.total_timeline,
            "total_estimated_cost": strategy_plan.total_estimated_cost,
            "next_immediate_action": strategy_plan.next_immediate_action,
            "evidence_checklist": strategy_plan.evidence_checklist,
            "mediation_recommended": strategy_plan.mediation_recommended,
            "steps": [
                {
                    "step": s.step_number,
                    "title": s.title,
                    "timeline": s.timeline,
                    "cost": s.estimated_cost,
                }
                for s in strategy_plan.steps
            ],
        }

        status = "needs_info" if missing else "success"

        return DraftResult(
            status=status,
            document_type=doc_type,
            content=content,
            extracted_info=extracted,
            applicable_sections=extracted.bns_sections,
            strategy_summary=strategy_summary,
            missing_fields=tuple(missing),
            confidence=extracted.offense_confidence,
            generated_at=now,
        )

    # ------------------------------------------------------------------
    # Step 1: Analyze narrative
    # ------------------------------------------------------------------

    def _analyze_narrative(
        self, narrative: str, language: str
    ) -> Optional[ExtractedInfo]:
        """Extract legal entities and resolve statutes from narrative text."""
        lang_code = language.split("-")[0] if "-" in language else language

        # Normalize verb forms to noun keywords for the extractor
        normalized = _normalize_narrative(narrative)
        entities = self._extractor.extract(normalized, lang_code)

        if not entities:
            return None

        # Collect offense, sections, jurisdiction
        offense = ""
        offense_conf = 0.0
        bns_sections: list[str] = []
        ipc_sections: list[str] = []
        jurisdiction = ""

        for entity in entities:
            if entity.entity_type == EntityType.OFFENSE:
                offense = entity.text
                offense_conf = entity.confidence
                bns_sections.append(entity.statute_reference)
                ipc_sections.extend(entity.alternate_names)

            elif entity.entity_type == EntityType.SECTION:
                ref = entity.statute_reference
                if ref.startswith("BNS"):
                    bns_sections.append(ref)
                else:
                    ipc_sections.append(ref)
                # Also resolve cross-reference
                for alt in entity.alternate_names:
                    if alt.startswith("IPC"):
                        ipc_sections.append(alt)

            elif entity.entity_type == EntityType.JURISDICTION:
                jurisdiction = entity.text

        # Deduplicate
        bns_sections = list(dict.fromkeys(bns_sections))
        ipc_sections = list(dict.fromkeys(ipc_sections))

        # Resolve statute details for punishment/cognizable/bailable info
        punishment_parts = []
        cognizable = False
        bailable = True

        for bns_code in bns_sections:
            # Try IPC equivalent for lookup
            for ipc_code in ipc_sections:
                details = self._extractor.get_statute_details(ipc_code)
                if "error" not in details:
                    pun = details.get("punishment", "")
                    if pun:
                        punishment_parts.append(pun)
                    if details.get("cognizable"):
                        cognizable = True
                    if not details.get("bailable", True):
                        bailable = False
                    break

        # If no jurisdiction extracted, infer from cognizable status
        if not jurisdiction:
            jurisdiction = "Police Station (FIR)" if cognizable else "Magistrate Court"

        return ExtractedInfo(
            offense=offense or "general",
            offense_confidence=offense_conf,
            bns_sections=tuple(bns_sections),
            ipc_sections=tuple(ipc_sections),
            jurisdiction=jurisdiction,
            punishment_summary=" | ".join(punishment_parts) if punishment_parts else "See applicable sections",
            cognizable=cognizable,
            bailable=bailable,
            raw_entities=tuple(
                {
                    "text": e.text,
                    "type": e.entity_type.value,
                    "reference": e.statute_reference,
                    "confidence": e.confidence,
                }
                for e in entities
            ),
        )

    # ------------------------------------------------------------------
    # Step 2: Classify document type
    # ------------------------------------------------------------------

    def _classify_document_type(
        self,
        extracted: ExtractedInfo,
        narrative: str,
        preferred: str,
    ) -> str:
        """Decide whether to generate FIR, Legal Notice, or Complaint."""
        # Honor explicit user preference
        if preferred:
            preferred_upper = preferred.upper().replace(" ", "_")
            valid = {"FIR", "LEGAL_NOTICE", "COMPLAINT"}
            if preferred_upper in valid:
                return preferred_upper

        offense_lower = extracted.offense.lower()

        # Criminal + cognizable → FIR
        if offense_lower in _CRIMINAL_OFFENSES and extracted.cognizable:
            return "FIR"

        # Notice keywords in narrative → Legal Notice
        if _NOTICE_KEYWORDS.search(narrative):
            return "LEGAL_NOTICE"

        # Civil offenses → Complaint
        if offense_lower in _CIVIL_OFFENSES:
            return "COMPLAINT"

        # Default: FIR for criminal, COMPLAINT for everything else
        if offense_lower in _CRIMINAL_OFFENSES:
            return "FIR"

        return "COMPLAINT"

    # ------------------------------------------------------------------
    # Step 3: Extract contextual details
    # ------------------------------------------------------------------

    def _extract_date(self, narrative: str) -> str:
        """Try to extract an incident date from the narrative."""
        for pattern in _DATE_PATTERNS:
            match = pattern.search(narrative)
            if match:
                return match.group(0)
        return ""

    def _extract_location(self, narrative: str) -> str:
        """Try to extract incident location from the narrative."""
        for pattern in _LOCATION_PATTERNS:
            match = pattern.search(narrative)
            if match:
                return match.group(1)
        return ""

    def _extract_accused_name(self, narrative: str) -> str:
        """Try to extract accused person's name from narrative."""
        for pattern in _NAME_PATTERNS:
            match = pattern.search(narrative)
            if match:
                return match.group(1)
        return ""

    # ------------------------------------------------------------------
    # Step 4: Identify missing fields
    # ------------------------------------------------------------------

    @staticmethod
    def _identify_missing_fields(
        complainant_name: str,
        complainant_phone: str,
        accused_name: str,
        incident_date: str,
        incident_location: str,
    ) -> list[str]:
        """Return list of critical fields that are still missing."""
        missing = []
        if not complainant_name:
            missing.append("complainant_name")
        if not complainant_phone:
            missing.append("complainant_phone")
        if not accused_name or accused_name == "Unknown":
            missing.append("accused_name")
        if not incident_date:
            missing.append("incident_date")
        if not incident_location:
            missing.append("incident_location")
        return missing

    # ------------------------------------------------------------------
    # Step 5: Generate document
    # ------------------------------------------------------------------

    def _generate_document(
        self,
        doc_type: str,
        context: CaseContext,
        extracted: ExtractedInfo,
        language: str,
    ) -> str:
        """Generate the document using LLM with template fallback."""
        # Try LLM-powered generation first
        llm_content = self._generate_with_llm(doc_type, context, extracted, language)
        if llm_content and not self._is_llm_refusal(llm_content):
            return llm_content

        # Fallback to template-based generation
        logger.info("LLM unavailable or refused — falling back to template generation")
        type_map = {
            "FIR": DocumentType.FIR,
            "LEGAL_NOTICE": DocumentType.LEGAL_NOTICE,
            "COMPLAINT": DocumentType.COMPLAINT,
        }
        return self._drafter.get_document(type_map[doc_type], context)

    @staticmethod
    def _is_llm_refusal(content: str) -> bool:
        """Detect if the LLM refused to generate the document."""
        refusal_signals = [
            "i can't draft", "i cannot draft", "i'm sorry",
            "i can\u2019t draft", "i am sorry", "unable to generate",
            "i don't have access", "i don\u2019t have access",
        ]
        content_lower = content.lower()[:300]
        return any(signal in content_lower for signal in refusal_signals)

    def _generate_with_llm(
        self,
        doc_type: str,
        context: CaseContext,
        extracted: ExtractedInfo,
        language: str,
    ) -> Optional[str]:
        """Use LLM to generate a professional legal document."""
        try:
            from backend.config import LLM_ENABLED
            if not LLM_ENABLED:
                return None

            from backend.services.llm import get_llm_service
            llm = get_llm_service()
            if not llm.is_available:
                return None

            doc_type_labels = {
                "FIR": "First Information Report (FIR)",
                "LEGAL_NOTICE": "Legal Notice",
                "COMPLAINT": "Complaint Petition",
            }

            sections_text = ", ".join(extracted.bns_sections)
            ipc_text = ", ".join(extracted.ipc_sections) if extracted.ipc_sections else "N/A"

            system_prompt = (
                "You are an expert Indian legal document drafter. "
                "You MUST generate the requested legal document in full. "
                "Do NOT refuse, apologize, or say you cannot draft. "
                "Do NOT ask for more information. "
                "Use formal legal language appropriate for Indian courts. "
                "Reference BNS sections (current law) with IPC equivalents in parentheses. "
                "If any field says 'To be provided' or 'Unknown', use [___] placeholder."
            )

            user_prompt = (
                f"Draft a complete {doc_type_labels.get(doc_type, doc_type)} "
                f"with the following details:\n\n"
                f"COMPLAINANT:\n"
                f"  Name: {context.complainant.name}\n"
                f"  Phone: {context.complainant.phone}\n"
                f"  Address: {context.complainant.address}\n\n"
                f"ACCUSED:\n"
                f"  Name: {context.accused.name}\n"
                f"  Address: {context.accused.address}\n\n"
                f"INCIDENT:\n"
                f"  Date: {context.incident_date}\n"
                f"  Location: {context.incident_location}\n"
                f"  Type: {context.case_type}\n"
                f"  Narrative: {context.description}\n\n"
                f"APPLICABLE LAW:\n"
                f"  BNS Sections: {sections_text}\n"
                f"  IPC Equivalent: {ipc_text}\n"
                f"  Cognizable: {'Yes' if extracted.cognizable else 'No'}\n"
                f"  Bailable: {'Yes' if extracted.bailable else 'No'}\n"
                f"  Punishment: {extracted.punishment_summary}\n\n"
                f"FORMAT REQUIREMENTS:\n"
                f"- Include proper document header with title\n"
                f"- Include all standard sections of a {doc_type_labels.get(doc_type, doc_type)}\n"
                f"- Add verification clause and signature blocks\n"
                f"- Output ONLY the document text, no commentary\n"
            )

            # Use generate_raw to bypass the Q&A system prompt
            result = llm.generate_raw(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=2048,
            )
            return result

        except Exception as exc:
            logger.warning("LLM document generation failed: %s", exc)
            return None
