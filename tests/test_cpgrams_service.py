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
    assert result["intent"] == "government_service_grievance"
    assert result["workflow"] == "cpgrams"
    assert result["handoff"] is None
    assert result["handoff_state"] == "DRAFT"
    assert result["handoff_blockers"] == [
        "Provide the State or Union Territory.",
        "Provide either the district or city.",
        "Provide the locality or service location.",
        "Identify the public authority or office involved.",
        "Provide the incident date or period.",
        "State the desired resolution.",
        "Confirm whether the citizen has a CPGRAMS account.",
    ]
    assert result["classification"]["domain"] == "civic_infrastructure"
    assert result["classification"]["confidence"] in {"medium", "high"}
    assert result["authority"]["requires_verification"] is True
    assert "local body" in result["authority"]["candidate"].lower()
    assert "state_or_union_territory" in result["missing_information"]
    assert "district_or_city" in result["missing_information"]
    assert "locality_or_service_location" in result["missing_information"]
    assert result["jurisdiction_completeness"] == {
        "state_known": False,
        "district_known": False,
        "city_known": False,
        "locality_known": False,
        "authority_known": False,
    }
    assert "ministry_id" not in result["authority"]
    assert result["authority"]["provenance"]["source_url"].startswith("https://pgportal.gov.in")


def test_semantic_records_request_redirects_to_explicit_rti_handoff(service):
    result = service.prepare(
        "I want copies of records showing how much money was sanctioned and spent on "
        "repairing this road."
    )

    assert result["status"] == "not_suitable"
    assert result["intent"] == "information_request"
    assert result["workflow"] == "rti"
    assert result["handoff"] == {"journey": "rti", "handler": "rti_assistant"}
    assert result["handoff_state"] == "DRAFT"
    assert result["handoff_blockers"] == [
        "CPGRAMS review is unavailable: The official CPGRAMS portal states that RTI "
        "matters are not taken up for redress. Continue in the RTI workflow instead."
    ]
    assert result["classification"]["domain"] == "information_request"
    assert result["suitability"]["exclusion_category"] == "rti_matter"
    assert result["draft"] is None
    assert result["jurisdiction_completeness"]["state_known"] is False


@pytest.mark.parametrize(
    "narrative",
    [
        "Who was the contractor for this municipal road repair project?",
        "What was the sanctioned amount for repairing this municipal road?",
        "What work order was issued for this municipal road repair?",
        "Which inspection records exist for this municipal road repair?",
        "What contractor information is recorded for this municipal road?",
    ],
)
def test_question_form_record_requests_redirect_to_rti(service, narrative: str):
    result = service.prepare(narrative)

    assert result["intent"] == "information_request"
    assert result["workflow"] == "rti"
    assert result["handoff"] == {"journey": "rti", "handler": "rti_assistant"}
    assert result["draft"] is None


def test_semantic_road_repair_request_remains_cpgrams_grievance(service):
    result = service.prepare(
        "Please repair this road. I complained several times and no action was taken."
    )

    assert result["intent"] == "government_service_grievance"
    assert result["workflow"] == "cpgrams"
    assert result["handoff"] is None
    assert result["classification"]["domain"] == "civic_infrastructure"
    assert result["suitability"]["is_suitable"] is True
    assert result["draft"] is not None


@pytest.mark.parametrize(
    ("narrative", "intent", "workflow", "journey", "handler"),
    [
        (
            "My landlord refuses to return my security deposit after I moved out.",
            "rights_guidance",
            "rights_guidance",
            "rights",
            "rights_navigator",
        ),
        (
            "I am a student and want to know which government schemes I am eligible for.",
            "scheme_eligibility",
            "scheme_eligibility",
            "scheme_eligibility",
            "scheme_eligibility",
        ),
        (
            "My landlord assaulted me and stole my phone yesterday.",
            "criminal_incident",
            "criminal",
            "criminal",
            "smart_legal_pipeline",
        ),
        (
            "My landlord threatened to kill me yesterday.",
            "escalation",
            "criminal",
            "criminal",
            "smart_legal_pipeline",
        ),
        (
            "Explain IPC 304 punishment to me.",
            "section_lookup",
            "legal",
            "legal",
            "smart_legal_pipeline",
        ),
        (
            "Draft a police complaint because I was assaulted yesterday.",
            "complaint_draft",
            "complaint_draft",
            "complaint_draft",
            "complaint_drafter",
        ),
        (
            "A government officer assaulted me and the case is pending before a court.",
            "criminal_incident",
            "criminal",
            "criminal",
            "smart_legal_pipeline",
        ),
        (
            "Which government schemes can I get? The dispute is pending before the court.",
            "scheme_eligibility",
            "scheme_eligibility",
            "scheme_eligibility",
            "scheme_eligibility",
        ),
        (
            "My life is in danger. I am a government employee challenging my promotion.",
            "escalation",
            "criminal",
            "criminal",
            "smart_legal_pipeline",
        ),
        (
            "A colleague assaulted me. I am a government employee challenging my promotion.",
            "criminal_incident",
            "criminal",
            "criminal",
            "smart_legal_pipeline",
        ),
        (
            "Someone scammed me online and took my money.",
            "criminal_incident",
            "criminal",
            "criminal",
            "smart_legal_pipeline",
        ),
        (
            "Draft a police complaint: I am a government employee challenging my promotion.",
            "complaint_draft",
            "complaint_draft",
            "complaint_draft",
            "complaint_drafter",
        ),
        (
            "Which government scheme applies? I am a government employee challenging my promotion.",
            "scheme_eligibility",
            "scheme_eligibility",
            "scheme_eligibility",
            "scheme_eligibility",
        ),
    ],
)
def test_non_grievance_intents_cannot_enter_cpgrams_drafting(
    service,
    narrative: str,
    intent: str,
    workflow: str,
    journey: str,
    handler: str,
):
    result = service.prepare(
        narrative,
        state="Tamil Nadu",
        city="Chennai",
        locality="Ward 1",
        authority_hint="Office named by citizen",
        incident_date="August 2026",
        desired_resolution="Take the appropriate action.",
        cpgrams_account_status="registered",
    )

    assert result["status"] == "not_suitable"
    assert result["intent"] == intent
    assert result["workflow"] == workflow
    assert result["handoff"] == {"journey": journey, "handler": handler}
    assert result["handoff_state"] == "DRAFT"
    assert result["handoff_blockers"]
    assert result["draft"] is None


@pytest.mark.parametrize(
    ("narrative", "intent"),
    [
        ("What does contract law say about agreements?", "general"),
        ("Hello, how are you today?", "greeting"),
    ],
)
def test_generic_non_grievance_input_never_enters_cpgrams_drafting(
    service,
    narrative: str,
    intent: str,
):
    result = service.prepare(narrative)

    assert result["status"] == "not_suitable"
    assert result["intent"] == intent
    assert result["workflow"] == "legal"
    assert result["handoff"] == {
        "journey": "legal",
        "handler": "smart_legal_pipeline",
    }
    assert result["draft"] is None


@pytest.mark.parametrize(
    "narrative",
    [
        "The PHC refuses to give me essential medicines despite repeated complaints.",
        "My caste certificate application is stuck at the tehsil for six months.",
        "Garbage has not been collected from our street for three weeks.",
        "My pension stopped arriving in January and the office ignores me.",
        "The passport office lost my application and will not respond.",
        "The ration shop has been closed for a month.",
    ],
)
def test_common_public_service_failures_remain_cpgrams_grievances(
    service,
    narrative: str,
):
    result = service.prepare(narrative)

    assert result["intent"] == "government_service_grievance"
    assert result["workflow"] == "cpgrams"
    assert result["status"] == "needs_information"
    assert result["draft"] is not None


@pytest.mark.parametrize(
    "narrative",
    [
        "My PM-KISAN payment has not been received for three months.",
        "The Atal Pension Yojana pension payment is delayed and complaints were ignored.",
        "My PM-SYM application is stuck with no response.",
    ],
)
def test_scheme_delivery_failures_remain_cpgrams_grievances(
    service,
    narrative: str,
):
    result = service.prepare(narrative)

    assert result["intent"] == "government_service_grievance"
    assert result["workflow"] == "cpgrams"
    assert result["draft"] is not None


def test_city_satisfies_cpgrams_district_or_city_requirement(service):
    result = service.prepare(
        "Please repair this municipal road because earlier complaints were ignored.",
        state="Tamil Nadu",
        city="Chennai",
        locality="Ward 1",
        authority_hint="Municipal office named by the citizen",
        incident_date="January 2026 onward",
        desired_resolution="Repair the road and communicate the action taken.",
        cpgrams_account_status="registered",
    )

    assert result["status"] == "ready_for_review"
    assert result["handoff_state"] == "PREPARED"
    assert result["handoff_blockers"] == []
    assert "district_or_city" not in result["missing_information"]
    assert result["jurisdiction_completeness"] == {
        "state_known": True,
        "district_known": False,
        "city_known": True,
        "locality_known": True,
        "authority_known": True,
    }
    assert "Chennai" in result["draft"]["formatted_text"]


def test_missing_sentinels_cannot_bypass_cpgrams_handoff_prerequisites(service):
    result = service.prepare(
        "Please repair this municipal road because earlier complaints were ignored.",
        state="Tamil Nadu",
        city="unknown",
        locality="N/A",
        authority_hint="unknown",
        incident_date="not known",
        desired_resolution="not_applicable",
        cpgrams_account_status="registered",
    )

    assert result["status"] == "needs_information"
    assert result["handoff_state"] == "DRAFT"
    assert result["missing_information"] == [
        "district_or_city",
        "locality_or_service_location",
        "public_authority_or_office_involved",
        "incident_date_or_period",
        "desired_resolution",
    ]
    assert result["handoff_blockers"] == [
        "Provide either the district or city.",
        "Provide the locality or service location.",
        "Identify the public authority or office involved.",
        "Provide the incident date or period.",
        "State the desired resolution.",
    ]
    assert result["jurisdiction_completeness"] == {
        "state_known": True,
        "district_known": False,
        "city_known": False,
        "locality_known": False,
        "authority_known": False,
    }


def test_hyphenated_and_punctuated_missing_sentinels_cannot_prepare_handoff(service):
    result = service.prepare(
        "Please repair this municipal road because earlier complaints were ignored.",
        state="Tamil Nadu",
        city="not-applicable",
        locality="N/A.",
        authority_hint="unknown.",
        incident_date="not-applicable",
        desired_resolution="not_applicable.",
        cpgrams_account_status="registered",
    )

    assert result["status"] == "needs_information"
    assert result["handoff_state"] == "DRAFT"
    assert result["missing_information"] == [
        "district_or_city",
        "locality_or_service_location",
        "public_authority_or_office_involved",
        "incident_date_or_period",
        "desired_resolution",
    ]
    assert len(result["handoff_blockers"]) == 5


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
    assert result["handoff_state"] == "PREPARED"
    assert result["handoff_blockers"] == []
    assert result["jurisdiction_completeness"]["state_known"] is True
    assert result["jurisdiction_completeness"]["district_known"] is True
    assert result["jurisdiction_completeness"]["city_known"] is False
    assert result["jurisdiction_completeness"]["authority_known"] is True
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
    assert result["handoff_state"] == "DRAFT"
    assert len(result["handoff_blockers"]) == 1
    assert result["suitability"]["reason"] in result["handoff_blockers"][0]
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
