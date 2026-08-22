"""HTTP smoke and validation tests for the integrated PS3 workflows."""

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

    draft = client.post("/api/rti/draft", json=_complete_rti_payload())
    assert draft.status_code == 200
    body = draft.json()
    assert body["status"] == "ready_for_review"
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


def test_unknown_scheme_returns_404() -> None:
    response = client.post(
        "/api/schemes/check-eligibility",
        json={"scheme_id": "not-a-scheme", "profile": {}},
    )
    assert response.status_code == 404


def test_cpgrams_preparation_classifies_and_never_claims_submission() -> None:
    response = client.post(
        "/api/cpgrams/prepare",
        json={
            "grievance": "The municipal road has dangerous potholes and complaints were ignored",
            "state": "Delhi",
            "district": "New Delhi",
            "locality": "Ward 1",
            "organisation_hint": "municipal authority",
            "incident_date": "since January 2026",
            "desired_resolution": "Repair the road and communicate the action taken",
            "cpgrams_account_status": "registered",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["domain"] == "civic_infrastructure"
    assert body["draft"]["formatted_text"]
    assert body["external_action_requires_confirmation"] is True
    assert body["status"] == "ready_for_review"
    assert "submitted" not in body["status"]


def test_cpgrams_exclusion_redirects_rti_matter() -> None:
    response = client.post(
        "/api/cpgrams/prepare",
        json={"grievance": "I want to file an RTI request for government records"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_suitable"
    assert body["suitability"]["exclusion_category"] == "rti_matter"
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
    assert all(item["domain"] == "tenant" for item in body["results"])
    assert all(item["source_url"].startswith("https://") for item in body["results"])
