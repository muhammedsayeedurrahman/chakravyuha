"""Focused tests for deterministic CPGRAMS grievance preparation."""

from __future__ import annotations

import pytest

from backend.services.cpgrams_service import CPGRAMSService


@pytest.fixture()
def service() -> CPGRAMSService:
    return CPGRAMSService()


def test_road_grievance_routes_broadly_and_requests_jurisdiction(service):
    result = service.prepare(
        "The road outside our colony has had dangerous potholes for six months."
    )

    assert result["status"] == "needs_information"
    assert result["classification"]["domain"] == "civic_infrastructure"
    assert result["classification"]["confidence"] in {"medium", "high"}
    assert result["authority"]["requires_verification"] is True
    assert "local body" in result["authority"]["candidate"].lower()
    assert "state_or_union_territory" in result["missing_information"]
    assert "district_or_city" in result["missing_information"]
    assert "locality_or_service_location" in result["missing_information"]
    assert "ministry_id" not in result["authority"]
    assert result["authority"]["provenance"]["source_url"].startswith("https://pgportal.gov.in")


def test_complete_context_produces_reviewable_structured_draft(service):
    result = service.prepare(
        "My pension payment has remained unpaid since January despite two written reminders.",
        state="Karnataka",
        district="Bengaluru Urban",
        authority_hint="The pension office shown on my sanction letter",
        incident_date="January 2026 onward",
        prior_steps=["Submitted written reminder on 10 February 2026"],
        prior_reference="ACK-USER-SUPPLIED-1",
        desired_resolution="Release the pending pension and explain the delay.",
        evidence=["Pension sanction letter", "Reminder acknowledgement"],
        cpgrams_account_status="registered",
    )

    assert result["status"] == "ready_for_review"
    assert result["missing_information"] == []
    assert result["authority"]["authority_hint_status"] == "user_supplied_requires_verification"
    assert result["draft"]["subject"].startswith("Grievance regarding")
    assert "Release the pending pension" in result["draft"]["relief_requested"][0]
    assert result["draft"]["evidence"] == [
        "Pension sanction letter",
        "Reminder acknowledgement",
    ]
    assert "ACK-USER-SUPPLIED-1" in result["draft"]["formatted_text"]


def test_ambiguous_narrative_exposes_low_confidence(service):
    result = service.prepare(
        "A government service application has not moved and I have received no response."
    )

    assert result["classification"]["domain"] == "general_public_service"
    assert result["classification"]["confidence"] == "low"
    assert result["authority"]["confidence"] == "low"
    assert result["suitability"]["requires_verification"] is True


@pytest.mark.parametrize(
    ("narrative", "category"),
    [
        ("I want to file an RTI request for copies of records.", "rti_matter"),
        (
            "My dispute is pending before the court and I want CPGRAMS to overturn it.",
            "court_or_sub_judice",
        ),
        (
            "I am a government employee challenging my promotion and seniority decision.",
            "government_employee_service_matter",
        ),
    ],
)
def test_official_exclusions_are_flagged(service, narrative, category):
    result = service.prepare(narrative)

    assert result["status"] == "not_suitable"
    assert result["suitability"]["is_suitable"] is False
    assert result["suitability"]["exclusion_category"] == category
    assert result["draft"] is None


def test_filing_and_tracking_guidance_has_official_provenance(service):
    guide = service.get_filing_guide()

    assert guide["portal_url"] == "https://pgportal.gov.in/"
    assert guide["status_url"] == "https://pgportal.gov.in/Status"
    assert "does not charge" in guide["fee_note"]
    assert "email" in guide["email_note"].lower()
    assert {"OTP", "CAPTCHA", "final review and explicit submission confirmation"}.issubset(
        set(guide["human_actions_required"])
    )
    assert all(source["source_type"].startswith("official") for source in guide["provenance"])


def test_government_employee_exclusion_respects_exhausted_channels_condition(service):
    result = service.prepare(
        "I am a government employee challenging a promotion decision after all prescribed "
        "departmental channels have been exhausted."
    )

    assert result["status"] != "not_suitable"
    assert result["suitability"]["is_suitable"] is True
    assert result["suitability"]["requires_verification"] is True


def test_too_short_narrative_is_rejected(service):
    with pytest.raises(ValueError, match="at least 10"):
        service.prepare("pothole")
