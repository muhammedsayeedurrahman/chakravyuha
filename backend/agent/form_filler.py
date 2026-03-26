"""Government portal form automation — delegates to OpenClaw engine."""

from __future__ import annotations

from backend.agent.openclaw.orchestrator import get_openclaw


async def fill_portal_form(portal_id: str, user_data: dict, documents: list[str] | None = None) -> dict:
    """Autonomously fill a government portal form via OpenClaw.

    Args:
        portal_id: Portal identifier (cpgrams, consumer_helpline, ecourts, mparivahan).
        user_data: Dict with user-provided form data.
        documents: Optional list of file paths to upload.

    Returns:
        Dict with status, reference_number, steps_completed, and message.
    """
    openclaw = get_openclaw()
    result = await openclaw.file_form(
        portal_id=portal_id,
        user_data=user_data,
        documents=documents,
    )
    return {
        "status": result.status.value,
        "reference_number": result.reference_number,
        "message": result.message,
        "steps_completed": result.steps_completed,
        "error": result.error,
    }


def get_supported_portals() -> list[dict]:
    """List government portals supported for form filling."""
    openclaw = get_openclaw()
    portals = openclaw.list_portals()
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "url": p["url"],
            "forms": [p["description"]],
        }
        for p in portals
    ]
