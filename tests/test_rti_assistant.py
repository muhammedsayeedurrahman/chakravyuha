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
