"""Legal disclaimer utilities for Lexaro."""

from __future__ import annotations

from backend.config import get_settings

DISCLAIMER_BANNER = (
    "⚖️ **LEGAL DISCLAIMER**: Lexaro provides legal INFORMATION, not legal ADVICE. "
    "This tool is for educational and informational purposes only. It does not "
    "constitute legal advice, and no attorney-client relationship is formed. "
    "Always consult a qualified lawyer for legal matters. "
    "In emergencies, contact Police (100) or NALSA (15100)."
)


def append_disclaimer(response_text: str) -> str:
    """Append legal disclaimer to any response text."""
    settings = get_settings()
    return f"{response_text}\n\n---\n_{settings.disclaimer_text}_"


def get_disclaimer_markdown() -> str:
    """Return disclaimer as Gradio-compatible markdown."""
    return DISCLAIMER_BANNER
