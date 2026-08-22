"""CPGRAMS grievance preparation API built on the existing OpenClaw path."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.schemas import CPGRAMSPrepareRequest, CPGRAMSPrepareResponse
from backend.services.cpgrams_service import get_cpgrams_service


router = APIRouter(prefix="/api/cpgrams", tags=["CPGRAMS Assistant"])


@router.post("/prepare", response_model=CPGRAMSPrepareResponse)
async def prepare_cpgrams(request: CPGRAMSPrepareRequest) -> CPGRAMSPrepareResponse:
    """Classify and draft a grievance for review; this endpoint never submits."""
    try:
        result = get_cpgrams_service().prepare(
            request.grievance,
            state=request.state or "",
            district=request.district or "",
            city=request.city or "",
            locality=request.locality or "",
            authority_hint=request.organisation_hint or "",
            incident_date=request.incident_date or "",
            prior_steps=request.prior_steps,
            prior_reference=request.prior_reference or "",
            desired_resolution=request.desired_resolution or "",
            evidence=request.evidence,
            cpgrams_account_status=request.cpgrams_account_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    authority = result["authority"]
    authority["status"] = "requires_verification"
    return CPGRAMSPrepareResponse(
        **result,
        external_action_requires_confirmation=True,
        disclaimer=(
            "This prepares a citizen-reviewed grievance; it does not file it. Exact portal "
            "authority/category selection must be verified. Login, OTP, CAPTCHA, identity, "
            "consent, and final submission remain human-controlled."
        ),
    )


@router.get("/guide")
async def cpgrams_guide() -> dict:
    """Return official-source filing, exclusion, and tracking guidance."""
    service = get_cpgrams_service()
    return {"filing_guide": service.get_filing_guide(), "sources": service.get_sources()}
