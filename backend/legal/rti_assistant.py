"""Deterministic RTI routing and record-request drafting.

The routing catalogue contains functional hints, not a PIO directory.  This
module therefore keeps authority names generic and exposes uncertainty instead
of guessing an officer, department, fee, or State filing portal.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.config import DATA_DIR
from backend.legal.document_drafter import DocumentDrafter, RTIContext
from backend.models.schemas import (
    ConfidenceLevel,
    JurisdictionCompleteness,
    KnowledgeStatus,
    Provenance,
    RTIDraftRequest,
    RTIDraftResponse,
    RTIFilingGuidance,
    RTIIdentifyRequest,
    RTIRoutingResult,
)


RTI_ACT_SOURCE = Provenance(
    source="The Right to Information Act, 2005",
    source_url=(
        "https://www.indiacode.nic.in/bitstream/123456789/15691/1/"
        "rti_act_2005.pdf"
    ),
    jurisdiction="India",
    effective_date="2005-10-12",
    last_verified="2026-08-20",
)
RTI_ONLINE_SOURCE = Provenance(
    source="RTI Online - Government of India FAQ",
    source_url="https://rtionline.gov.in/faq.php",
    jurisdiction="Central Government public authorities",
    last_verified="2026-08-20",
)


_FIELD_LABELS = {
    "state": "State or Union Territory",
    "district": "District",
    "district_or_city": "District or city",
    "locality": "Locality and identifiable location",
    "road_type_or_controlling_authority": "Road type or any known controlling authority",
    "service_or_asset": "Specific public service or asset",
    "water_supplier_or_connection_details": "Water supplier or connection/service details",
    "ration_card_or_fair_price_shop_details": "Ration-card or fair-price-shop reference",
    "police_station_or_unit": "Police station or unit",
    "record_or_reference_number": "Complaint or record reference number, if available",
    "institution_or_scheme_name": "Institution or scheme name",
    "government_level": "Whether the authority is local, State/UT, or Central",
    "tehsil_or_taluk": "Tehsil or taluk",
    "property_or_record_identifier": "Property or land-record identifier",
    "institution_or_programme": "Institution or programme name",
    "service_date_or_reference": "Relevant service date or reference number",
    "scheme_name": "Scheme name",
    "application_or_beneficiary_reference": "Application or beneficiary reference",
    "government_service_or_programme": "Government service, programme, or record involved",
    "state_or_central": "Whether the matter concerns a State/UT or Central authority",
    "office_previously_contacted": "Office already contacted, if any",
}


class RTIAssistant:
    """Prepare reviewable RTI applications without inventing jurisdiction."""

    def __init__(self, data_file: Path | None = None) -> None:
        self.data_file = data_file or DATA_DIR / "rti_authority_hints.json"
        with self.data_file.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.metadata: dict[str, Any] = payload["metadata"]
        self.records: list[dict[str, Any]] = payload["records"]
        self.fallback: dict[str, Any] = payload["fallback"]
        self.drafter = DocumentDrafter()

    def identify_department(self, request: RTIIdentifyRequest) -> RTIRoutingResult:
        """Return a functional authority candidate and the information still needed."""
        authority_hint = self._known_text(request.authority_hint)
        road_type = self._known_text(request.road_type)
        searchable = " ".join(
            value
            for value in (
                request.issue,
                authority_hint,
                road_type,
            )
            if value
        ).casefold()
        scored: list[tuple[int, int, dict[str, Any]]] = []
        for record in self.records:
            matches = [
                keyword
                for keyword in record.get("keywords", [])
                if keyword.casefold() in searchable
            ]
            # Prefer a more specific phrase when keyword counts tie.
            scored.append((len(matches), max((len(k) for k in matches), default=0), record))
        best_score, _, record = max(scored, key=lambda row: (row[0], row[1]))
        if best_score == 0:
            record = self.fallback

        jurisdiction = JurisdictionCompleteness.from_values(
            state=request.state,
            district=request.district,
            city=request.city,
            locality=request.locality,
            authority=request.authority_hint,
        )
        required_fields = record.get("required_fields", [])
        missing = [
            _FIELD_LABELS.get(field, field.replace("_", " ").capitalize())
            for field in required_fields
            if not self._field_is_present(field, request)
        ]

        missing_jurisdiction_fields = {
            "state": not jurisdiction.state_known,
            "district": not jurisdiction.district_known,
            "district_or_city": not (
                jurisdiction.district_known or jurisdiction.city_known
            ),
            "locality": not jurisdiction.locality_known,
            "state_or_central": not (
                jurisdiction.state_known or jurisdiction.authority_known
            ),
        }
        jurisdiction_missing = any(
            missing_jurisdiction_fields.get(field, False)
            for field in required_fields
        )
        if jurisdiction_missing:
            confidence = ConfidenceLevel.REQUIRES_JURISDICTION
            status = KnowledgeStatus.REQUIRES_JURISDICTION
        elif best_score == 0:
            confidence = ConfidenceLevel.LOW
            status = KnowledgeStatus.REQUIRES_VERIFICATION
        else:
            # Topic matches are only hints.  They never establish record custody.
            confidence = ConfidenceLevel.MEDIUM
            status = KnowledgeStatus.REQUIRES_VERIFICATION

        likely_authority = record["likely_authority"]
        if authority_hint:
            likely_authority = (
                f"Citizen-provided candidate: {authority_hint}. Verify that this "
                "public authority holds or controls the requested records before filing."
            )

        reason = record["reason"]
        if missing:
            reason += " Clarification is needed before the office can be narrowed safely."

        return RTIRoutingResult(
            domain=record["domain"],
            likely_authority=likely_authority,
            authority_type=record["authority_type"],
            confidence=confidence,
            reason=reason,
            missing_information=missing,
            jurisdiction_completeness=jurisdiction,
            status=status,
            source=self.metadata["official_framework_source"],
            source_url=self.metadata["official_framework_url"],
        )

    def propose_information_requests(self, request: RTIIdentifyRequest) -> list[str]:
        """Transform a grievance into requests for existing records/information."""
        record = self._matching_record(request)
        location_parts = (
            self._known_text(value)
            for value in (request.locality, request.city, request.district, request.state)
        )
        location = ", ".join(part for part in location_parts if part) or "the specified location"
        period = self._known_text(request.date_range) or "the relevant period"
        values = {
            "issue": self._clean_issue(request.issue),
            "location": location,
            "date_range": period,
        }
        return [template.format(**values) for template in record["record_requests"]]

    def prepare_draft(self, request: RTIDraftRequest) -> RTIDraftResponse:
        """Create a structured RTI draft plus jurisdiction-qualified next steps."""
        routing = self.identify_department(request)
        information_requests = [
            item.strip() for item in request.information_requests if item.strip()
        ] or self.propose_information_requests(request)

        missing = list(routing.missing_information)
        if not request.applicant_name:
            missing.append("Applicant name")
        if not request.applicant_address:
            missing.append("Applicant postal address")
        if request.is_indian_citizen is not True:
            missing.append("Confirmation that the applicant is a citizen of India")

        location_parts = (
            self._known_text(value)
            for value in (request.locality, request.city, request.district, request.state)
        )
        location = ", ".join(value for value in location_parts if value)
        context = RTIContext(
            applicant_name=request.applicant_name or "[Applicant name required]",
            applicant_address=request.applicant_address or "[Applicant postal address required]",
            applicant_contact=request.applicant_contact or "[Optional contact details]",
            public_authority=routing.likely_authority,
            subject=f"Records concerning {self._clean_issue(request.issue)}",
            information_requests=information_requests,
            location=location or "[Location/jurisdiction required]",
            date_range=self._known_text(request.date_range) or "the relevant period",
            citizenship_statement=(
                "I am a citizen of India."
                if request.is_indian_citizen is True
                else "[Confirm citizenship eligibility before filing.]"
            ),
        )
        document = self.drafter.draft_rti_application(context)
        status = "ready_for_review" if not missing else "needs_information"
        filename = self._filename(request.applicant_name)
        return RTIDraftResponse(
            status=status,
            routing=routing,
            information_requests=information_requests,
            missing_information=list(dict.fromkeys(missing)),
            document_text=document,
            download_filename=filename,
            filing_guidance=self.filing_guidance(request),
            disclaimer=(
                "This is an informational drafting aid, not legal advice. Authority, "
                "record custody, applicable fee, filing channel, and local RTI rules must "
                "be verified before filing. No individual PIO has been identified."
            ),
        )

    def filing_guidance(self, request: RTIIdentifyRequest | None = None) -> RTIFilingGuidance:
        """Return filing steps without treating the Central portal as a State portal."""
        request = request or RTIIdentifyRequest(issue="Request access to identifiable public records")
        authority_hint = self._known_text(request.authority_hint)
        state = self._known_text(request.state)
        hint_text = f"{authority_hint or ''} {request.issue}".casefold()
        looks_central = any(
            term in hint_text
            for term in ("central government", "union ministry", "government of india")
        )
        if looks_central:
            pathway = "central_public_authority"
            next_step = (
                "Verify the Central public authority, then review the draft before using "
                "the official RTI Online portal or the authority's accepted offline channel."
            )
            steps = [
                "Verify which Central public authority holds or controls each requested record.",
                "Review the information requests and remove questions that ask for opinions or grievance redressal.",
                "Use the official RTI Online portal only for participating Central public authorities, or verify the authority's accepted offline channel.",
                "Complete any fee or exemption step shown by the official channel; do not rely on an unverified fee stated by this assistant.",
                "Keep the acknowledgement and registration details for status checks or a first appeal.",
            ]
        elif state:
            pathway = "state_or_ut_public_authority"
            next_step = (
                f"Verify the relevant {state} public authority and its official "
                "State/UT RTI filing channel or accepted offline procedure."
            )
            steps = [
                "Verify which State/UT or local public authority holds or controls each requested record.",
                "Review the information requests and the address of the receiving public authority.",
                "Check the relevant State/UT government's official RTI rules, fee, and filing channel.",
                "Do not file a State/UT authority request through the Central RTI Online portal.",
                "Keep proof of filing and any registration or postal-delivery details.",
            ]
        else:
            pathway = "jurisdiction_required"
            next_step = "Provide the State/UT and whether the record belongs to a Central, State/UT, or local authority."
            steps = [
                "Identify the government service, programme, project, or office connected with the record.",
                "Provide the State/UT and local area where relevant.",
                "Verify which public authority holds or controls the requested records.",
                "Review the draft only after the authority and filing jurisdiction are narrowed.",
            ]

        return RTIFilingGuidance(
            pathway=pathway,
            steps=steps,
            next_step=next_step,
            warnings=[
                "The Central RTI Online portal states that it is not for State Government public authorities.",
                "Do not include Aadhaar numbers, bank details, passwords, or unrelated sensitive personal information in the request.",
                "Response time and any transfer or appeal route depend on the Act and the facts; verify current official guidance for the receiving authority.",
            ],
            sources=[RTI_ACT_SOURCE, RTI_ONLINE_SOURCE],
        )

    def template_catalogue(self) -> dict[str, Any]:
        """Expose reviewable record-request patterns and their verification status."""
        return {
            "status": self.metadata["status"],
            "notice": self.metadata["description"],
            "topics": [
                {
                    "id": record["id"],
                    "domain": record["domain"],
                    "authority_type": record["authority_type"],
                    "record_requests": record["record_requests"],
                }
                for record in self.records
            ],
            "source": RTI_ACT_SOURCE.model_dump(mode="json"),
        }

    def _matching_record(self, request: RTIIdentifyRequest) -> dict[str, Any]:
        authority_hint = self._known_text(request.authority_hint)
        road_type = self._known_text(request.road_type)
        searchable = f"{request.issue} {authority_hint or ''} {road_type or ''}".casefold()
        scored = [
            (sum(keyword.casefold() in searchable for keyword in record.get("keywords", [])), record)
            for record in self.records
        ]
        score, record = max(scored, key=lambda row: row[0])
        return record if score else self.fallback

    @staticmethod
    def _clean_issue(issue: str) -> str:
        cleaned = " ".join(issue.strip().split())
        cleaned = re.sub(r"^(why|how come)\s+", "", cleaned, flags=re.IGNORECASE)
        return cleaned.rstrip("?.!")

    @staticmethod
    def _known_text(value: object) -> str | None:
        """Return trimmed citizen input only when it is substantive."""
        if not JurisdictionCompleteness.is_known_value(value):
            return None
        return str(value).strip()

    @staticmethod
    def _field_is_present(field: str, request: RTIIdentifyRequest) -> bool:
        values = request.model_dump()
        known = JurisdictionCompleteness.is_known_value
        if field == "district_or_city":
            return known(request.district) or known(request.city)
        if field == "state_or_central":
            return known(request.state) or known(request.authority_hint)
        if field == "locality":
            return known(request.locality)
        if field == "road_type_or_controlling_authority":
            return known(request.road_type) or known(request.authority_hint)
        if field in {
            "service_or_asset",
            "government_service_or_programme",
            "institution_or_programme",
        }:
            return known(request.issue)
        if field in {
            "water_supplier_or_connection_details",
            "ration_card_or_fair_price_shop_details",
            "police_station_or_unit",
            "record_or_reference_number",
            "institution_or_scheme_name",
            "government_level",
            "tehsil_or_taluk",
            "property_or_record_identifier",
            "service_date_or_reference",
            "scheme_name",
            "application_or_beneficiary_reference",
            "office_previously_contacted",
        }:
            return known(request.authority_hint)
        return known(values.get(field))

    @staticmethod
    def _filename(applicant_name: str | None) -> str:
        suffix = re.sub(r"[^a-z0-9]+", "-", (applicant_name or "application").casefold()).strip("-")
        return f"rti-{suffix or 'application'}.txt"


@lru_cache(maxsize=1)
def get_rti_assistant() -> RTIAssistant:
    """Return the process-wide RTI assistant."""
    return RTIAssistant()
