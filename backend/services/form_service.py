"""Form filing agent — Playwright automation for government portals."""

from __future__ import annotations

import logging

from backend.models.schemas import FormResponse

logger = logging.getLogger("chakravyuha")

# Supported portals and their demo configurations
PORTALS = {
    "parivahan": {
        "name": "Parivahan (Driving License)",
        "url": "https://parivahan.gov.in/",
        "fields": ["name", "dob", "address", "state", "phone"],
        "steps": [
            "Navigate to portal",
            "Select service type",
            "Fill personal details",
            "Upload documents",
            "Enter OTP",
            "Submit application",
        ],
    },
    "efiling": {
        "name": "eFiling (Income Tax)",
        "url": "https://www.incometax.gov.in/",
        "fields": ["pan", "name", "assessment_year", "income"],
        "steps": [
            "Navigate to portal",
            "Login / Register",
            "Select ITR form",
            "Fill income details",
            "Verify with Aadhaar OTP",
            "Submit return",
        ],
    },
    "ecourts": {
        "name": "eCourts (Case Status)",
        "url": "https://ecourts.gov.in/",
        "fields": ["case_number", "year", "court_type", "state"],
        "steps": [
            "Navigate to eCourts portal",
            "Select court complex",
            "Enter case details",
            "View case status",
        ],
    },
    "nalsa": {
        "name": "NALSA (Legal Aid Application)",
        "url": "https://nalsa.gov.in/",
        "fields": ["name", "phone", "case_type", "income_certificate"],
        "steps": [
            "Navigate to NALSA portal",
            "Select legal services authority",
            "Fill application form",
            "Upload income certificate",
            "Submit application",
        ],
    },
}


class FormService:
    """Government portal form-filling agent.

    For hackathon demo: uses pre-configured steps with simulated progress.
    Production would use Playwright for actual browser automation.
    """

    def __init__(self) -> None:
        self._active_sessions: dict[str, dict] = {}

    def get_available_portals(self) -> list[dict[str, str]]:
        """List available government portals."""
        return [
            {"id": pid, "name": info["name"], "url": info["url"]}
            for pid, info in PORTALS.items()
        ]

    def get_portal_fields(self, portal: str) -> list[str]:
        """Get required fields for a portal."""
        info = PORTALS.get(portal)
        return info["fields"] if info else []

    async def start_form(self, portal: str, user_data: dict) -> FormResponse:
        """Start form-filling process for a portal."""
        info = PORTALS.get(portal)
        if info is None:
            return FormResponse(
                portal=portal,
                status="error",
                message=f"Unknown portal: {portal}. Available: {list(PORTALS.keys())}",
            )

        # Validate required fields
        missing = [f for f in info["fields"] if f not in user_data]
        if missing:
            return FormResponse(
                portal=portal,
                status="error",
                current_step="validation",
                message=f"Missing required fields: {', '.join(missing)}",
            )

        # In demo mode, simulate the process
        session_id = f"{portal}_{id(user_data)}"
        self._active_sessions[session_id] = {
            "portal": portal,
            "user_data": user_data,
            "current_step_idx": 0,
            "steps": info["steps"],
        }

        # Simulate first steps
        steps = info["steps"]
        completed = steps[:2]  # Simulate first 2 steps done

        # Check if OTP step exists
        has_otp = any("otp" in s.lower() for s in steps)

        if has_otp:
            return FormResponse(
                portal=portal,
                status="otp_required",
                current_step="Waiting for OTP verification",
                steps_completed=completed,
                message=(
                    f"Form filling started for {info['name']}. "
                    f"Completed {len(completed)}/{len(steps)} steps. "
                    "Please enter the OTP sent to your registered mobile number."
                ),
            )

        return FormResponse(
            portal=portal,
            status="completed",
            current_step="All steps completed",
            steps_completed=steps,
            message=f"Form successfully filled for {info['name']}!",
        )

    async def submit_otp(self, portal: str, otp: str) -> FormResponse:
        """Submit OTP to continue form filling."""
        info = PORTALS.get(portal)
        if info is None:
            return FormResponse(
                portal=portal,
                status="error",
                message="Unknown portal",
            )

        # In demo mode, accept any 6-digit OTP
        if len(otp) != 6 or not otp.isdigit():
            return FormResponse(
                portal=portal,
                status="error",
                current_step="OTP verification",
                message="Invalid OTP. Please enter a 6-digit OTP.",
            )

        return FormResponse(
            portal=portal,
            status="completed",
            current_step="All steps completed",
            steps_completed=info["steps"],
            message=f"OTP verified! Form successfully submitted for {info['name']}.",
        )


# Singleton
_form_service: FormService | None = None


def get_form_service() -> FormService:
    """Get or create the FormService singleton."""
    global _form_service
    if _form_service is None:
        _form_service = FormService()
    return _form_service
