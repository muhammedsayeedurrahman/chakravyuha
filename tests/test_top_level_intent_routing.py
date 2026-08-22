"""Regression tests for the shared router used by the browser smart-query path."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.agent.intent_classifier import (
    INTENT_INFORMATION_REQUEST,
    INTENT_LEGAL_QUERY,
    IntentResult,
    civic_handoff_for,
    is_automatic_civic_handoff,
)
from backend.controllers import pipeline
from backend.main import app


client = TestClient(app)


@pytest.mark.parametrize(
    ("query", "intent", "workflow", "domain", "journey"),
    [
        (
            "I want copies of records showing how much money was sanctioned and spent on repairing this road.",
            "information_request",
            "rti",
            None,
            "rti",
        ),
        (
            "My municipal road has not been repaired for two years. I have complained several times but nothing happened.",
            "government_service_grievance",
            "cpgrams",
            None,
            "cpgrams",
        ),
        (
            "My landlord refuses to return my security deposit. What can I do?",
            "rights_guidance",
            "rights_guidance",
            "tenant",
            "rights",
        ),
        (
            "I bought a defective phone and the seller refuses to replace or refund it.",
            "rights_guidance",
            "rights_guidance",
            "consumer",
            "rights",
        ),
        (
            "My employer hasn't paid my salary for three months.",
            "rights_guidance",
            "rights_guidance",
            "labour",
            "rights",
        ),
        (
            "I am a 21-year-old student looking for government schemes.",
            "scheme_eligibility",
            "scheme_eligibility",
            None,
            "scheme_eligibility",
        ),
    ],
)
def test_smart_query_hands_noncriminal_intents_to_existing_workflows(
    query: str,
    intent: str,
    workflow: str,
    domain: str | None,
    journey: str,
) -> None:
    response = client.post("/api/smart-query", json={"query": query})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == intent
    assert body["workflow"] == workflow
    assert body["domain"] == domain
    assert body["handoff"]["journey"] == journey
    assert body["sections"] == []
    assert body["source"] == "intent_router"
    assert body["routing_confidence"] >= 0.8
    assert body["automatic_handoff"] is True


def test_smart_query_keeps_genuine_criminal_incident_on_existing_pipeline() -> None:
    response = client.post(
        "/api/smart-query",
        json={"query": "Someone broke into my home and stole my laptop."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "criminal_incident"
    assert body["workflow"] == "criminal"
    assert body["handoff"] is None
    assert body["source"] != "intent_router"
    assert body["automatic_handoff"] is False


def test_low_confidence_or_unmapped_intent_cannot_auto_handoff() -> None:
    low_confidence = IntentResult(
        intent=INTENT_INFORMATION_REQUEST,
        confidence=0.79,
        method="test",
        entities={"journey": "rti", "workflow": "rti"},
    )
    low_confidence_handoff = civic_handoff_for(low_confidence)

    assert low_confidence_handoff is not None
    assert is_automatic_civic_handoff(low_confidence, low_confidence_handoff) is False

    unmapped = IntentResult(
        intent=INTENT_LEGAL_QUERY,
        confidence=0.99,
        method="test",
    )
    assert civic_handoff_for(unmapped) is None
    assert is_automatic_civic_handoff(unmapped, None) is False


def test_topic_does_not_override_requested_action() -> None:
    grievance = client.post(
        "/api/smart-query",
        json={"query": "Please repair this road. I complained several times and no action was taken."},
    ).json()
    records = client.post(
        "/api/smart-query",
        json={"query": "Please provide copies of road work orders and expenditure records."},
    ).json()

    assert grievance["intent"] == "government_service_grievance"
    assert grievance["workflow"] == "cpgrams"
    assert records["intent"] == "information_request"
    assert records["workflow"] == "rti"


def test_non_english_input_uses_translation_before_top_level_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    translation_calls: list[tuple[str, str]] = []

    async def fake_translate(text: str, source_lang: str) -> str:
        translation_calls.append((text, source_lang))
        return (
            "My municipal road has not been repaired for two years. "
            "I complained several times and nothing happened."
        )

    async def keep_response(response: object, target_lang: str) -> object:
        assert target_lang == "hi-IN"
        return response

    monkeypatch.setattr(pipeline, "translate_to_english", fake_translate)
    monkeypatch.setattr(pipeline, "translate_smart_response", keep_response)
    pipeline.get_pipeline_cache().clear()

    response = asyncio.run(
        pipeline.process_query(
            "नगरपालिका की सड़क दो साल से ठीक नहीं हुई है।",
            language="hi-IN",
        )
    )

    assert response.intent == "government_service_grievance"
    assert response.workflow == "cpgrams"
    assert response.handoff["journey"] == "cpgrams"
    assert len(translation_calls) == 1
