"""HTTP endpoints for the end-to-end RTI preparation workflow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response

from backend.legal.rti_assistant import get_rti_assistant
from backend.models.schemas import RTIDraftRequest, RTIDraftResponse, RTIIdentifyRequest, RTIRoutingResult


router = APIRouter(prefix="/api/rti", tags=["RTI Assistant"])


@router.post("/identify-department", response_model=RTIRoutingResult)
async def identify_department(request: RTIIdentifyRequest) -> RTIRoutingResult:
    """Identify a likely authority type while exposing unresolved jurisdiction."""
    return get_rti_assistant().identify_department(request)


@router.post("/draft", response_model=RTIDraftResponse)
async def draft_rti(request: RTIDraftRequest) -> RTIDraftResponse:
    """Prepare editable record requests, an RTI draft, and filing guidance."""
    return get_rti_assistant().prepare_draft(request)


@router.post("/download")
async def download_rti(request: RTIDraftRequest) -> Response:
    """Download a complete citizen-reviewed draft as a UTF-8 text document."""
    draft = get_rti_assistant().prepare_draft(request)
    if draft.status != "ready_for_review":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Complete the missing information before downloading the RTI draft.",
                "missing_information": draft.missing_information,
            },
        )
    return Response(
        content=draft.document_text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{draft.download_filename}"'},
    )


@router.get("/templates")
async def list_rti_templates() -> dict:
    """List sourced, editable record-request patterns by civic topic."""
    return get_rti_assistant().template_catalogue()


@router.get("/guide")
async def rti_guide(
    state: str | None = Query(default=None, max_length=100),
    authority_hint: str | None = Query(default=None, max_length=300),
) -> dict:
    """Return filing guidance with Central-versus-State safeguards."""
    request = RTIIdentifyRequest(
        issue="Request access to identifiable public records",
        state=state,
        authority_hint=authority_hint,
    )
    return get_rti_assistant().filing_guidance(request).model_dump(mode="json")
