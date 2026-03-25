"""Tests for section lookup correctness."""

import pytest
from backend.legal.sections import SectionLookup


@pytest.fixture
def lookup():
    return SectionLookup()


class TestSectionLookup:
    def test_lookup_bns_section(self, lookup):
        result = lookup.lookup_section("BNS-100")
        assert result is not None
        assert result["section_id"] == "BNS-100"
        assert "murder" in result["title"].lower()

    def test_lookup_ipc_section(self, lookup):
        result = lookup.lookup_section("IPC-302")
        assert result is not None
        assert result["section_id"] == "IPC-302"

    def test_lookup_nonexistent_section(self, lookup):
        result = lookup.lookup_section("BNS-99999")
        assert result is None

    def test_ipc_to_bns_mapping(self, lookup):
        bns = lookup.ipc_to_bns("IPC-302")
        assert bns == "BNS-100"

    def test_bns_to_ipc_mapping(self, lookup):
        ipc = lookup.bns_to_ipc("BNS-100")
        assert ipc == "IPC-302"

    def test_ipc_to_bns_nonexistent(self, lookup):
        result = lookup.ipc_to_bns("IPC-99999")
        assert result is None

    def test_search_theft(self, lookup):
        results = lookup.search_sections("theft")
        assert len(results) > 0
        section_ids = [r["section_id"] for r in results]
        assert "BNS-305" in section_ids or any("theft" in r["title"].lower() for r in results)

    def test_search_murder(self, lookup):
        results = lookup.search_sections("murder")
        assert len(results) > 0
        top = results[0]
        assert "murder" in top["title"].lower() or "murder" in top.get("description", "").lower()

    def test_search_bns_only(self, lookup):
        results = lookup.search_sections("theft", law="bns")
        for r in results:
            assert r["section_id"].startswith("BNS")

    def test_search_ipc_only(self, lookup):
        results = lookup.search_sections("theft", law="ipc")
        for r in results:
            assert r["section_id"].startswith("IPC")

    def test_get_both_laws_from_bns(self, lookup):
        result = lookup.get_both_laws("BNS-100")
        assert result["bns"] is not None
        assert result["ipc"] is not None
        assert result["bns"]["section_id"] == "BNS-100"
        assert result["ipc"]["section_id"] == "IPC-302"

    def test_get_both_laws_from_ipc(self, lookup):
        result = lookup.get_both_laws("IPC-420")
        assert result["ipc"] is not None
        assert result["bns"] is not None

    def test_search_domestic_violence(self, lookup):
        results = lookup.search_sections("domestic violence")
        assert len(results) > 0

    def test_search_dowry(self, lookup):
        results = lookup.search_sections("dowry")
        section_ids = [r["section_id"] for r in results]
        assert "BNS-103" in section_ids or "BNS-85" in section_ids

    def test_all_bns_sections_have_required_fields(self, lookup):
        for section in lookup._bns:
            assert "section_id" in section
            assert "title" in section
            assert "description" in section
            assert "punishment" in section

    def test_search_results_sorted_by_score(self, lookup):
        results = lookup.search_sections("fraud")
        if len(results) > 1:
            scores = [r["match_score"] for r in results]
            assert scores == sorted(scores, reverse=True)
