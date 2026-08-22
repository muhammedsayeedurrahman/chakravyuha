"""Focused tests for RTI routing, drafting, and source-aware guidance."""

from backend.legal.rti_assistant import RTIAssistant
from backend.models.schemas import ConfidenceLevel, RTIDraftRequest, RTIIdentifyRequest


def test_road_routing_asks_for_missing_jurisdiction() -> None:
    result = RTIAssistant().identify_department(
        RTIIdentifyRequest(issue="My road has not been repaired for two years")
    )

    assert result.domain == "Roads / public works"
    assert result.confidence == ConfidenceLevel.REQUIRES_JURISDICTION
    assert "State or Union Territory" in result.missing_information
    assert result.jurisdiction_completeness.model_dump() == {
        "state_known": False,
        "district_known": False,
        "city_known": False,
        "locality_known": False,
        "authority_known": False,
    }
    assert "Public Works Department" not in result.likely_authority


def test_routing_remains_review_required_after_jurisdiction() -> None:
    result = RTIAssistant().identify_department(
        RTIIdentifyRequest(
            issue="Potholes on our municipal road have not been repaired",
            state="Delhi",
            city="Delhi",
            locality="Ward 1",
            road_type="municipal road",
        )
    )

    assert result.confidence == ConfidenceLevel.MEDIUM
    assert result.status.value == "requires_verification"
    assert result.missing_information == []
    assert result.jurisdiction_completeness.state_known is True
    assert result.jurisdiction_completeness.district_known is False
    assert result.jurisdiction_completeness.city_known is True
    assert result.jurisdiction_completeness.locality_known is True
    assert result.jurisdiction_completeness.authority_known is False


def test_state_is_retained_while_only_other_required_rti_location_is_requested() -> None:
    result = RTIAssistant().identify_department(
        RTIIdentifyRequest(
            issue="I want road repair work-order and expenditure records",
            state="Tamil Nadu",
        )
    )

    assert result.jurisdiction_completeness.state_known is True
    assert result.jurisdiction_completeness.city_known is False
    assert "State or Union Territory" not in result.missing_information
    assert "District or city" in result.missing_information


def test_rti_missing_sentinels_are_not_treated_as_jurisdiction() -> None:
    result = RTIAssistant().identify_department(
        RTIIdentifyRequest(
            issue="I want road repair work-order and expenditure records",
            state="unknown",
            city="N/A",
            locality="not known",
            authority_hint="not_applicable",
        )
    )

    assert result.jurisdiction_completeness.model_dump() == {
        "state_known": False,
        "district_known": False,
        "city_known": False,
        "locality_known": False,
        "authority_known": False,
    }
    assert "State or Union Territory" in result.missing_information
    assert "District or city" in result.missing_information
    assert "Locality and identifiable location" in result.missing_information


def test_rti_missing_sentinels_never_leak_into_routing_or_draft() -> None:
    draft = RTIAssistant().prepare_draft(
        RTIDraftRequest(
            issue="I need municipal sanitation service records for my street",
            state="unknown",
            district="   ",
            city="N/A",
            locality="not known",
            authority_hint="not_applicable",
            road_type="none",
            date_range="do not know",
            applicant_name="A Citizen",
            applicant_address="Address supplied separately",
            is_indian_citizen=True,
        )
    )

    assert draft.status == "needs_information"
    assert not draft.routing.likely_authority.startswith("Citizen-provided candidate:")
    assert draft.filing_guidance.pathway == "jurisdiction_required"
    assert "the specified location" in " ".join(draft.information_requests)
    assert "the relevant period" in " ".join(draft.information_requests)
    assert "Relevant location: [Location/jurisdiction required]" in draft.document_text
    assert "Relevant period: the relevant period" in draft.document_text

    rendered = " ".join(
        [
            draft.routing.likely_authority,
            draft.routing.reason,
            *draft.information_requests,
            draft.document_text,
            draft.filing_guidance.next_step,
            *draft.filing_guidance.steps,
        ]
    ).casefold()
    for sentinel in ("unknown", "n/a", "not known", "not_applicable", "do not know"):
        assert sentinel not in rendered


def test_grievance_is_transformed_into_requests_for_records() -> None:
    requests = RTIAssistant().propose_information_requests(
        RTIIdentifyRequest(
            issue="Why have you failed to repair my road?",
            state="Delhi",
            city="Delhi",
            locality="Ward 1",
            road_type="municipal road",
            date_range="1 January 2024 to 31 December 2025",
        )
    )

    joined = " ".join(requests).casefold()
    assert "work order" in joined
    assert "inspection" in joined
    assert "why have you failed" not in joined


def test_complete_draft_reuses_document_drafter() -> None:
    draft = RTIAssistant().prepare_draft(
        RTIDraftRequest(
            issue="Please provide records about repairs to the road near my home",
            state="Delhi",
            city="Delhi",
            locality="Ward 1",
            road_type="municipal road",
            date_range="calendar year 2025",
            applicant_name="A Citizen",
            applicant_address="Ward 1, Delhi",
            is_indian_citizen=True,
        )
    )

    assert draft.status == "ready_for_review"
    assert "RIGHT TO INFORMATION APPLICATION" in draft.document_text
    assert "section 6(1)" in draft.document_text
    assert "Why" not in draft.document_text
    assert draft.download_filename == "rti-a-citizen.txt"


def test_draft_exposes_missing_applicant_and_location_fields() -> None:
    draft = RTIAssistant().prepare_draft(
        RTIDraftRequest(issue="I need the file records for my pending government application")
    )

    assert draft.status == "needs_information"
    assert "Applicant name" in draft.missing_information
    assert "Applicant postal address" in draft.missing_information
    assert draft.routing.confidence == ConfidenceLevel.REQUIRES_JURISDICTION


def test_state_guidance_does_not_direct_user_to_central_portal() -> None:
    guidance = RTIAssistant().filing_guidance(
        RTIIdentifyRequest(
            issue="I need municipal sanitation records",
            state="Karnataka",
        )
    )

    assert guidance.pathway == "state_or_ut_public_authority"
    assert any("Do not file" in step for step in guidance.steps)
    assert all(source.source_url.startswith("https://") for source in guidance.sources)
