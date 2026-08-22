"""Tests for provenance-aware consumer, tenant, and labour retrieval."""

from backend.legal.corpus_loader import CorpusLoader
from backend.legal.hybrid_retriever import HybridRetriever
from backend.models.schemas import CivicLegalQueryRequest, ConfidenceLevel, KnowledgeStatus
from backend.services.legal_service import LegalService


def test_civic_corpus_loads_separate_domains_with_provenance() -> None:
    records = CorpusLoader.load_civic_records()

    assert {record.domain for record in records} == {"consumer", "tenant", "labour"}
    assert all(record.source_url.startswith("https://") for record in records)
    assert all(record.last_verified for record in records)
    assert all(record.document_type for record in records)


def test_consumer_query_returns_consumer_records_only() -> None:
    response = LegalService().query_civic(
        CivicLegalQueryRequest(
            query="The seller refuses a refund for a defective product",
            domain="consumer",
        )
    )

    assert response.results
    assert all(result.domain == "consumer" for result in response.results)
    assert response.results[0].source
    assert response.results[0].source_url.startswith("https://")
    assert response.missing_information == []
    assert response.jurisdiction_completeness.model_dump() == {
        "state_known": False,
        "district_known": False,
        "city_known": False,
        "locality_known": False,
        "authority_known": False,
    }


def test_tenant_query_requires_state_or_ut() -> None:
    response = LegalService().query_civic(
        CivicLegalQueryRequest(
            query="My landlord is threatening eviction and withholding my deposit",
            domain="tenant",
        )
    )

    assert response.confidence == ConfidenceLevel.REQUIRES_JURISDICTION
    assert response.status == KnowledgeStatus.REQUIRES_JURISDICTION
    assert response.missing_information
    assert "State" in response.missing_information[0]
    assert response.jurisdiction_completeness.state_known is False
    assert any("State or Union Territory" in step for step in response.next_steps)


def test_tenant_missing_state_sentinel_is_still_requested() -> None:
    response = LegalService().query_civic(
        CivicLegalQueryRequest(
            query="My landlord is withholding my security deposit",
            domain="tenant",
            state="unknown",
            city="N/A",
        )
    )

    assert response.jurisdiction is None
    assert response.jurisdiction_completeness.state_known is False
    assert response.jurisdiction_completeness.city_known is False
    assert response.missing_information == [
        "State or Union Territory where the rented premises are located"
    ]


def test_tenant_query_with_jurisdiction_is_still_cautious() -> None:
    response = LegalService().query_civic(
        CivicLegalQueryRequest(
            query="My landlord is threatening eviction and withholding my deposit",
            domain="tenant",
            jurisdiction="Karnataka",
        )
    )

    assert response.confidence == ConfidenceLevel.MEDIUM
    assert response.status == KnowledgeStatus.REQUIRES_VERIFICATION
    assert response.missing_information == []
    assert all(result.status == KnowledgeStatus.REQUIRES_JURISDICTION for result in response.results)
    assert response.jurisdiction_completeness.state_known is True
    assert response.jurisdiction_completeness.city_known is False
    assert "Karnataka identified; city/local jurisdiction may still be required" in response.answer
    assert "Provide the State or Union Territory" not in response.answer
    assert all("Provide the State or Union Territory" not in step for step in response.next_steps)


def test_tenant_explicit_state_does_not_reask_state_when_city_is_unknown() -> None:
    response = LegalService().query_civic(
        CivicLegalQueryRequest(
            query="My landlord refuses to return my security deposit",
            domain="tenant",
            state="Tamil Nadu",
        )
    )

    expected = "Tamil Nadu identified; city/local jurisdiction may still be required"
    assert response.jurisdiction == "Tamil Nadu"
    assert response.jurisdiction_completeness.state_known is True
    assert response.jurisdiction_completeness.city_known is False
    assert response.missing_information == []
    assert expected in response.answer
    assert expected in response.next_steps[0]
    assert "Provide the State or Union Territory" not in response.answer
    assert all("Provide the State or Union Territory" not in step for step in response.next_steps)


def test_labour_query_uses_current_code_record() -> None:
    response = LegalService().query_civic(
        CivicLegalQueryRequest(
            query="My employer has not paid my salary and deducted wages",
            domain="labour",
            state="Tamil Nadu",
            city="Chennai",
        )
    )

    assert response.results[0].id == "labour-wages"
    assert response.results[0].effective_date == "2025-11-21"
    assert "Code on Wages" in response.results[0].source
    assert response.missing_information == []
    assert response.jurisdiction_completeness.state_known is True
    assert response.jurisdiction_completeness.city_known is True
    assert response.jurisdiction_completeness.district_known is False


def test_jurisdiction_filter_never_leaks_another_states_rule() -> None:
    records = [
        {"id": "general", "jurisdiction": "India"},
        {"id": "warning", "jurisdiction": "State/UT-specific"},
        {"id": "ka", "jurisdiction": "Karnataka"},
        {"id": "mh", "jurisdiction": "Maharashtra"},
    ]

    filtered = HybridRetriever.filter_civic_records(records, "Karnataka")
    assert {record["id"] for record in filtered} == {"general", "warning", "ka"}

    without_state = HybridRetriever.filter_civic_records(records, None)
    assert {record["id"] for record in without_state} == {"general", "warning"}
