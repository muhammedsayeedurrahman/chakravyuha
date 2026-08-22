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


def test_labour_query_uses_current_code_record() -> None:
    response = LegalService().query_civic(
        CivicLegalQueryRequest(
            query="My employer has not paid my salary and deducted wages",
            domain="labour",
        )
    )

    assert response.results[0].id == "labour-wages"
    assert response.results[0].effective_date == "2025-11-21"
    assert "Code on Wages" in response.results[0].source


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
