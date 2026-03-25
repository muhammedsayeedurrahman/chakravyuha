"""Case tracker router — CRUD /api/cases."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.case_service import get_case_service

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CreateCaseRequest(BaseModel):
    """Request to create a new case."""
    title: str
    description: str
    sections: list[str] = []
    severity: str = "LOW"


class UpdateCaseRequest(BaseModel):
    """Request to update a case."""
    status: str | None = None
    event: str | None = None
    details: str = ""


@router.post("")
async def create_case(request: CreateCaseRequest) -> dict:
    """Create a new tracked case."""
    service = get_case_service()
    case = service.create_case(
        title=request.title,
        description=request.description,
        sections=request.sections,
        severity=request.severity,
    )
    return {"success": True, "data": case.model_dump()}


@router.get("")
async def list_cases() -> dict:
    """List all tracked cases."""
    service = get_case_service()
    cases = service.list_cases()
    return {"success": True, "data": [c.model_dump() for c in cases], "count": len(cases)}


@router.get("/{case_id}")
async def get_case(case_id: str) -> dict:
    """Get a specific case by ID."""
    service = get_case_service()
    case = service.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return {"success": True, "data": case.model_dump()}


@router.put("/{case_id}")
async def update_case(case_id: str, request: UpdateCaseRequest) -> dict:
    """Update a case status or add timeline event."""
    service = get_case_service()
    case = service.update_case(
        case_id=case_id,
        status=request.status,
        event=request.event,
        details=request.details,
    )
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return {"success": True, "data": case.model_dump()}


@router.delete("/{case_id}")
async def delete_case(case_id: str) -> dict:
    """Delete a case."""
    service = get_case_service()
    deleted = service.delete_case(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return {"success": True, "message": f"Case {case_id} deleted"}
