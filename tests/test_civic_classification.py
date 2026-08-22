"""Classification and safe-response tests for civic/legal journeys."""

import pytest

from backend.agent.intent_classifier import (
    INTENT_CIVIC_QUERY,
    INTENT_COMPLAINT_DRAFT,
    INTENT_CPGRAMS,
    INTENT_RTI,
    INTENT_SCHEME_ELIGIBILITY,
    classify_intent,
)
from backend.agent.orchestrator import Orchestrator
from backend.services.classifier import classify
from backend.services.response_engine import get_response


@pytest.mark.parametrize(
    ("query", "scenario"),
    [
        ("Help me draft an RTI", "rti"),
        ("Am I eligible for a government scheme?", "scheme_eligibility"),
        ("I need to lodge a government grievance on CPGRAMS", "cpgrams"),
        ("The public road needs repair", "civic_service"),
        ("My landlord is withholding my deposit", "tenant_landlord"),
        ("My salary has not been paid", "employment_issue"),
        ("The seller refused a refund", "consumer_complaint"),
    ],
)
def test_scenario_classifier_covers_civic_domains(query: str, scenario: str) -> None:
    assert classify(query).scenario == scenario


@pytest.mark.parametrize(
    ("query", "intent", "journey"),
    [
        ("Draft an RTI for road repair records", INTENT_RTI, "rti"),
        ("Which government scheme can I get?", INTENT_SCHEME_ELIGIBILITY, "scheme_eligibility"),
        ("I want to file a CPGRAMS grievance", INTENT_CPGRAMS, "cpgrams"),
        ("There is a pothole on the municipal road", INTENT_CIVIC_QUERY, "civic"),
    ],
)
def test_agent_intent_classifier_routes_civic_workflows(
    query: str, intent: str, journey: str
) -> None:
    result = classify_intent(query)

    assert result.intent == intent
    assert result.entities["journey"] == journey
    assert result.method == "regex"


def test_existing_complaint_draft_intent_is_preserved() -> None:
    assert classify_intent("Please draft a police complaint").intent == INTENT_COMPLAINT_DRAFT


def test_agent_routes_civic_intent_to_typed_handoff_without_rag() -> None:
    orchestrator = object.__new__(Orchestrator)

    result = orchestrator.process_text_input("Help me draft an RTI", {})

    assert result["handoff"]["journey"] == "rti"
    assert result["handoff"]["handler"] == "rti_assistant"
    assert result["sections"] == []


@pytest.mark.parametrize(
    "scenario",
    [
        "consumer_complaint",
        "tenant_landlord",
        "employment_issue",
        "rti",
        "scheme_eligibility",
        "cpgrams",
        "civic_service",
    ],
)
def test_civic_scenarios_have_conservative_responses(scenario: str) -> None:
    response = get_response(scenario)

    assert response is not None
    assert response.guidance
    assert response.outcome


def test_legacy_canned_responses_no_longer_assert_unsafe_limits_or_deadlines() -> None:
    consumer = get_response("consumer_complaint")
    labour = get_response("employment_issue")
    tenant = get_response("tenant_landlord")
    rti = get_response("rti")

    combined = "\n".join(
        [consumer.guidance, labour.guidance, tenant.guidance, rti.guidance, rti.outcome]
    )
    assert "Rs 1 crore" not in combined
    assert "15 days" not in combined
    assert "within 3 months" not in combined
    assert "Rs 250/day" not in combined
    assert "requires verification" in combined.lower()
