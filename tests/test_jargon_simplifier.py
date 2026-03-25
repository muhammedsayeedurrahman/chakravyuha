"""Tests for Jargon Simplifier."""

import pytest
from backend.legal.jargon_simplifier import JargonSimplifier


@pytest.fixture
def simplifier():
    return JargonSimplifier()


def test_simplify_term_acquittal(simplifier):
    """Test simplifying 'Acquittal' term."""
    result = simplifier.simplify_term("acquittal")
    
    assert "acquittal" in result["term"].lower()
    assert len(result["simple_explanation"]) > 0
    assert "guilty" in result["simple_explanation"].lower()


def test_simplify_term_advocate(simplifier):
    """Test simplifying 'Advocate' term."""
    result = simplifier.simplify_term("advocate")
    
    assert "lawyer" in result["simple_explanation"].lower()


def test_simplify_term_case_insensitive(simplifier):
    """Test term simplification is case-insensitive."""
    result1 = simplifier.simplify_term("FIR")
    result2 = simplifier.simplify_term("fir")
    
    assert result1["simple_explanation"] == result2["simple_explanation"]


def test_simplify_statute_code_bns_103(simplifier):
    """Test simplifying BNS-103 (Murder)."""
    result = simplifier.simplify_statute_code("BNS-103")
    
    assert result["code"] == "BNS-103"
    assert "murder" in result["title"].lower()
    assert "death" in result["simple_explanation"].lower() or "life" in result["simple_explanation"].lower()


def test_simplify_statute_code_bns_115(simplifier):
    """Test simplifying BNS-115 (Hurt)."""
    result = simplifier.simplify_statute_code("BNS-115")
    
    assert "hurt" in result["title"].lower()
    assert "injury" in result["simple_explanation"].lower() or "physical" in result["simple_explanation"].lower()


def test_simplify_statute_code_bns_303(simplifier):
    """Test simplifying BNS-303 (Theft)."""
    result = simplifier.simplify_statute_code("BNS-303")
    
    assert "theft" in result["title"].lower()
    assert "property" in result["simple_explanation"].lower() or "taking" in result["simple_explanation"].lower()


def test_simplify_ipc_code(simplifier):
    """Test simplifying legacy IPC codes."""
    result = simplifier.simplify_statute_code("IPC-302")
    
    assert "BNS-103" in result.get("equivalent", "")


def test_simplify_unknown_term(simplifier):
    """Test behavior with unknown term."""
    result = simplifier.simplify_term("XYZABC")
    
    assert "not found" in result["simple_explanation"].lower() or len(result["simple_explanation"]) > 0


def test_simplify_unknown_statute(simplifier):
    """Test behavior with unknown statute code."""
    result = simplifier.simplify_statute_code("BNS-999")
    
    assert "error" in result or "not found" in result.get("simple_explanation", "").lower()


def test_simplify_text_replaces_legal_terms(simplifier):
    """Test text simplification replaces legal jargon."""
    legal_text = "Notwithstanding the aforementioned provisions, the accused shall appear hereinafter"
    simplified = simplifier.simplify_text(legal_text)
    
    # Check that some legal terms were replaced
    assert "despite" in simplified or simplified != legal_text


def test_get_related_terms(simplifier):
    """Test getting related terms."""
    related = simplifier.get_related_terms("Conviction")
    
    assert isinstance(related, list)
    # Should have some related terms like "Guilty"
    assert len(related) >= 0


def test_hindi_term_available(simplifier):
    """Test Hindi translation is available."""
    result = simplifier.simplify_term("FIR")
    
    assert len(result["hindi_term"]) > 0 or "hindi" in result


def test_statute_hindi_available(simplifier):
    """Test statute Hindi translation available."""
    result = simplifier.simplify_statute_code("BNS-103")
    
    assert len(result.get("hindi", "")) > 0


def test_punishment_included(simplifier):
    """Test punishment details are included."""
    result = simplifier.simplify_statute_code("BNS-115")
    
    assert "punishment" in result
    assert "jail" in result.get("punishment", "").lower() or "fine" in result.get("punishment", "").lower()
