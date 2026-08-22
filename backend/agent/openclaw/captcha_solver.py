"""Compatibility shim for the retired automated CAPTCHA solver.

Government-portal CAPTCHAs are a human verification boundary. OpenClaw now
pauses through :class:`~backend.agent.openclaw.human_gate.CaptchaGate`; it does
not read, solve, refresh, transcribe, or bypass a challenge. The legacy class
name remains importable so older callers fail closed instead of breaking at
import time.
"""

from __future__ import annotations

import logging

from backend.agent.openclaw.models import CaptchaType

logger = logging.getLogger("openclaw.captcha")


class CaptchaSolver:
    """Deprecated no-op that never attempts automated CAPTCHA solving."""

    async def solve(
        self,
        page,
        captcha_type: CaptchaType,
        captcha_img_selector: str = "img#captchaImage, img.captcha",
        captcha_input_selector: str = "input#captcha",
    ) -> None:
        """Return ``None`` without inspecting or interacting with the challenge."""

        del page, captcha_type, captcha_img_selector, captcha_input_selector
        logger.warning(
            "Automated CAPTCHA solving is disabled; use the human CAPTCHA gate"
        )
        return None
