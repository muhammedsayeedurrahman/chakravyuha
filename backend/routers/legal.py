"""Legal query router — POST /api/query, GET /api/sections/{id}."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.schemas import QueryRequest, QueryResponse, LegalSection
from backend.services.legal_service import get_legal_service

router = APIRouter(prefix="/api", tags=["legal"])


@router.post("/query", response_model=QueryResponse)
async def query_legal(request: QueryRequest) -> QueryResponse:
    """Free-text legal query — returns matching sections via RAG + keyword search."""
    service = get_legal_service()
    return service.query_rag(request.text, top_k=request.top_k)


@router.get("/sections/{section_id}")
async def get_section(section_id: str) -> dict:
    """Look up a specific legal section by ID (e.g., BNS-103 or IPC-302)."""
    service = get_legal_service()
    section = service.lookup_section(section_id)
    if section is None:
        raise HTTPException(status_code=404, detail=f"Section {section_id} not found")

    result = section.model_dump()

    # Include cross-reference
    corresponding = service.get_corresponding_section(section_id)
    if corresponding:
        result["cross_reference"] = corresponding.model_dump()

    # Include defence strategies
    defence = service.get_defence_strategy(section_id)
    if defence:
        result["defence_strategies"] = defence.get("defences", [])

    return {"success": True, "data": result}


@router.get("/sections")
async def list_sections(act: str | None = None) -> dict:
    """List all sections, optionally filtered by act (BNS or IPC)."""
    service = get_legal_service()
    sections = list(service._section_index.values())

    if act:
        act_lower = act.lower()
        sections = [
            s for s in sections
            if act_lower in s.act.lower()
        ]

    return {
        "success": True,
        "data": [s.model_dump() for s in sections],
        "count": len(sections),
    }


@router.get("/ipc-to-bns/{ipc_id}")
async def ipc_to_bns(ipc_id: str) -> dict:
    """Get the BNS equivalent of an IPC section."""
    service = get_legal_service()
    bns_section = service.get_corresponding_section(ipc_id)
    if bns_section is None:
        raise HTTPException(
            status_code=404,
            detail=f"No BNS equivalent found for {ipc_id}",
        )
    return {"success": True, "data": bns_section.model_dump()}
