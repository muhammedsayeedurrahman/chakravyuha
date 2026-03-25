"""Guided question flow router — POST /api/guided/next."""

from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import GuidedFlowState, GuidedFlowStep
from backend.services.legal_service import get_legal_service

router = APIRouter(prefix="/api/guided", tags=["guided"])


@router.post("/start", response_model=GuidedFlowStep)
async def start_guided_flow() -> GuidedFlowStep:
    """Start a new guided flow session — returns the root question."""
    service = get_legal_service()
    state = GuidedFlowState(current_node="root")
    return service.get_guided_step(state)


@router.post("/next", response_model=GuidedFlowStep)
async def next_guided_step(state: GuidedFlowState) -> GuidedFlowStep:
    """Advance the guided flow based on user's answer."""
    service = get_legal_service()
    if state.selected_answer:
        return service.process_guided_answer(state, state.selected_answer)
    return service.get_guided_step(state)


@router.get("/tree")
async def get_tree() -> dict:
    """Return the full guided decision tree (for debugging/demo)."""
    service = get_legal_service()
    return {"success": True, "data": service._guided_tree}
