"""HTTP smoke and validation tests for the integrated PS3 workflows."""

import pytest

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def _complete_rti_payload() -> dict:
    return {
        "issue": "The municipal road near my home has not been repaired for two years",
        "state": "Delhi",
        "city": "Delhi",
        "locality": "Ward 1",
        "road_type": "municipal road",
        "date_range": "1 January 2024 to 31 December 2025",
        "applicant_name": "A Citizen",
        "applicant_address": "Ward 1, Delhi",
        "is_indian_citizen": True,
    }


def test_rti_rejects_too_short_issue() -> None:
    response = client.post("/api/rti/draft", json={"issue": "road"})
    assert response.status_code == 422


def test_rti_route_then_draft_and_download() -> None:
    route = client.post(
        "/api/rti/identify-department",
        json={"issue": "The road has not been repaired for two years"},
    )
    assert route.status_code == 200
    assert route.json()["confidence"] == "requires_jurisdiction"
    assert route.json()["jurisdiction_completeness"] == {
        "state_known": False,
        "district_known": False,
        "city_known": False,
        "locality_known": False,
        "authority_known": False,
    }

    draft = client.post("/api/rti/draft", json=_complete_rti_payload())
    assert draft.status_code == 200
    body = draft.json()
    assert body["status"] == "ready_for_review"
    assert body["routing"]["jurisdiction_completeness"]["state_known"] is True
    assert body["routing"]["jurisdiction_completeness"]["city_known"] is True
    assert "work order" in " ".join(body["information_requests"]).lower()
    assert "RIGHT TO INFORMATION APPLICATION" in body["document_text"]

    download = client.post("/api/rti/download", json=_complete_rti_payload())
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("text/plain")
    assert "rti-a-citizen.txt" in download.headers["content-disposition"]


def test_rti_download_is_gated_when_information_is_missing() -> None:
    response = client.post(
        "/api/rti/download",
        json={"issue": "The road has not been repaired for two years"},
    )
    assert response.status_code == 409
    assert "missing_information" in response.json()["detail"]


def test_scheme_eligibility_match_has_explanations_and_provenance() -> None:
    response = client.post(
        "/api/schemes/check-eligibility",
        json={
            "scheme_id": "pm-sym",
            "profile": {
                "is_unorganised_worker": True,
                "age": 30,
                "monthly_income": 12000,
                "is_income_tax_payer": False,
                "covered_by_epfo": False,
                "covered_by_esic": False,
                "covered_by_nps": False,
            },
        },
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "Likely eligible"
    assert result["matched_conditions"]
    assert result["potential_disqualifiers"] == []
    assert all(
        {
            "observed_value",
            "expected_value",
            "operator",
            "effect",
            "explanation",
        }.issubset(condition)
        for condition in result["matched_conditions"]
    )
    assert result["provenance"]["source_url"].startswith("https://")
    assert "percentage" not in str(result).lower()


def test_scheme_guided_check_asks_only_a_few_candidate_questions() -> None:
    response = client.post(
        "/api/schemes/guided-check",
        json={"profile": {}, "max_questions": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["complete"] is False
    assert 1 <= len(body["next_questions"]) <= 3
    assert len({question["field"] for question in body["next_questions"]}) == len(
        body["next_questions"]
    )
    assert all(question["input_type"] == "boolean" for question in body["next_questions"])


def test_unknown_scheme_returns_404() -> None:
    response = client.post(
        "/api/schemes/check-eligibility",
        json={"scheme_id": "not-a-scheme", "profile": {}},
    )
    assert response.status_code == 404


def test_pm_kisan_string_yes_is_unknown_instead_of_fabricated_negative() -> None:
    response = client.post(
        "/api/schemes/check-eligibility",
        json={
            "scheme_id": "pm-kisan",
            "profile": {
                "is_landholding_farmer_family": True,
                "land_acquired_after_2019_02_01_other_than_inheritance": False,
                "is_institutional_landholder": False,
                "family_member_holds_or_held_constitutional_post": False,
                "family_member_in_excluded_elected_office": False,
                "family_member_is_non_exempt_government_employee": False,
                "family_member_is_non_exempt_pensioner_10000_or_more": False,
                "family_member_paid_income_tax_last_assessment_year": "Yes",
                "family_member_is_practising_registered_professional": False,
                "family_is_nri_for_new_beneficiary_rule": False,
            },
            "max_questions": 10,
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    tax_unknown = next(
        item
        for item in result["unknown_conditions"]
        if item["rule_id"] == "pm_kisan_income_tax"
    )
    assert result["status"] == "Possibly eligible"
    assert tax_unknown["reason"] == "invalid_value"
    assert tax_unknown["observed_value"] == "Yes"
    assert not any(
        item["rule_id"] == "pm_kisan_income_tax"
        for item in result["matched_conditions"]
    )


@pytest.mark.parametrize(
    ("scheme_id", "field", "rule_id"),
    [
        ("pm-sym", "is_unorganised_worker", "pm_sym_unorganised_worker"),
        ("pm-kisan", "is_landholding_farmer_family", "pm_kisan_landholding_family"),
    ],
)
def test_known_boolean_string_is_preserved_for_strict_engine_validation(
    scheme_id: str,
    field: str,
    rule_id: str,
) -> None:
    response = client.post(
        "/api/schemes/check-eligibility",
        json={
            "scheme_id": scheme_id,
            "profile": {field: "Yes"},
            "max_questions": 10,
        },
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    invalid = next(
        item for item in result["unknown_conditions"] if item["rule_id"] == rule_id
    )
    assert result["status"] == "Not enough information"
    assert invalid["reason"] == "invalid_value"
    assert invalid["observed_value"] == "Yes"
    assert rule_id not in {
        item["rule_id"] for item in result["matched_conditions"]
    }


def test_cpgrams_preparation_classifies_and_never_claims_submission() -> None:
    response = client.post(
        "/api/cpgrams/prepare",
        json={
            "grievance": "The municipal road has dangerous potholes and complaints were ignored",
            "state": "Delhi",
            "district": "New Delhi",
            "city": "New Delhi",
            "locality": "Ward 1",
            "organisation_hint": "municipal authority",
            "incident_date": "since January 2026",
            "desired_resolution": "Repair the road and communicate the action taken",
            "cpgrams_account_status": "registered",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "government_service_grievance"
    assert body["workflow"] == "cpgrams"
    assert body["handoff"] is None
    assert body["classification"]["domain"] == "civic_infrastructure"
    assert body["draft"]["formatted_text"]
    assert body["external_action_requires_confirmation"] is True
    assert body["status"] == "ready_for_review"
    assert body["handoff_state"] == "PREPARED"
    assert body["handoff_blockers"] == []
    assert body["jurisdiction_completeness"] == {
        "state_known": True,
        "district_known": True,
        "city_known": True,
        "locality_known": True,
        "authority_known": True,
    }
    assert "submitted" not in body["status"]


def test_cpgrams_exclusion_redirects_rti_matter() -> None:
    response = client.post(
        "/api/cpgrams/prepare",
        json={
            "grievance": (
                "I want copies of records showing how much money was sanctioned and spent "
                "on repairing this road"
            )
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_suitable"
    assert body["intent"] == "information_request"
    assert body["workflow"] == "rti"
    assert body["handoff"] == {"journey": "rti", "handler": "rti_assistant"}
    assert body["handoff_state"] == "DRAFT"
    assert body["handoff_blockers"] == [
        "CPGRAMS review is unavailable: The official CPGRAMS portal states that RTI "
        "matters are not taken up for redress. Continue in the RTI workflow instead."
    ]
    assert body["classification"]["domain"] == "information_request"
    assert body["suitability"]["exclusion_category"] == "rti_matter"
    assert body["draft"] is None
    assert body["jurisdiction_completeness"]["state_known"] is False


def test_cpgrams_rights_request_hands_off_without_creating_grievance() -> None:
    response = client.post(
        "/api/cpgrams/prepare",
        json={
            "grievance": (
                "My landlord refuses to return my security deposit after I moved out."
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_suitable"
    assert body["intent"] == "rights_guidance"
    assert body["workflow"] == "rights_guidance"
    assert body["handoff"] == {"journey": "rights", "handler": "rights_navigator"}
    assert body["handoff_state"] == "DRAFT"
    assert body["handoff_blockers"]
    assert body["draft"] is None


def test_tenant_api_requires_jurisdiction_and_retains_sources() -> None:
    response = client.post(
        "/api/legal/domains/query",
        json={
            "query": "My landlord threatens eviction and will not return my deposit",
            "domain": "tenant",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "requires_jurisdiction"
    assert body["missing_information"]
    assert body["jurisdiction_completeness"]["state_known"] is False
    assert any("State or Union Territory" in step for step in body["next_steps"])
    assert all(item["domain"] == "tenant" for item in body["results"])
    assert all(item["source_url"].startswith("https://") for item in body["results"])


def test_tenant_api_retains_explicit_state_and_only_flags_city_as_unknown() -> None:
    response = client.post(
        "/api/legal/domains/query",
        json={
            "query": "My landlord will not return my security deposit",
            "domain": "tenant",
            "state": "Tamil Nadu",
        },
    )

    assert response.status_code == 200
    body = response.json()
    expected = "Tamil Nadu identified; city/local jurisdiction may still be required"
    assert body["jurisdiction"] == "Tamil Nadu"
    assert body["jurisdiction_completeness"]["state_known"] is True
    assert body["jurisdiction_completeness"]["city_known"] is False
    assert body["missing_information"] == []
    assert expected in body["answer"]
    assert expected in body["next_steps"][0]
    assert "Provide the State or Union Territory" not in body["answer"]
