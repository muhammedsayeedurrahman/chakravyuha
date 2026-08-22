"""Tests for deterministic and explainable government-scheme eligibility."""

from __future__ import annotations

import json

import pytest

from backend.legal.scheme_eligibility import (
    LIKELY_ELIGIBLE,
    LIKELY_NOT_ELIGIBLE,
    NOT_ENOUGH_INFORMATION,
    POSSIBLY_ELIGIBLE,
    SchemeEligibilityEngine,
    SchemeNotFoundError,
)


@pytest.fixture
def engine() -> SchemeEligibilityEngine:
    return SchemeEligibilityEngine()


def _pm_sym_profile(*, age: int = 30, monthly_income: int = 12000) -> dict:
    return {
        "is_unorganised_worker": True,
        "age": age,
        "monthly_income": monthly_income,
        "is_income_tax_payer": False,
        "covered_by_epfo": False,
        "covered_by_esic": False,
        "covered_by_nps": False,
    }


def _apy_profile(*, age: int = 30, income_tax_payer: bool = False) -> dict:
    return {
        "is_indian_citizen": True,
        "age": age,
        "has_savings_account": True,
        "is_or_has_been_income_tax_payer": income_tax_payer,
        "already_has_apy_account": False,
    }


def _pm_kisan_profile() -> dict:
    return {
        "is_landholding_farmer_family": True,
        "land_acquired_after_2019_02_01_other_than_inheritance": False,
        "is_institutional_landholder": False,
        "family_member_holds_or_held_constitutional_post": False,
        "family_member_in_excluded_elected_office": False,
        "family_member_is_non_exempt_government_employee": False,
        "family_member_is_non_exempt_pensioner_10000_or_more": False,
        "family_member_paid_income_tax_last_assessment_year": False,
        "family_member_is_practising_registered_professional": False,
        "family_is_nri_for_new_beneficiary_rule": False,
    }


def test_dataset_contains_only_three_sourced_schemes(engine: SchemeEligibilityEngine):
    schemes = engine.list_schemes()

    assert {scheme["id"] for scheme in schemes} == {"pm-sym", "apy", "pm-kisan"}
    assert engine.metadata["scheme_count"] == 3
    for scheme in schemes:
        assert scheme["source_url"].startswith("https://")
        assert scheme["source_type"].startswith("official_")
        assert scheme["last_verified"] == "2026-08-20"
        assert scheme["status"].startswith("verified")
        assert scheme["required_documents"]
        assert scheme["application_process"]


@pytest.mark.parametrize("age", [18, 40])
def test_pm_sym_age_boundaries_are_inclusive(
    engine: SchemeEligibilityEngine, age: int
):
    result = engine.check_eligibility("pm-sym", _pm_sym_profile(age=age))

    assert result["status"] == LIKELY_ELIGIBLE
    assert not result["potential_disqualifiers"]
    assert len(result["matched_conditions"]) == 7


def test_pm_sym_income_boundary_is_inclusive(engine: SchemeEligibilityEngine):
    at_limit = engine.check_eligibility(
        "pm-sym", _pm_sym_profile(monthly_income=15000)
    )
    over_limit = engine.check_eligibility(
        "pm-sym", _pm_sym_profile(monthly_income=15001)
    )

    assert at_limit["status"] == LIKELY_ELIGIBLE
    assert over_limit["status"] == LIKELY_NOT_ELIGIBLE
    assert any(
        item["rule_id"] == "pm_sym_monthly_income"
        for item in over_limit["potential_disqualifiers"]
    )


@pytest.mark.parametrize("age", [17, 41])
def test_pm_sym_outside_age_boundary_is_explained(
    engine: SchemeEligibilityEngine, age: int
):
    result = engine.check_eligibility("pm-sym", _pm_sym_profile(age=age))

    assert result["status"] == LIKELY_NOT_ELIGIBLE
    age_failure = next(
        item
        for item in result["potential_disqualifiers"]
        if item["rule_id"] == "pm_sym_age"
    )
    assert "18-to-40" in age_failure["explanation"]


def test_missing_profile_returns_only_targeted_questions(
    engine: SchemeEligibilityEngine,
):
    result = engine.check_eligibility("pm-sym", {}, max_questions=3)

    assert result["status"] == NOT_ENOUGH_INFORMATION
    assert len(result["unknown_conditions"]) == 7
    assert [question["field"] for question in result["next_questions"]] == [
        "is_unorganised_worker",
        "age",
        "monthly_income",
    ]
    assert not result["matched_conditions"]
    assert not result["potential_disqualifiers"]


def test_partial_profile_is_possibly_eligible_and_does_not_repeat_answered_field(
    engine: SchemeEligibilityEngine,
):
    result = engine.check_eligibility(
        "pm-sym", {"is_unorganised_worker": True}, max_questions=2
    )

    assert result["status"] == POSSIBLY_ELIGIBLE
    assert result["matched_conditions"][0]["rule_id"] == "pm_sym_unorganised_worker"
    assert [question["field"] for question in result["next_questions"]] == [
        "age",
        "monthly_income",
    ]


def test_apy_40th_birthday_boundary_and_taxpayer_exclusion(
    engine: SchemeEligibilityEngine,
):
    boundary = engine.check_eligibility("apy", _apy_profile(age=40))
    taxpayer = engine.check_eligibility(
        "apy", _apy_profile(age=40, income_tax_payer=True)
    )

    assert boundary["status"] == LIKELY_ELIGIBLE
    assert taxpayer["status"] == LIKELY_NOT_ELIGIBLE
    tax_failure = next(
        item
        for item in taxpayer["potential_disqualifiers"]
        if item["rule_id"] == "apy_income_tax"
    )
    assert "1 October 2022" in tax_failure["explanation"]


def test_pm_kisan_family_exclusion_is_explained(engine: SchemeEligibilityEngine):
    eligible_profile = _pm_kisan_profile()
    excluded_profile = {**eligible_profile, "family_member_paid_income_tax_last_assessment_year": True}

    eligible = engine.check_eligibility("pm-kisan", eligible_profile)
    excluded = engine.check_eligibility("pm-kisan", excluded_profile)

    assert eligible["status"] == LIKELY_ELIGIBLE
    assert excluded["status"] == LIKELY_NOT_ELIGIBLE
    assert any(
        "last assessment year" in item["explanation"]
        for item in excluded["potential_disqualifiers"]
    )
    assert excluded["verification_note"]


def test_result_is_explainable_and_has_no_numeric_eligibility_score(
    engine: SchemeEligibilityEngine,
):
    result = engine.check_eligibility("apy", _apy_profile())
    serialized = json.dumps(result).lower()

    assert result["why"]
    assert result["matched_conditions"]
    assert all(item["explanation"] for item in result["matched_conditions"])
    assert result["source_url"].startswith("https://")
    assert result["last_verified"] == "2026-08-20"
    assert "percentage" not in serialized
    assert "eligibility_score" not in serialized


def test_unknown_scheme_raises_clear_error(engine: SchemeEligibilityEngine):
    with pytest.raises(SchemeNotFoundError, match="Unknown scheme"):
        engine.check_eligibility("not-a-real-scheme", {})

    with pytest.raises(SchemeNotFoundError, match="Unknown scheme"):
        engine.get_scheme("not-a-real-scheme")


def test_list_detail_and_search_methods(engine: SchemeEligibilityEngine):
    assert engine.get_scheme("PM-SYM")["id"] == "pm-sym"
    assert engine.get_scheme("PFRDA APY")["id"] == "apy"
    assert [scheme["id"] for scheme in engine.search_schemes("farmer")] == [
        "pm-kisan"
    ]
    assert len(engine.search_schemes("")) == 3


def test_invalid_numeric_value_is_unknown_and_visible_warning(
    engine: SchemeEligibilityEngine,
):
    profile = _pm_sym_profile()
    profile["age"] = "forty"

    result = engine.check_eligibility("pm-sym", profile)

    assert result["status"] == POSSIBLY_ELIGIBLE
    assert any(
        item["rule_id"] == "pm_sym_age" and item["reason"] == "invalid_value"
        for item in result["unknown_conditions"]
    )
    assert result["evaluation_warnings"]


def test_synthetic_state_specific_rule_uses_injected_dataset():
    dataset = {
        "metadata": {"last_verified": "2026-08-20"},
        "schemes": [
            {
                "id": "synthetic-karnataka",
                "name": "Synthetic Karnataka Test Scheme",
                "short_name": "SKTS",
                "aliases": [],
                "eligibility_rules": [
                    {
                        "id": "state_rule",
                        "field": "state",
                        "operator": "in",
                        "value": ["Karnataka", "KA"],
                        "effect": "require",
                        "description": "Applicant resides in Karnataka.",
                        "pass_message": "Your state is covered by this synthetic scheme.",
                        "fail_message": "This synthetic scheme is limited to Karnataka.",
                        "unknown_message": "Your state is required.",
                        "question": "Which state do you live in?",
                        "priority": 1,
                    }
                ],
                "jurisdiction": {
                    "country": "India",
                    "level": "state",
                    "states": ["Karnataka"],
                },
                "required_documents": [],
                "application_process": [],
                "source": "Synthetic test record",
                "source_url": "https://example.invalid/synthetic-test-only",
                "last_verified": "2026-08-20",
                "source_type": "synthetic_test",
                "status": "test_only",
            }
        ],
    }
    injected = SchemeEligibilityEngine(dataset=dataset)

    assert injected.check_eligibility("synthetic-karnataka", {"state": "KA"})[
        "status"
    ] == LIKELY_ELIGIBLE
    assert injected.check_eligibility(
        "synthetic-karnataka", {"state": "Kerala"}
    )["status"] == LIKELY_NOT_ELIGIBLE

    missing = injected.check_eligibility("synthetic-karnataka", {})
    assert missing["status"] == NOT_ENOUGH_INFORMATION
    assert missing["next_questions"] == [
        {
            "rule_id": "state_rule",
            "field": "state",
            "question": "Which state do you live in?",
            "reason": "missing",
        }
    ]


def test_zero_question_limit_returns_no_questions(engine: SchemeEligibilityEngine):
    result = engine.check_eligibility("apy", {}, max_questions=0)

    assert result["unknown_conditions"]
    assert result["next_questions"] == []
