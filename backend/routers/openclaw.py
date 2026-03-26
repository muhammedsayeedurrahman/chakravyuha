"""OpenClaw router — async government portal form filing API.

Action space (agent harness pattern):
  POST /api/openclaw/file          → start filing (returns session_id immediately)
  GET  /api/openclaw/status/{id}   → poll progress, steps, OTP status
  POST /api/openclaw/otp           → submit OTP to unblock paused flow
  GET  /api/openclaw/portals       → list supported portals
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from backend.agent.openclaw.orchestrator import get_openclaw

logger = logging.getLogger("openclaw.router")

router = APIRouter(prefix="/api/openclaw", tags=["openclaw"])


# ── Request / Response models ─────────────────────────────────────────────

class FilingRequest(BaseModel):
    """Request to start autonomous form filing."""

    portal_id: str
    user_data: dict[str, str]
    documents: list[str] | None = None


class OTPSubmitRequest(BaseModel):
    """Request to submit OTP."""

    session_id: str
    otp: str


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("/portals")
async def list_portals() -> list[dict]:
    """List all supported government portals."""
    openclaw = get_openclaw()
    return openclaw.list_portals()


@router.post("/file")
async def start_filing(request: FilingRequest) -> dict:
    """Start autonomous form filing — returns immediately with session_id.

    The filing runs in the background. Poll /status/{session_id} for progress.
    """
    openclaw = get_openclaw()

    # Validate before starting
    missing = openclaw.validate_request(request.portal_id, request.user_data)
    if missing:
        return {
            "session_id": None,
            "portal_id": request.portal_id,
            "status": "error",
            "message": f"Missing required fields: {', '.join(missing)}",
            "current_step": "",
            "steps_completed": [],
            "reference_number": None,
            "error": f"Missing: {', '.join(missing)}",
            "next_actions": ["Fill the missing fields and retry"],
        }

    try:
        state = openclaw.start_filing(
            portal_id=request.portal_id,
            user_data=request.user_data,
            documents=request.documents,
        )
        return state.to_dict()
    except Exception as exc:
        logger.error("Failed to start filing: %s", exc)
        return {
            "session_id": None,
            "portal_id": request.portal_id,
            "status": "error",
            "message": str(exc),
            "current_step": "",
            "steps_completed": [],
            "reference_number": None,
            "error": str(exc),
            "next_actions": ["Check backend logs and retry"],
        }


@router.get("/status/{session_id}")
async def get_status(session_id: str) -> dict:
    """Poll the current status of a filing session.

    Returns current step, completed steps, OTP status, and result.
    """
    openclaw = get_openclaw()
    state = openclaw.get_session(session_id)

    if state is None:
        return {
            "session_id": session_id,
            "portal_id": None,
            "status": "not_found",
            "message": f"No filing session found for {session_id}",
            "current_step": "",
            "steps_completed": [],
            "reference_number": None,
            "error": "Session not found or expired",
            "next_actions": ["Start a new filing with POST /api/openclaw/file"],
        }

    return state.to_dict()


@router.post("/otp")
async def submit_otp(request: OTPSubmitRequest) -> dict:
    """Submit OTP to continue a paused form-filing flow."""
    openclaw = get_openclaw()
    success = openclaw.otp_gate.submit_otp(request.session_id, request.otp)

    if success:
        return {
            "success": True,
            "message": "OTP submitted — agent resuming filing...",
            "next_actions": ["Poll GET /api/openclaw/status/{session_id} for result"],
        }

    return {
        "success": False,
        "message": "No pending OTP request for this session.",
        "next_actions": ["Check session_id is correct, or filing may have timed out"],
    }
