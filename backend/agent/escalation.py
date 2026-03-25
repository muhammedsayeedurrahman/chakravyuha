"""Auto-escalation to NALSA/police when danger is detected."""

from backend.config import CHILD_HELPLINE, NALSA_HELPLINE, POLICE_HELPLINE, WOMEN_HELPLINE

# Keywords/patterns that trigger escalation
_DANGER_KEYWORDS = [
    "murder", "kill", "killing", "death threat", "rape", "sexual assault",
    "kidnap", "abduct", "imminent danger", "life in danger", "going to die",
    "suicide", "self-harm", "domestic violence", "beating daily",
    "acid attack", "burn", "gun", "pistol", "bomb",
]

_ESCALATION_SECTION_IDS = {
    "BNS-100", "BNS-109", "BNS-63", "BNS-103", "BNS-113",
    "BNS-140", "BNS-66",
}


def check_escalation_needed(query: str, sections: list[dict] | None = None) -> bool:
    """Check if the situation requires immediate escalation.

    Args:
        query: User's query text.
        sections: Retrieved legal sections (optional).

    Returns:
        True if escalation is recommended.
    """
    query_lower = query.lower()

    # Check keywords
    for keyword in _DANGER_KEYWORDS:
        if keyword in query_lower:
            return True

    # Check if any retrieved section is high-severity
    if sections:
        for section in sections:
            sid = section.get("section_id", "")
            if sid in _ESCALATION_SECTION_IDS:
                return True

    return False


def get_escalation_info(location: str | None = None) -> dict:
    """Get emergency contact information for escalation.

    Args:
        location: Optional location string for nearest services.

    Returns:
        Dict with emergency contacts and instructions.
    """
    info = {
        "message": (
            "This appears to be an emergency situation. Please contact the authorities immediately."
        ),
        "contacts": [
            {"name": "Police", "number": POLICE_HELPLINE, "description": "For immediate danger or crime in progress"},
            {"name": "NALSA Legal Aid", "number": NALSA_HELPLINE, "description": "Free legal assistance 24/7"},
            {"name": "Women Helpline", "number": WOMEN_HELPLINE, "description": "For women in distress"},
            {"name": "Child Helpline", "number": CHILD_HELPLINE, "description": "For children in danger"},
        ],
        "instructions": [
            "If you are in immediate danger, call Police (100) first",
            "Move to a safe location if possible",
            "Do not confront the perpetrator",
            "Preserve any evidence (photos, messages, recordings)",
            "NALSA provides FREE legal aid — call 15100",
        ],
    }

    if location:
        info["location_note"] = f"For services near {location}, call NALSA at {NALSA_HELPLINE}"

    return info
