"""Tests for Document Drafting Agent."""

import pytest
from backend.legal.document_drafter import (
    DocumentDrafter,
    DocumentType,
    PartyInfo,
    CaseContext,
)


@pytest.fixture
def drafter():
    return DocumentDrafter()


@pytest.fixture
def sample_case():
    """Sample case context for testing."""
    return CaseContext(
        complainant=PartyInfo(
            name="Raj Kumar",
            phone="9876543210",
            email="raj@example.com",
            address="123 Main Street, Delhi-110001",
            occupation="Engineer",
        ),
        accused=PartyInfo(
            name="John Doe",
            phone="9123456789",
            address="456 Court Road, Delhi-110002",
        ),
        case_type="Theft",
        incident_date="2024-03-20",
        incident_location="Delhi Market, Chandni Chowk",
        description="I was at Delhi Market when my mobile phone was snatched by the accused. The incident occurred at 3 PM near the fountain.",
        offense_sections=["BNS-303", "BNS-351"],
        evidence=["CCTV footage", "Police diary", "Mobile phone IMEI"],
        witnesses=["Witness 1: Priya", "Witness 2: Arjun"],
    )


def test_draft_fir(drafter, sample_case):
    """Test FIR generation."""
    fir = drafter.draft_fir(sample_case)
    
    # Verify FIR contains key elements
    assert "FIRST INFORMATION REPORT" in fir
    assert "Raj Kumar" in fir
    assert "John Doe" in fir
    assert "BNS-303" in fir
    assert "Theft" in fir
    assert "2024-03-20" in fir
    assert "CCTV footage" in fir
    

def test_draft_legal_notice(drafter, sample_case):
    """Test legal notice generation."""
    notice = drafter.draft_legal_notice(sample_case)
    
    # Verify notice contains key elements
    assert "LEGAL NOTICE" in notice
    assert "Raj Kumar" in notice
    assert "John Doe" in notice
    assert "BNS-303" in notice
    assert "30 (Thirty) days" in notice


def test_draft_complaint(drafter, sample_case):
    """Test complaint generation."""
    complaint = drafter.draft_complaint(sample_case)
    
    # Verify complaint contains key elements
    assert "COMPLAINT PETITION" in complaint
    assert "Raj Kumar" in complaint
    assert "John Doe" in complaint
    assert "BNS-303" in complaint


def test_fir_contains_personal_details(drafter, sample_case):
    """Verify FIR includes all personal details."""
    fir = drafter.draft_fir(sample_case)
    
    assert sample_case.complainant.name in fir
    assert sample_case.complainant.phone in fir
    assert sample_case.complainant.address in fir
    assert sample_case.accused.name in fir
    assert sample_case.accused.address in fir


def test_fir_includes_incident_details(drafter, sample_case):
    """Verify FIR includes incident details."""
    fir = drafter.draft_fir(sample_case)
    
    assert sample_case.incident_date in fir
    assert sample_case.incident_location in fir
    assert sample_case.case_type in fir
    assert sample_case.description in fir


def test_fir_lists_offense_sections(drafter, sample_case):
    """Verify FIR lists all offense sections."""
    fir = drafter.draft_fir(sample_case)
    
    for section in sample_case.offense_sections:
        assert section in fir


def test_fir_includes_evidence(drafter, sample_case):
    """Verify FIR includes evidence list."""
    fir = drafter.draft_fir(sample_case)
    
    for evidence in sample_case.evidence:
        assert evidence in fir


def test_fir_includes_witnesses(drafter, sample_case):
    """Verify FIR includes witness list."""
    fir = drafter.draft_fir(sample_case)
    
    for witness in sample_case.witnesses:
        assert witness in fir


def test_fir_with_no_evidence(drafter, sample_case):
    """Test FIR generation with no evidence."""
    sample_case.evidence = []
    fir = drafter.draft_fir(sample_case)
    
    assert "To be collected" in fir


def test_fir_with_no_witnesses(drafter, sample_case):
    """Test FIR generation with no witnesses."""
    sample_case.witnesses = []
    fir = drafter.draft_fir(sample_case)
    
    assert "To be identified" in fir


def test_get_document_fir(drafter, sample_case):
    """Test get_document method with FIR type."""
    doc = drafter.get_document(DocumentType.FIR, sample_case)
    assert "FIRST INFORMATION REPORT" in doc


def test_get_document_notice(drafter, sample_case):
    """Test get_document method with LEGAL_NOTICE type."""
    doc = drafter.get_document(DocumentType.LEGAL_NOTICE, sample_case)
    assert "LEGAL NOTICE" in doc


def test_get_document_complaint(drafter, sample_case):
    """Test get_document method with COMPLAINT type."""
    doc = drafter.get_document(DocumentType.COMPLAINT, sample_case)
    assert "COMPLAINT PETITION" in doc


def test_invalid_document_type(drafter, sample_case):
    """Test error handling for invalid document type."""
    with pytest.raises(ValueError):
        drafter.get_document("INVALID_TYPE", sample_case)


def test_document_has_date_generated(drafter, sample_case):
    """Verify documents include generation date."""
    fir = drafter.draft_fir(sample_case)
    
    # Should contain current date (at least the format)
    assert "/" in fir  # Date format typically has slashes
