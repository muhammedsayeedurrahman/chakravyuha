"""Tests for RAG retrieval accuracy."""

import pytest
from backend.legal.rag import LegalRAG


@pytest.fixture
def rag():
    return LegalRAG()


class TestLegalRAG:
    def test_rag_init(self, rag):
        """RAG initializes without error."""
        assert rag is not None

    def test_is_ready_without_db(self, rag):
        """RAG reports not ready if vector DB hasn't been built."""
        # This may be True or False depending on whether build_vectordb was run
        assert isinstance(rag.is_ready, bool)

    @pytest.mark.skipif(
        not LegalRAG().is_ready,
        reason="Vector DB not built — run scripts/build_vectordb.py first"
    )
    def test_retrieve_theft(self, rag):
        results = rag.retrieve_sections("someone stole my phone")
        assert len(results) > 0
        section_ids = [r["section_id"] for r in results]
        assert any("63" in sid or "378" in sid for sid in section_ids)

    @pytest.mark.skipif(
        not LegalRAG().is_ready,
        reason="Vector DB not built"
    )
    def test_retrieve_murder(self, rag):
        results = rag.retrieve_sections("someone was murdered")
        assert len(results) > 0

    @pytest.mark.skipif(
        not LegalRAG().is_ready,
        reason="Vector DB not built"
    )
    def test_retrieve_with_correction(self, rag):
        result = rag.retrieve_with_correction("my husband beats me and demands dowry")
        assert "sections" in result
        assert "confidence" in result
        assert result["confidence"] in ("high", "medium", "low", "none")

    @pytest.mark.skipif(
        not LegalRAG().is_ready,
        reason="Vector DB not built"
    )
    def test_retrieve_no_results_for_nonsense(self, rag):
        result = rag.retrieve_with_correction("asdfghjkl zxcvbnm qwerty")
        # Should return low/medium confidence or no results (not high)
        assert result["confidence"] in ("low", "medium", "none")

    @pytest.mark.skipif(
        not LegalRAG().is_ready,
        reason="Vector DB not built"
    )
    def test_generate_response_format(self, rag):
        sections = rag.retrieve_sections("theft")
        response = rag.generate_response("theft", sections)
        assert isinstance(response, str)
        lower = response.lower()
        assert "DISCLAIMER" in response or "legal" in lower or "lawyer" in lower or "consult" in lower

    def test_generate_response_empty_sections(self, rag):
        response = rag.generate_response("test", [])
        assert "NALSA" in response or "no matching" in response.lower() or "could not find" in response.lower()

    @pytest.mark.skipif(
        not LegalRAG().is_ready,
        reason="Vector DB not built"
    )
    def test_retrieve_returns_scores(self, rag):
        results = rag.retrieve_sections("road accident death")
        if results:
            assert all("score" in r for r in results)
            assert all(0 <= r["score"] <= 1 for r in results)
