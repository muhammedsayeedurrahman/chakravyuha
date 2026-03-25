"""Form filing router — POST /api/form/start, POST /api/form/otp."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.models.schemas import FormRequest, FormResponse
from backend.services.form_service import get_form_service

router = APIRouter(prefix="/api/form", tags=["forms"])


class OtpRequest(BaseModel):
    """OTP submission request."""
    portal: str
    otp: str


@router.get("/portals")
async def list_portals() -> dict:
    """List available government portals."""
    service = get_form_service()
    return {"success": True, "data": service.get_available_portals()}


@router.get("/portals/{portal}/fields")
async def get_portal_fields(portal: str) -> dict:
    """Get required fields for a specific portal."""
    service = get_form_service()
    fields = service.get_portal_fields(portal)
    if not fields:
        return {"success": False, "error": f"Unknown portal: {portal}"}
    return {"success": True, "data": fields}


@router.post("/start", response_model=FormResponse)
async def start_form(request: FormRequest) -> FormResponse:
    """Start form filling for a government portal."""
    service = get_form_service()
    return await service.start_form(request.portal, request.user_data)


@router.post("/otp", response_model=FormResponse)
async def submit_otp(request: OtpRequest) -> FormResponse:
    """Submit OTP to continue form filling."""
    service = get_form_service()
    return await service.submit_otp(request.portal, request.otp)
