"""
Tests for Statute Resolver

Tests IPC to BNS conversion and statute information lookup
"""

import pytest
from backend.legal.statute_resolver import StatuteResolver


@pytest.fixture
def resolver():
    """Initialize statute resolver for tests"""
    return StatuteResolver()


def test_resolve_ipc_to_bns(resolver):
    """Test IPC to BNS resolution"""
    result = resolver.resolve_to_bns("IPC-302")
    
    assert result["ipc"] == "IPC-302"
    assert result["bns"] == "BNS-103"
    assert "Both versions refer to same offense" in result["status"]


def test_resolve_bns_to_ipc(resolver):
    """Test BNS to IPC resolution (reverse mapping)"""
    result = resolver.resolve_to_ipc("BNS-103")
    
    assert result["bns"] == "BNS-103"
    assert result["ipc"] == "IPC-302"


def test_get_punishment_ipc(resolver):
    """Test getting punishment for IPC code"""
    punishment = resolver.get_punishment("IPC-302")
    
    assert "Death" in punishment or "life imprisonment" in punishment
    assert punishment != "Unknown"


def test_get_punishment_bns(resolver):
    """Test getting punishment for BNS code"""
    punishment = resolver.get_punishment("BNS-103")
    
    assert "Death" in punishment or "life imprisonment" in punishment


def test_get_statute_details_ipc(resolver):
    """Test getting full details for IPC section"""
    details = resolver.get_statute_details("IPC-302")
    
    assert details["statute_code"] == "IPC-302"
    assert "Deprecated" in details["status"]
    assert "BNS-103" in details.get("current_equivalent", "")
    assert details["cognizable"] == True
    assert details["bailable"] == False


def test_get_statute_details_bns(resolver):
    """Test getting full details for BNS section"""
    details = resolver.get_statute_details("BNS-103")
    
    assert details["statute_code"] == "BNS-103"
    assert "Current" in details["status"]
    assert "2024-07-01" in details["status"]


def test_is_cognizable_murder(resolver):
    """Test that murder is cognizable"""
    assert resolver.is_cognizable("IPC-302") == True
    assert resolver.is_cognizable("BNS-103") == True


def test_is_cognizable_hurt(resolver):
    """Test that simple hurt is not cognizable"""
    assert resolver.is_cognizable("IPC-323") == False
    assert resolver.is_cognizable("BNS-115") == False


def test_is_bailable_murder(resolver):
    """Test that murder is not bailable"""
    assert resolver.is_bailable("IPC-302") == False
    assert resolver.is_bailable("BNS-103") == False


def test_is_bailable_hurt(resolver):
    """Test that simple hurt is bailable"""
    assert resolver.is_bailable("IPC-323") == True
    assert resolver.is_bailable("BNS-115") == True


def test_get_jurisdiction_court(resolver):
    """Test getting jurisdiction court"""
    court = resolver.get_jurisdiction_court("IPC-302")
    
    assert "Court" in court or court != "Unknown Court"


def test_resolve_nonexistent_ipc(resolver):
    """Test resolution of non-existent IPC code"""
    result = resolver.resolve_to_bns("IPC-9999")
    
    assert "error" in result or result["status"] == "Not mapped"


def test_resolve_nonexistent_bns(resolver):
    """Test resolution of non-existent BNS code"""
    result = resolver.resolve_to_ipc("BNS-9999")
    
    assert "error" in result or result["status"] == "Not mapped"


def test_multiple_statute_conversions(resolver):
    """Test converting multiple statutes"""
    test_cases = [
        ("IPC-302", "BNS-103"),  # Murder
        ("IPC-323", "BNS-115"),  # Hurt
        ("IPC-379", "BNS-303"),  # Theft
    ]
    
    for ipc, expected_bns in test_cases:
        result = resolver.resolve_to_bns(ipc)
        assert result["bns"] == expected_bns


def test_consistent_bidirectional_resolution(resolver):
    """Test that bidirectional resolution is consistent"""
    # Forward: IPC → BNS
    forward = resolver.resolve_to_bns("IPC-302")
    bns_code = forward["bns"]
    
    # Reverse: BNS → IPC
    reverse = resolver.resolve_to_ipc(bns_code)
    ipc_code = reverse["ipc"]
    
    # Should get back to original
    assert ipc_code == "IPC-302"


def test_punishment_consistency(resolver):
    """Test that punishment is consistent across IPC and BNS codes"""
    ipc_punishment = resolver.get_punishment("IPC-302")
    bns_punishment = resolver.get_punishment("BNS-103")
    
    # Both should have same essential punishment info
    assert ipc_punishment == bns_punishment


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
