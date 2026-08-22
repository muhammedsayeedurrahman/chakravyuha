"""Classification and safe-response tests for civic/legal journeys."""

import pytest

from backend.agent.intent_classifier import (
    INTENT_CIVIC_QUERY,
    INTENT_COMPLAINT_DRAFT,
    INTENT_CPGRAMS,
    INTENT_CRIMINAL_INCIDENT,
    INTENT_GOVERNMENT_SERVICE_GRIEVANCE,
    INTENT_INFORMATION_REQUEST,
    INTENT_RTI,
    INTENT_RIGHTS_GUIDANCE,
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
        ("There is a pothole on the municipal road", INTENT_CPGRAMS, "cpgrams"),
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
    ("query", "intent", "workflow", "domain"),
    [
        (
            "I want copies of records showing how much money was sanctioned and spent on repairing this road.",
            INTENT_INFORMATION_REQUEST,
            "rti",
            None,
        ),
        (
            "My municipal road has not been repaired for two years. I have complained several times but nothing happened.",
            INTENT_GOVERNMENT_SERVICE_GRIEVANCE,
            "cpgrams",
            None,
        ),
        (
            "My landlord refuses to return my security deposit. What can I do?",
            INTENT_RIGHTS_GUIDANCE,
            "rights_guidance",
            "tenant",
        ),
        (
            "I bought a defective phone and the seller refuses to replace or refund it.",
            INTENT_RIGHTS_GUIDANCE,
            "rights_guidance",
            "consumer",
        ),
        (
            "My employer hasn't paid my salary for three months.",
            INTENT_RIGHTS_GUIDANCE,
            "rights_guidance",
            "labour",
        ),
        (
            "Someone broke into my home and stole my laptop.",
            INTENT_CRIMINAL_INCIDENT,
            "criminal",
            None,
        ),
    ],
)
def test_top_level_router_uses_requested_action_before_topic(
    query: str, intent: str, workflow: str, domain: str | None
) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == intent
    assert result.entities.get("workflow") == workflow
    assert result.entities.get("domain") == domain


@pytest.mark.parametrize(
    "query",
    [
        "My landlord assaulted me and stole my phone.",
        "The seller assaulted me when I asked for a refund.",
    ],
)
def test_genuine_crime_outranks_rights_topic_words(query: str) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == INTENT_CRIMINAL_INCIDENT
    assert result.entities["workflow"] == "criminal"


@pytest.mark.parametrize(
    "query",
    [
        "Who was the contractor for this road repair?",
        "What was the sanctioned amount for the road?",
        "What work order was issued for this road repair?",
        "Which inspection records exist for this road repair?",
        "What contractor information is recorded for this road?",
        "I want copies of police records about a murder.",
        "I want records relating to IPC 304 cases.",
    ],
)
def test_question_form_public_record_requests_route_to_rti(query: str) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == INTENT_INFORMATION_REQUEST
    assert result.entities["workflow"] == "rti"


@pytest.mark.parametrize(
    "query",
    [
        "I need copies of my pension payment records.",
        "Please provide the ration shop inspection records.",
        "I want records of my PM-KISAN payments.",
        "Give me copies of passport office file notings.",
        "I need documents showing why my caste certificate is delayed.",
        "Which pension payment records are available?",
        "What records exist for my PM-KISAN payments?",
        "Where can I find passport office file notings?",
    ],
)
def test_public_record_action_outranks_service_or_scheme_topic(query: str) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == INTENT_INFORMATION_REQUEST
    assert result.entities["workflow"] == "rti"


def test_scheme_application_document_requirements_remain_scheme_guidance() -> None:
    result = classify_intent(
        "Which documents are required for applying to PM-KISAN?",
        allow_llm_fallback=False,
    )

    assert result.intent == INTENT_SCHEME_ELIGIBILITY


@pytest.mark.parametrize(
    "query",
    [
        "What documents do I need for a caste certificate?",
        "Which documents do I need for my pension?",
    ],
)
def test_public_service_application_requirements_do_not_route_to_rti(query: str) -> None:
    assert classify_intent(query, allow_llm_fallback=False).intent != INTENT_INFORMATION_REQUEST


def test_emergency_without_record_seeking_still_escalates() -> None:
    result = classify_intent(
        "There is a gun and my life is in danger right now.",
        allow_llm_fallback=False,
    )

    assert result.intent == "escalation"


@pytest.mark.parametrize(
    ("query", "intent", "domain"),
    [
        ("How do I get a private contract reviewed?", "general", None),
        ("I need documents for my consumer complaint.", INTENT_RIGHTS_GUIDANCE, "consumer"),
        ("A man mugged me and snatched my bag.", INTENT_CRIMINAL_INCIDENT, None),
        ("My neighbour vandalised my car.", INTENT_CRIMINAL_INCIDENT, None),
        ("Someone forged my signature and withdrew money.", INTENT_CRIMINAL_INCIDENT, None),
        ("My husband hit me last night.", INTENT_CRIMINAL_INCIDENT, None),
        ("A PM-KISAN official assaulted me at the office.", INTENT_CRIMINAL_INCIDENT, None),
        ("I was robbed while applying for a government scheme.", INTENT_CRIMINAL_INCIDENT, None),
        ("The Atal Pension Yojana agent stole my money.", INTENT_CRIMINAL_INCIDENT, None),
        (
            "My landlord ignored my complaints about the public road; please repair it.",
            INTENT_GOVERNMENT_SERVICE_GRIEVANCE,
            None,
        ),
        (
            "My employer at a government hospital has not paid my salary for three months.",
            INTENT_RIGHTS_GUIDANCE,
            "labour",
        ),
        (
            "The public transport employer has not paid my wages.",
            INTENT_RIGHTS_GUIDANCE,
            "labour",
        ),
        ("Someone attacked me at a CPGRAMS office.", INTENT_CRIMINAL_INCIDENT, None),
        ("Someone scammed me online and took my money.", INTENT_CRIMINAL_INCIDENT, None),
        ("A broker defrauded me of five lakh rupees.", INTENT_CRIMINAL_INCIDENT, None),
        ("My husband slapped me last night.", INTENT_CRIMINAL_INCIDENT, None),
        (
            "A man threatened me with a knife and demanded money.",
            INTENT_CRIMINAL_INCIDENT,
            None,
        ),
        ("Someone set fire to my shop deliberately.", INTENT_CRIMINAL_INCIDENT, None),
        ("A stranger is stalking me every day.", INTENT_CRIMINAL_INCIDENT, None),
    ],
)
def test_action_precedence_and_private_record_boundaries(
    query: str,
    intent: str,
    domain: str | None,
) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == intent
    assert result.entities.get("domain") == domain


@pytest.mark.parametrize(
    "query",
    [
        "The PHC refuses to give me essential medicines despite repeated complaints.",
        "My caste certificate application is stuck at the tehsil for six months.",
        "Garbage has not been collected from our street for three weeks.",
        "My pension stopped arriving in January and the office ignores me.",
        "The passport office lost my application and will not respond.",
        "The ration shop has been closed for a month.",
    ],
)
def test_common_public_service_failures_route_to_cpgrams(query: str) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == INTENT_GOVERNMENT_SERVICE_GRIEVANCE
    assert result.entities["workflow"] == "cpgrams"


@pytest.mark.parametrize(
    "query",
    [
        "My PM-KISAN payment has not been received for three months.",
        "The Atal Pension Yojana pension payment is delayed and complaints were ignored.",
        "My PM-SYM application is stuck with no response.",
    ],
)
def test_scheme_service_failures_route_to_cpgrams_redress(query: str) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == INTENT_GOVERNMENT_SERVICE_GRIEVANCE
    assert result.entities["workflow"] == "cpgrams"


@pytest.mark.parametrize(
    "query",
    [
        "Am I eligible for PM-KISAN?",
        "Which government schemes can I get?",
        "I am a student looking for government schemes.",
    ],
)
def test_explicit_scheme_discovery_remains_scheme_eligibility(query: str) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == INTENT_SCHEME_ELIGIBILITY


@pytest.mark.parametrize(
    "query",
    [
        "I need the inspection report for my used car.",
        "Please show the tender document from our private company.",
    ],
)
def test_private_records_do_not_route_to_rti(query: str) -> None:
    assert classify_intent(query, allow_llm_fallback=False).intent != INTENT_INFORMATION_REQUEST


def test_immediate_danger_outranks_a_simultaneous_records_request() -> None:
    result = classify_intent(
        "My life is in danger right now and I need copies of police records.",
        allow_llm_fallback=False,
    )

    assert result.intent == "escalation"


@pytest.mark.parametrize(
    "query",
    [
        "Draft a police complaint because I was assaulted yesterday.",
        "Please draft a legal notice to my landlord for my security deposit.",
    ],
)
def test_explicit_drafting_action_outranks_incident_or_rights_topic(query: str) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == INTENT_COMPLAINT_DRAFT


def test_definitional_civic_topic_is_not_treated_as_grievance() -> None:
    result = classify_intent("What is a pothole?", allow_llm_fallback=False)

    assert result.intent != INTENT_GOVERNMENT_SERVICE_GRIEVANCE


@pytest.mark.parametrize(
    ("query", "domain"),
    [
        ("My lease has been terminated without notice.", "tenant"),
        ("My rent was increased illegally.", "tenant"),
        ("The service provider refuses to refund me.", "consumer"),
        ("I paid for a product but cannot get a refund.", "consumer"),
        ("My EPF contribution was deducted but not deposited.", "labour"),
        ("I was retrenched without notice.", "labour"),
        ("I need help under POSH at work.", "labour"),
    ],
)
def test_shared_rights_domain_inference_preserves_existing_vocabulary(
    query: str,
    domain: str,
) -> None:
    result = classify_intent(query, allow_llm_fallback=False)

    assert result.intent == INTENT_RIGHTS_GUIDANCE
    assert result.entities["domain"] == domain
    assert result.entities["workflow"] == "rights_guidance"


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
