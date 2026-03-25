"""Escalation service — severity classification and routing."""

from __future__ import annotations

import logging

from backend.config import get_settings
from backend.models.schemas import EscalationInfo

logger = logging.getLogger("chakravyuha")

# Keywords mapped to severity levels
HIGH_SEVERITY_KEYWORDS = {
    "murder", "kill", "death", "rape", "sexual assault", "kidnap", "abduct",
    "acid attack", "terrorism", "terrorist", "bomb", "suicide", "die",
    "life threatening", "weapon", "gun", "knife", "hostage", "trafficking",
    "hatya", "balatkaar", "apmaan", "maut", "maar", "aatankvad",
}

MEDIUM_SEVERITY_KEYWORDS = {
    "assault", "hurt", "grievous", "robbery", "dacoity", "extortion",
    "domestic violence", "dowry", "harassment", "stalking", "threat",
    "blackmail", "arson", "riot", "gang", "marpeet", "dhamki", "loot",
}

EMERGENCY_KEYWORDS = {
    "help", "emergency", "urgent", "danger", "dying", "bleeding",
    "bachao", "madad", "emergency", "jaldi",
}


class EscalationService:
    """Classify severity and route to appropriate authority."""

    def classify_severity(self, text: str, section_ids: list[str] | None = None) -> str:
        """Classify query severity as HIGH, MEDIUM, or LOW."""
        text_lower = text.lower()
        words = set(text_lower.split())

        if words & HIGH_SEVERITY_KEYWORDS or words & EMERGENCY_KEYWORDS:
            return "HIGH"

        if words & MEDIUM_SEVERITY_KEYWORDS:
            return "MEDIUM"

        # Check section-based severity
        high_sections = {
            "BNS-103", "BNS-104", "BNS-109", "BNS-65", "BNS-66",
            "BNS-70", "BNS-69", "BNS-140", "BNS-152",
        }
        if section_ids:
            if set(section_ids) & high_sections:
                return "HIGH"

        return "LOW"

    def get_escalation_info(self, severity: str, text: str = "") -> EscalationInfo:
        """Get escalation routing based on severity."""
        settings = get_settings()

        if severity == "HIGH":
            return EscalationInfo(
                severity="HIGH",
                should_escalate=True,
                contacts=[
                    {"name": "Police", "number": settings.police_helpline, "type": "emergency"},
                    {"name": "NALSA Helpline", "number": settings.nalsa_helpline, "type": "legal_aid"},
                    {"name": "Women Helpline", "number": settings.women_helpline, "type": "women"},
                    {"name": "Child Helpline", "number": settings.child_helpline, "type": "child"},
                ],
                message=(
                    "⚠️ This appears to be a SERIOUS legal matter requiring immediate attention. "
                    f"Please contact the Police ({settings.police_helpline}) or "
                    f"NALSA Helpline ({settings.nalsa_helpline}) for free legal aid immediately. "
                    "Do not rely solely on this tool for such matters."
                ),
            )

        if severity == "MEDIUM":
            return EscalationInfo(
                severity="MEDIUM",
                should_escalate=True,
                contacts=[
                    {"name": "NALSA Helpline", "number": settings.nalsa_helpline, "type": "legal_aid"},
                    {"name": "Tele-Law Service", "number": "1800-11-0031", "type": "legal_aid"},
                ],
                message=(
                    "This matter may require professional legal assistance. "
                    f"Consider contacting NALSA ({settings.nalsa_helpline}) for free legal aid "
                    "or the Tele-Law Service (1800-11-0031) for free legal consultation."
                ),
            )

        return EscalationInfo(
            severity="LOW",
            should_escalate=False,
            contacts=[
                {"name": "NALSA Helpline", "number": settings.nalsa_helpline, "type": "legal_aid"},
            ],
            message="",
        )


# Singleton
_escalation_service: EscalationService | None = None


def get_escalation_service() -> EscalationService:
    """Get or create the EscalationService singleton."""
    global _escalation_service
    if _escalation_service is None:
        _escalation_service = EscalationService()
    return _escalation_service
