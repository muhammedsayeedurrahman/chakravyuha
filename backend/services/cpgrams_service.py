"""Deterministic CPGRAMS grievance preparation.

This module prepares a citizen's narrative for review before any portal action.
It deliberately suggests only broad authority *types*.  Exact ministries,
departments, portal option values, and officer identities must be selected or
verified by a human against the live CPGRAMS portal.

Authoritative procedural statements are limited to the official sources in
``SOURCES``.  The records were last checked on 2026-08-20 and should be
re-verified periodically because portal procedure can change.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class SourceRecord:
    """Provenance for a government-information statement."""

    source: str
    source_url: str
    jurisdiction: str
    effective_date: str | None
    last_verified: str
    source_type: str
    status: str = "verified"


CPGRAMS_PORTAL_SOURCE = SourceRecord(
    source="CPGRAMS official portal (About, exclusions, filing and tracking)",
    source_url="https://pgportal.gov.in/",
    jurisdiction="India",
    effective_date=None,
    last_verified="2026-08-20",
    source_type="official_portal",
)

CPGRAMS_STATUS_SOURCE = SourceRecord(
    source="CPGRAMS official View Status page",
    source_url="https://pgportal.gov.in/Status",
    jurisdiction="India",
    effective_date=None,
    last_verified="2026-08-20",
    source_type="official_portal",
)

DARPG_GUIDELINES_SOURCE = SourceRecord(
    source="DARPG Comprehensive Guidelines for Handling Public Grievances",
    source_url=(
        "https://darpg.gov.in/sites/default/files/"
        "Comprehensive_guidelines_for_handling_the_Public_Grievances.pdf"
    ),
    jurisdiction="India",
    effective_date="2024-08-23",
    last_verified="2026-08-20",
    source_type="official_guideline",
)

SOURCES = (
    CPGRAMS_PORTAL_SOURCE,
    CPGRAMS_STATUS_SOURCE,
    DARPG_GUIDELINES_SOURCE,
)


@dataclass(frozen=True)
class DomainRule:
    domain: str
    label: str
    authority_type: str
    candidate: str
    patterns: tuple[re.Pattern[str], ...]
    needs_locality: bool = False


def _patterns(*values: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(value, re.IGNORECASE) for value in values)


# These are topic hints, not claims that a named authority has jurisdiction.
DOMAIN_RULES: tuple[DomainRule, ...] = (
    DomainRule(
        domain="civic_infrastructure",
        label="Civic infrastructure or local public works",
        authority_type="Local body or public works/service-delivery authority",
        candidate="Relevant local body or public works authority controlling the asset",
        patterns=_patterns(
            r"\broad|street|pothole|footpath|drain|drainage|sewer|streetlight\b",
            r"\bgarbage|waste collection|sanitation|public toilet\b",
            r"\bbridge|public works|municipal|municipality|panchayat\b",
        ),
        needs_locality=True,
    ),
    DomainRule(
        domain="public_utility",
        label="Public utility or essential service delivery",
        authority_type="Public utility or supervising service-delivery authority",
        candidate="Relevant public utility or supervising government authority",
        patterns=_patterns(
            r"\bwater supply|tap water|electricity|power cut|power supply\b",
            r"\bpublic distribution|ration shop|ration card|lpg|gas connection\b",
        ),
        needs_locality=True,
    ),
    DomainRule(
        domain="pension_social_welfare",
        label="Pension, benefit, or social-welfare service",
        authority_type="Pension, social-welfare, or benefit-administering authority",
        candidate="Relevant authority administering the pension, benefit, or welfare service",
        patterns=_patterns(
            r"\bpension|pensioner|retiral|retirement benefit\b",
            r"\bsocial welfare|benefit payment|scholarship|subsidy\b",
            r"\bdisability benefit|widow pension|old age pension\b",
        ),
    ),
    DomainRule(
        domain="certificate_document_service",
        label="Government certificate, identity, or document service",
        authority_type="Issuing public authority or its supervising department",
        candidate="Public authority responsible for issuing or correcting the document",
        patterns=_patterns(
            r"\bcertificate|caste certificate|income certificate|birth certificate|death certificate\b",
            r"\baadhaar|passport|driving licen[cs]e|voter id|government document\b",
        ),
    ),
    DomainRule(
        domain="police_public_safety_service",
        label="Police or public-safety service delivery",
        authority_type="Police/public-safety authority or its grievance supervisory office",
        candidate="Relevant police or public-safety authority responsible for the service",
        patterns=_patterns(
            r"\bpolice|police station|fir|complaint not registered\b",
            r"\bpublic safety|emergency service|traffic police\b",
        ),
        needs_locality=True,
    ),
    DomainRule(
        domain="revenue_tax",
        label="Revenue, tax, or land-record service",
        authority_type="Revenue, tax, or land-record public authority",
        candidate="Relevant revenue, tax, or land-record authority handling the service",
        patterns=_patterns(
            r"\bincome tax|tax refund|gst|customs|tax notice\b",
            r"\bland record|mutation|revenue record|tehsil|patta\b",
        ),
    ),
    DomainRule(
        domain="transport_service",
        label="Government transport service",
        authority_type="Transport or road-safety public authority",
        candidate="Relevant transport authority responsible for the service",
        patterns=_patterns(
            r"\brto|transport office|vehicle registration|driving licen[cs]e\b",
            r"\bpublic transport|government bus|permit|challan\b",
        ),
    ),
    DomainRule(
        domain="public_education_service",
        label="Public education service",
        authority_type="Public education or institution-supervising authority",
        candidate="Relevant public education authority or institution supervisor",
        patterns=_patterns(
            r"\bgovernment school|public school|education department\b",
            r"\bgovernment college|public university|school admission|teacher vacancy\b",
        ),
    ),
    DomainRule(
        domain="public_health_service",
        label="Public health service",
        authority_type="Public health or government-facility supervising authority",
        candidate="Relevant public health authority or government-facility supervisor",
        patterns=_patterns(
            r"\bgovernment hospital|public hospital|primary health cent(?:re|er)|phc\b",
            r"\bpublic health|ambulance service|government dispensary\b",
        ),
        needs_locality=True,
    ),
)


@dataclass(frozen=True)
class ExclusionRule:
    category: str
    reason: str
    alternative_path: str
    patterns: tuple[re.Pattern[str], ...]


# The exclusions below are stated by the official CPGRAMS portal and the 2024
# DARPG guidelines.  Matching is intentionally conservative.
EXCLUSION_RULES: tuple[ExclusionRule, ...] = (
    ExclusionRule(
        category="rti_matter",
        reason="The official CPGRAMS portal states that RTI matters are not taken up for redress.",
        alternative_path="Use the applicable Right to Information process instead of CPGRAMS.",
        patterns=_patterns(
            r"\b(?:rti|right to information)\b",
            r"\binformation request under (?:the )?rti\b",
        ),
    ),
    ExclusionRule(
        category="court_or_sub_judice",
        reason="The official CPGRAMS portal states that court-related or sub-judice matters are not taken up.",
        alternative_path="Use the applicable court or legal procedure and obtain qualified legal guidance if needed.",
        patterns=_patterns(
            r"\bsub[ -]?judice|pending before (?:a |the )?court|court judgment\b",
            r"\bappeal against (?:a |the )?court (?:order|judgment)\b",
        ),
    ),
    ExclusionRule(
        category="religious_matter",
        reason="The official CPGRAMS portal states that religious matters are not taken up for redress.",
        alternative_path="Verify an appropriate non-CPGRAMS channel for this matter.",
        patterns=_patterns(
            r"\breligious matter|religious doctrine|religious dispute\b",
        ),
    ),
    ExclusionRule(
        category="government_employee_service_matter",
        reason=(
            "CPGRAMS states that government-employee service matters are not taken up "
            "unless the prescribed departmental channels have already been exhausted."
        ),
        alternative_path=(
            "Use the prescribed departmental service-grievance channels first; if they "
            "have already been exhausted, verify CPGRAMS suitability before filing."
        ),
        patterns=_patterns(
            r"\bgovernment employee|government servant|civil servant\b.*\bpromotion|transfer|disciplinary|service matter|seniority\b",
            r"\bpromotion|transfer|disciplinary|service matter|seniority\b.*\bgovernment employee|government servant|civil servant\b",
        ),
    ),
    ExclusionRule(
        category="suggestion",
        reason="The 2024 DARPG guidelines list suggestions as outside the category of public grievance.",
        alternative_path="Use an appropriate public-consultation or suggestion channel and verify it with the relevant authority.",
        patterns=_patterns(
            r"\bpolicy suggestion|suggestion for government|i suggest that the government\b",
        ),
    ),
    ExclusionRule(
        category="territorial_or_foreign_relations",
        reason=(
            "The 2024 DARPG guidelines list matters affecting territorial integrity or "
            "friendly relations with other countries outside the category of public grievance."
        ),
        alternative_path="This requires verification through an appropriate specialist official channel.",
        patterns=_patterns(
            r"\bterritorial integrity|friendly relations with (?:a |another )?country|foreign relations\b",
        ),
    ),
)

SERVICE_CHANNELS_EXHAUSTED = _patterns(
    r"\b(?:all |the )?(?:prescribed )?departmental (?:channels|remedies) (?:have been |were |are )?exhausted\b",
    r"\bdepartmental (?:appeal|grievance) (?:was |has been )?(?:rejected|disposed|closed)\b",
)


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _clean_items(values: Iterable[object] | None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    for value in values:
        item = _clean_text(value)
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


class CPGRAMSService:
    """Prepare a grievance for human review; never submits it."""

    def prepare(
        self,
        narrative: str,
        *,
        state: str = "",
        district: str = "",
        locality: str = "",
        authority_hint: str = "",
        incident_date: str = "",
        prior_steps: Iterable[str] | None = None,
        prior_reference: str = "",
        desired_resolution: str = "",
        evidence: Iterable[str] | None = None,
        cpgrams_account_status: str = "unknown",
    ) -> dict:
        """Classify, identify gaps, and draft a CPGRAMS grievance.

        ``authority_hint`` is always labelled user-supplied and remains subject
        to verification.  This service never emits portal IDs or asserts an
        exact ministry/department.
        """

        narrative = _clean_text(narrative)
        if len(narrative) < 10:
            raise ValueError("Narrative must contain at least 10 characters.")

        context = {
            "state": _clean_text(state),
            "district": _clean_text(district),
            "locality": _clean_text(locality),
            "authority_hint": _clean_text(authority_hint),
            "incident_date": _clean_text(incident_date),
            "prior_steps": _clean_items(prior_steps),
            "prior_reference": _clean_text(prior_reference),
            "desired_resolution": _clean_text(desired_resolution),
            "evidence": _clean_items(evidence),
            "cpgrams_account_status": _clean_text(cpgrams_account_status).lower() or "unknown",
        }

        exclusion_context = " ".join([narrative, *context["prior_steps"]])
        service_matter_channels_exhausted = (
            any(
                rule.category == "government_employee_service_matter"
                and any(pattern.search(exclusion_context) for pattern in rule.patterns)
                for rule in EXCLUSION_RULES
            )
            and any(
                pattern.search(exclusion_context)
                for pattern in SERVICE_CHANNELS_EXHAUSTED
            )
        )
        exclusion = self._match_exclusion(exclusion_context)
        domain, matched_terms = self._classify_domain(narrative)
        classification = self._classification(domain, matched_terms)

        if exclusion:
            return {
                "status": "not_suitable",
                "classification": classification,
                "suitability": {
                    "is_suitable": False,
                    "exclusion_category": exclusion.category,
                    "reason": exclusion.reason,
                    "alternative_path": exclusion.alternative_path,
                    "requires_verification": False,
                },
                "authority": self._authority(domain, context, excluded=True),
                "missing_information": [],
                "draft": None,
                "filing_guide": self.get_filing_guide(),
                "sources": self.get_sources(),
            }

        missing = self._missing_information(domain, context)
        draft = self._build_draft(narrative, domain, context)
        status = "needs_information" if missing else "ready_for_review"

        return {
            "status": status,
            "classification": classification,
            "suitability": {
                "is_suitable": True,
                "exclusion_category": None,
                "reason": (
                    (
                        "A government-employee service matter was identified, but the citizen "
                        "reports that prescribed departmental channels were exhausted. That "
                        "condition and CPGRAMS suitability require human verification."
                    )
                    if service_matter_channels_exhausted
                    else (
                        "The narrative appears to concern government service delivery and did "
                        "not match the official exclusion checks. A human must still verify "
                        "suitability."
                    )
                ),
                "alternative_path": None,
                "requires_verification": True,
            },
            "authority": self._authority(domain, context),
            "missing_information": missing,
            "draft": draft,
            "filing_guide": self.get_filing_guide(),
            "sources": self.get_sources(),
        }

    @staticmethod
    def _match_exclusion(narrative: str) -> ExclusionRule | None:
        for rule in EXCLUSION_RULES:
            matched = any(pattern.search(narrative) for pattern in rule.patterns)
            if not matched:
                continue
            if (
                rule.category == "government_employee_service_matter"
                and any(pattern.search(narrative) for pattern in SERVICE_CHANNELS_EXHAUSTED)
            ):
                # The official exclusion is conditional. If exhaustion is
                # asserted, leave suitability open but still require human
                # verification of that assertion and of the portal pathway.
                continue
            if matched:
                return rule
        return None

    @staticmethod
    def _classify_domain(narrative: str) -> tuple[DomainRule, list[str]]:
        best_rule: DomainRule | None = None
        best_matches: list[str] = []
        for rule in DOMAIN_RULES:
            matches = [match.group(0) for pattern in rule.patterns if (match := pattern.search(narrative))]
            if len(matches) > len(best_matches):
                best_rule = rule
                best_matches = matches

        if best_rule:
            return best_rule, best_matches

        return (
            DomainRule(
                domain="general_public_service",
                label="General government service-delivery grievance",
                authority_type="Relevant Central, State, or local public authority",
                candidate="Public authority responsible for the service described by the citizen",
                patterns=(),
            ),
            [],
        )

    @staticmethod
    def _classification(domain: DomainRule, matches: list[str]) -> dict:
        if len(matches) >= 2:
            confidence = "high"
        elif matches:
            confidence = "medium"
        else:
            confidence = "low"
        reason = (
            f"Matched topic indicators: {', '.join(matches)}."
            if matches
            else "No specific domain indicator was strong enough; using a general service-delivery category."
        )
        return {
            "domain": domain.domain,
            "label": domain.label,
            "confidence": confidence,
            "reason": reason,
        }

    @staticmethod
    def _authority(domain: DomainRule, context: dict, excluded: bool = False) -> dict:
        if excluded:
            return {
                "authority_type": "Not determined for an excluded CPGRAMS category",
                "candidate": "Unavailable until the appropriate non-CPGRAMS pathway is verified",
                "confidence": "low",
                "reason": "The narrative matched an official CPGRAMS exclusion.",
                "requires_verification": True,
                "authority_hint": context["authority_hint"] or None,
                "authority_hint_status": "user_supplied_requires_verification" if context["authority_hint"] else None,
                "provenance": asdict(CPGRAMS_PORTAL_SOURCE),
            }

        jurisdiction_parts = [
            value for value in (context["locality"], context["district"], context["state"]) if value
        ]
        has_jurisdiction = bool(context["state"] and context["district"])
        candidate = context["authority_hint"] or domain.candidate
        reason = (
            f"Broad topic routing for {domain.label.lower()}"
            + (f" in {', '.join(jurisdiction_parts)}" if jurisdiction_parts else "")
            + ". Exact portal authority selection must be verified by the citizen."
        )
        return {
            "authority_type": domain.authority_type,
            "candidate": candidate,
            "confidence": "medium" if has_jurisdiction else "low",
            "reason": reason,
            "requires_verification": True,
            "authority_hint": context["authority_hint"] or None,
            "authority_hint_status": "user_supplied_requires_verification" if context["authority_hint"] else None,
            "provenance": asdict(CPGRAMS_PORTAL_SOURCE),
        }

    @staticmethod
    def _missing_information(domain: DomainRule, context: dict) -> list[str]:
        missing: list[str] = []
        if not context["state"]:
            missing.append("state_or_union_territory")
        if not context["district"]:
            missing.append("district_or_city")
        if domain.needs_locality and not context["locality"]:
            missing.append("locality_or_service_location")
        if not context["authority_hint"]:
            missing.append("public_authority_or_office_involved")
        if not context["incident_date"]:
            missing.append("incident_date_or_period")
        if not context["desired_resolution"]:
            missing.append("desired_resolution")
        if context["cpgrams_account_status"] not in {"registered", "not_registered"}:
            missing.append("cpgrams_account_status")
        return missing

    @staticmethod
    def _build_draft(narrative: str, domain: DomainRule, context: dict) -> dict:
        first_sentence = re.split(r"(?<=[.!?])\s+", narrative, maxsplit=1)[0]
        first_sentence = first_sentence.rstrip(".!? ")
        subject_detail = first_sentence[:90].rstrip()
        subject = f"Grievance regarding {domain.label.lower()}: {subject_detail}"
        subject = subject[:160].rstrip()

        facts = [f"Citizen's description: {narrative}"]
        jurisdiction = ", ".join(
            value for value in (context["locality"], context["district"], context["state"]) if value
        )
        if jurisdiction:
            facts.append(f"Location/jurisdiction supplied by citizen: {jurisdiction}")
        if context["incident_date"]:
            facts.append(f"Date or period supplied by citizen: {context['incident_date']}")
        if context["authority_hint"]:
            facts.append(
                "Authority named by citizen (requires portal verification): "
                f"{context['authority_hint']}"
            )
        facts.extend(f"Prior step reported by citizen: {step}" for step in context["prior_steps"])
        if context["prior_reference"]:
            facts.append(f"Prior reference supplied by citizen: {context['prior_reference']}")

        relief = (
            [context["desired_resolution"]]
            if context["desired_resolution"]
            else [
                "Please examine the service-delivery grievance, provide appropriate redress, "
                "and communicate the action taken."
            ]
        )
        evidence = list(context["evidence"])

        formatted_lines = [
            f"Subject: {subject}",
            "",
            "Facts:",
            *(f"- {fact}" for fact in facts),
            "",
            "Relief requested:",
            *(f"- {item}" for item in relief),
            "",
            "Supporting documents/evidence:",
            *(f"- {item}" for item in evidence),
        ]
        if not evidence:
            formatted_lines.append("- None listed; add only documents that the citizen actually possesses.")

        return {
            "subject": subject,
            "facts": facts,
            "relief_requested": relief,
            "evidence": evidence,
            "formatted_text": "\n".join(formatted_lines),
        }

    @staticmethod
    def get_sources() -> list[dict]:
        return [asdict(source) for source in SOURCES]

    @staticmethod
    def get_filing_guide() -> dict:
        """Return only filing/tracking facts supported by official sources."""

        return {
            "portal_url": CPGRAMS_PORTAL_SOURCE.source_url,
            "status_url": CPGRAMS_STATUS_SOURCE.source_url,
            "steps": [
                "Register or sign in on the official CPGRAMS portal; the portal states that grievances can be lodged only by registered users.",
                "Review the grievance and select the live portal authority/category; do not rely on an unverified automatic ministry selection.",
                "Complete OTP, CAPTCHA, login, consent, and identity steps yourself.",
                "Confirm the final reviewed payload immediately before submission.",
                "Keep the unique registration ID shown by CPGRAMS after a verified submission.",
            ],
            "tracking": [
                "Use the unique registration ID to track the grievance on the official View Status page.",
                "After closure, the portal permits feedback; its current page states that a Poor rating enables an appeal option.",
                "The portal states that appeal status can also be tracked using the grievance registration number.",
            ],
            "fee_note": (
                "The CPGRAMS portal states that the Government does not charge the public a "
                "filing fee; any payment made for assisted filing through a CSC is a CSC charge."
            ),
            "email_note": "The CPGRAMS portal states that grievances sent by email are not entertained; lodge them on the portal.",
            "human_actions_required": [
                "authority/category verification",
                "login or registration",
                "OTP",
                "CAPTCHA",
                "final review and explicit submission confirmation",
            ],
            "provenance": [
                asdict(CPGRAMS_PORTAL_SOURCE),
                asdict(CPGRAMS_STATUS_SOURCE),
                asdict(DARPG_GUIDELINES_SOURCE),
            ],
        }


_cpgrams_service: CPGRAMSService | None = None


def get_cpgrams_service() -> CPGRAMSService:
    """Return the process-wide deterministic CPGRAMS preparation service."""

    global _cpgrams_service
    if _cpgrams_service is None:
        _cpgrams_service = CPGRAMSService()
    return _cpgrams_service


def prepare_cpgrams_grievance(narrative: str, **context) -> dict:
    """Functional adapter for callers that do not use service injection."""

    return get_cpgrams_service().prepare(narrative, **context)
