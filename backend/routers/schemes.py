"""Explainable, rule-driven government-scheme eligibility endpoints."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.legal.scheme_eligibility import SchemeEligibilityEngine, SchemeNotFoundError
from backend.models.schemas import (
    EligibilityCondition,
    KnowledgeStatus,
    Provenance,
    SchemeEligibilityRequest,
    SchemeEligibilityResult,
    SchemeGuidedCheckResponse,
)


router = APIRouter(prefix="/api/schemes", tags=["Government Schemes"])


@lru_cache(maxsize=1)
def get_scheme_engine() -> SchemeEligibilityEngine:
    """Return the deterministic scheme engine."""
    return SchemeEligibilityEngine()


def _summary(scheme: dict[str, Any]) -> dict[str, Any]:
    """Return citizen-facing catalogue fields without hiding provenance."""
    return {
        "id": scheme["id"],
        "name": scheme["name"],
        "short_name": scheme.get("short_name", ""),
        "description": scheme.get("description", ""),
        "benefit_summary": scheme.get("benefit_summary", ""),
        "target_group": scheme.get("target_group", ""),
        "jurisdiction": scheme.get("jurisdiction", {}),
        "required_documents": scheme.get("required_documents", []),
        "application_process": scheme.get("application_process", []),
        "official_portal_url": scheme.get("official_portal_url"),
        "contact_guidance": scheme.get("contact_guidance"),
        "source": scheme.get("source"),
        "source_url": scheme.get("source_url"),
        "source_type": scheme.get("source_type"),
        "effective_date": scheme.get("effective_date"),
        "last_verified": scheme.get("last_verified"),
        "status": scheme.get("status"),
        "verification_note": scheme.get("verification_note"),
    }


def _condition(item: dict[str, Any], outcome: str) -> EligibilityCondition:
    return EligibilityCondition(
        rule_id=item["rule_id"],
        description=item.get("description", ""),
        field=item["field"],
        outcome=outcome,
        explanation=item.get("explanation", ""),
        source_url=item.get("source_url"),
        reason=item.get("reason"),
        question=item.get("question"),
    )


def _result(raw: dict[str, Any]) -> SchemeEligibilityResult:
    jurisdiction = raw.get("jurisdiction") or {}
    if isinstance(jurisdiction, dict):
        jurisdiction_label = jurisdiction.get("country", "India")
        if jurisdiction.get("level"):
            jurisdiction_label += f" ({jurisdiction['level']})"
    else:
        jurisdiction_label = str(jurisdiction)
        jurisdiction = {"label": jurisdiction_label}
    record_status = str(raw.get("record_status", "requires_verification"))
    knowledge_status = (
        KnowledgeStatus.VERIFIED
        if record_status.startswith("verified")
        else KnowledgeStatus.REQUIRES_VERIFICATION
    )
    return SchemeEligibilityResult(
        scheme_id=raw["scheme_id"],
        scheme_name=raw["scheme_name"],
        short_name=raw.get("short_name", ""),
        status=raw["status"],
        matched_conditions=[_condition(item, "matched") for item in raw["matched_conditions"]],
        unknown_conditions=[_condition(item, "unknown") for item in raw["unknown_conditions"]],
        potential_disqualifiers=[
            _condition(item, "potential_disqualifier")
            for item in raw["potential_disqualifiers"]
        ],
        why=raw["why"],
        required_documents=raw.get("required_documents", []),
        application_process=raw.get("application_process", []),
        official_portal_url=raw.get("official_portal_url"),
        helpline=raw.get("helpline"),
        contact_guidance=raw.get("contact_guidance"),
        jurisdiction=jurisdiction,
        next_questions=raw.get("next_questions", []),
        record_status=record_status,
        verification_note=raw.get("verification_note"),
        evaluation_warnings=raw.get("evaluation_warnings", []),
        disclaimer=raw.get("disclaimer", ""),
        provenance=Provenance(
            source=raw["source"],
            source_url=raw["source_url"],
            source_type=raw.get("source_type", "official_government"),
            jurisdiction=jurisdiction_label,
            effective_date=raw.get("effective_date"),
            last_verified=raw["last_verified"],
            status=knowledge_status,
        ),
    )


def _evaluate(request: SchemeEligibilityRequest, guided: bool) -> SchemeGuidedCheckResponse:
    engine = get_scheme_engine()
    profile = request.profile.model_dump(exclude_none=True)
    identifiers = list(request.scheme_ids)
    if request.scheme_id:
        identifiers.insert(0, request.scheme_id)
    identifiers = list(dict.fromkeys(identifiers))
    try:
        raw_results = (
            [
                engine.check_eligibility(
                    identifier,
                    profile,
                    max_questions=1 if guided else request.max_questions,
                )
                for identifier in identifiers
            ]
            if identifiers
            else engine.check_all(
                profile,
                max_questions=1 if guided else request.max_questions,
            )
        )
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    results = [_result(raw) for raw in raw_results]
    questions: list[dict[str, Any]] = []
    seen_fields: set[str] = set()
    for result in results:
        for question in result.next_questions:
            field = question.get("field", "")
            if field and field not in seen_fields:
                seen_fields.add(field)
                questions.append(question)
            if len(questions) >= request.max_questions:
                break
        if len(questions) >= request.max_questions:
            break
    return SchemeGuidedCheckResponse(
        results=results,
        next_questions=questions,
        complete=not bool(questions),
    )


@router.get("/list")
async def list_schemes() -> dict[str, Any]:
    """List the small, source-verified scheme catalogue."""
    engine = get_scheme_engine()
    return {
        "schemes": [_summary(scheme) for scheme in engine.list_schemes()],
        "metadata": engine.metadata,
    }


@router.get("/search")
async def search_schemes(q: str = Query(default="", max_length=300)) -> dict[str, Any]:
    """Search verified scheme descriptions and target groups."""
    return {"schemes": [_summary(scheme) for scheme in get_scheme_engine().search_schemes(q)]}


@router.get("/{scheme_id}")
async def get_scheme(scheme_id: str) -> dict[str, Any]:
    """Return one scheme, including eligibility rules and provenance."""
    try:
        return get_scheme_engine().get_scheme(scheme_id)
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/check-eligibility", response_model=SchemeGuidedCheckResponse)
async def check_eligibility(request: SchemeEligibilityRequest) -> SchemeGuidedCheckResponse:
    """Deterministically evaluate one, several, or all catalogue schemes."""
    return _evaluate(request, guided=False)


@router.post("/guided-check", response_model=SchemeGuidedCheckResponse)
async def guided_check(request: SchemeEligibilityRequest) -> SchemeGuidedCheckResponse:
    """Return only the next few unanswered questions across candidate schemes."""
    return _evaluate(request, guided=True)
