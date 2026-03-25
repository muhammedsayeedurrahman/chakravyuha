"""Tests for the Agentic Complaint Drafter pipeline."""

import pytest
from backend.agent.complaint_drafter_agent import (
    ComplaintDrafterAgent,
    DraftResult,
    ExtractedInfo,
)


@pytest.fixture
def agent():
    return ComplaintDrafterAgent()


# ── Narrative analysis tests ────────────────────────────────────────────────


class TestNarrativeAnalysis:
    """Tests for entity extraction from narratives."""

    def test_extracts_theft_offense(self, agent):
        info = agent._analyze_narrative("Someone stole my phone yesterday", "en")
        assert info is not None
        assert info.offense == "theft"
        assert info.offense_confidence >= 0.8

    def test_extracts_hurt_offense(self, agent):
        info = agent._analyze_narrative("My neighbor hit me badly", "en")
        assert info is not None
        assert info.offense == "hurt"

    def test_extracts_cheating_offense(self, agent):
        info = agent._analyze_narrative("He cheated me of my money", "en")
        assert info is not None
        assert info.offense == "cheating"

    def test_extracts_bns_sections(self, agent):
        info = agent._analyze_narrative("There was a theft at my house", "en")
        assert info is not None
        assert len(info.bns_sections) > 0
        assert any("BNS" in s for s in info.bns_sections)

    def test_returns_none_for_unrelated_text(self, agent):
        info = agent._analyze_narrative("The weather is nice today", "en")
        assert info is None

    def test_extracts_murder_as_cognizable(self, agent):
        info = agent._analyze_narrative("Someone committed murder in the village", "en")
        assert info is not None
        assert info.offense == "murder"
        assert info.offense_confidence >= 0.9


# ── Document type classification tests ──────────────────────────────────────


class TestDocumentClassification:
    """Tests for auto-classifying document type."""

    def test_theft_classified_as_fir(self, agent):
        info = agent._analyze_narrative("My bike was stolen", "en")
        doc_type = agent._classify_document_type(info, "My bike was stolen", "")
        assert doc_type == "FIR"

    def test_cheating_classified_as_complaint(self, agent):
        info = agent._analyze_narrative("He cheated me in a deal", "en")
        doc_type = agent._classify_document_type(info, "He cheated me in a deal", "")
        assert doc_type == "COMPLAINT"

    def test_notice_keywords_trigger_legal_notice(self, agent):
        info = agent._analyze_narrative("I want to warn and demand compensation for theft", "en")
        doc_type = agent._classify_document_type(
            info, "I want to warn and demand compensation for theft", ""
        )
        assert doc_type == "LEGAL_NOTICE"

    def test_preferred_type_overrides_auto(self, agent):
        info = agent._analyze_narrative("Someone stole my phone", "en")
        doc_type = agent._classify_document_type(info, "Someone stole my phone", "COMPLAINT")
        assert doc_type == "COMPLAINT"

    def test_preferred_type_case_insensitive(self, agent):
        info = agent._analyze_narrative("Someone stole my phone", "en")
        doc_type = agent._classify_document_type(info, "Someone stole my phone", "legal_notice")
        assert doc_type == "LEGAL_NOTICE"


# ── Date/location/name extraction tests ─────────────────────────────────────


class TestContextExtraction:
    """Tests for extracting dates, locations, and names."""

    def test_extract_relative_date(self, agent):
        date = agent._extract_date("It happened yesterday near the market")
        assert date == "yesterday"

    def test_extract_date_pattern(self, agent):
        date = agent._extract_date("The incident occurred on 20/03/2026 at the shop")
        assert "20" in date and "03" in date and "2026" in date

    def test_extract_location_with_at(self, agent):
        loc = agent._extract_location("I was robbed at Delhi Market")
        assert "Delhi" in loc

    def test_extract_accused_name(self, agent):
        name = agent._extract_accused_name("My neighbor Ravi stole my laptop")
        assert name == "Ravi"


# ── Missing fields detection tests ──────────────────────────────────────────


class TestMissingFields:
    """Tests for identifying missing critical information."""

    def test_all_fields_present(self, agent):
        missing = agent._identify_missing_fields(
            complainant_name="Raj",
            complainant_phone="9876543210",
            accused_name="John",
            incident_date="2026-03-20",
            incident_location="Delhi",
        )
        assert missing == []

    def test_missing_complainant(self, agent):
        missing = agent._identify_missing_fields(
            complainant_name="",
            complainant_phone="",
            accused_name="John",
            incident_date="2026-03-20",
            incident_location="Delhi",
        )
        assert "complainant_name" in missing
        assert "complainant_phone" in missing

    def test_unknown_accused_flagged(self, agent):
        missing = agent._identify_missing_fields(
            complainant_name="Raj",
            complainant_phone="9876543210",
            accused_name="Unknown",
            incident_date="2026-03-20",
            incident_location="Delhi",
        )
        assert "accused_name" in missing


# ── Full pipeline (auto_draft) tests ────────────────────────────────────────


class TestAutoDraftPipeline:
    """Integration tests for the full agentic pipeline."""

    def test_auto_draft_theft_returns_fir(self, agent):
        result = agent.auto_draft(
            narrative="My neighbor stole my mobile phone from my house yesterday",
            complainant_name="Raj Kumar",
            complainant_phone="9876543210",
        )
        assert isinstance(result, DraftResult)
        assert result.status in ("success", "needs_info")
        assert result.document_type == "FIR"
        assert len(result.content) > 0
        assert len(result.applicable_sections) > 0

    def test_auto_draft_cheating_returns_complaint(self, agent):
        result = agent.auto_draft(
            narrative="My business partner cheated me of 5 lakh rupees",
            complainant_name="Priya Sharma",
            complainant_phone="9123456789",
        )
        assert result.document_type == "COMPLAINT"
        assert result.extracted_info.offense == "cheating"

    def test_auto_draft_with_no_entities_returns_error(self, agent):
        result = agent.auto_draft(
            narrative="The sky is blue and birds are singing",
        )
        assert result.status == "error"
        assert result.error is not None

    def test_auto_draft_includes_strategy(self, agent):
        result = agent.auto_draft(
            narrative="Someone committed theft at my shop",
            complainant_name="Test User",
            complainant_phone="9999999999",
        )
        assert result.strategy_summary is not None
        assert "recommended_forum" in result.strategy_summary
        assert "evidence_checklist" in result.strategy_summary
        assert "steps" in result.strategy_summary

    def test_auto_draft_reports_missing_fields(self, agent):
        result = agent.auto_draft(
            narrative="There was a theft at the market",
            # No complainant info provided
        )
        assert result.status == "needs_info"
        assert "complainant_name" in result.missing_fields

    def test_auto_draft_with_preferred_type(self, agent):
        result = agent.auto_draft(
            narrative="My neighbor stole my bike",
            complainant_name="Test",
            complainant_phone="1234567890",
            preferred_doc_type="LEGAL_NOTICE",
        )
        assert result.document_type == "LEGAL_NOTICE"

    def test_auto_draft_content_contains_sections(self, agent):
        result = agent.auto_draft(
            narrative="I was the victim of theft yesterday at my home",
            complainant_name="Test",
            complainant_phone="1234567890",
        )
        # The document content should reference BNS sections or document headers
        content_upper = result.content.upper()
        assert (
            "BNS" in result.content
            or "FIRST INFORMATION REPORT" in content_upper
            or "COMPLAINT" in content_upper
        )

    def test_auto_draft_extracted_info_immutable(self, agent):
        result = agent.auto_draft(
            narrative="There was a theft at my house yesterday",
            complainant_name="Test",
            complainant_phone="1234567890",
        )
        assert isinstance(result.extracted_info, ExtractedInfo)
        # frozen=True dataclass should raise on mutation
        with pytest.raises(AttributeError):
            result.extracted_info.offense = "different"

    def test_auto_draft_result_immutable(self, agent):
        result = agent.auto_draft(
            narrative="Someone stole my wallet",
            complainant_name="Test",
            complainant_phone="1234567890",
        )
        with pytest.raises(AttributeError):
            result.status = "modified"


# ── Intent classifier integration ───────────────────────────────────────────


class TestIntentClassifierIntegration:
    """Verify intent classifier detects complaint drafting intents."""

    def test_draft_complaint_intent(self):
        from backend.agent.intent_classifier import classify_intent, INTENT_COMPLAINT_DRAFT

        result = classify_intent("I want to draft a complaint")
        assert result.intent == INTENT_COMPLAINT_DRAFT

    def test_file_fir_intent(self):
        from backend.agent.intent_classifier import classify_intent, INTENT_COMPLAINT_DRAFT

        result = classify_intent("Help me file an FIR")
        assert result.intent == INTENT_COMPLAINT_DRAFT

    def test_generate_legal_notice_intent(self):
        from backend.agent.intent_classifier import classify_intent, INTENT_COMPLAINT_DRAFT

        result = classify_intent("Generate a legal notice for my case")
        assert result.intent == INTENT_COMPLAINT_DRAFT

    def test_prepare_petition_intent(self):
        from backend.agent.intent_classifier import classify_intent, INTENT_COMPLAINT_DRAFT

        result = classify_intent("I want to prepare a petition")
        assert result.intent == INTENT_COMPLAINT_DRAFT
