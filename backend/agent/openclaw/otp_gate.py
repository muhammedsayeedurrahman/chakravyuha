"""OTP Gate — Pause/resume mechanism for OTP-gated flows."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("openclaw.otp")

OTP_TIMEOUT_SECONDS = 300  # 5 minutes


@dataclass
class OTPRequest:
    """Represents a pending OTP request."""

    session_id: str
    prompt: str
    event: asyncio.Event = field(default_factory=asyncio.Event)
    otp_value: str | None = None
    timed_out: bool = False


class OTPGate:
    """Pause execution and wait for user-provided OTP.

    The agent pauses at OTP steps and prompts the user via the UI.
    This is by design — OTP requires human interaction.
    """

    def __init__(self) -> None:
        self._pending: dict[str, OTPRequest] = {}
        self._callbacks: list = []

    def on_otp_required(self, callback) -> None:
        """Register a callback for when OTP is needed.

        Callback signature: callback(session_id: str, prompt: str) -> None
        Used by the Gradio UI to show the OTP input field.
        """
        self._callbacks.append(callback)

    async def wait_for_otp(self, session_id: str, prompt: str = "Enter OTP sent to your mobile") -> str | None:
        """Block until user provides OTP via UI.

        Args:
            session_id: Unique session identifier.
            prompt: Message to display to the user.

        Returns:
            The OTP string, or None if timed out.
        """
        request = OTPRequest(session_id=session_id, prompt=prompt)
        self._pending[session_id] = request

        # Notify UI that OTP is needed
        for cb in self._callbacks:
            try:
                cb(session_id, prompt)
            except Exception as exc:
                logger.warning("OTP callback failed: %s", exc)

        logger.info("Waiting for OTP (session=%s, timeout=%ds)", session_id, OTP_TIMEOUT_SECONDS)

        # Wait for user to submit OTP (or timeout)
        try:
            await asyncio.wait_for(request.event.wait(), timeout=OTP_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            request.timed_out = True
            logger.warning("OTP timed out for session %s", session_id)
            self._pending.pop(session_id, None)
            return None

        otp = request.otp_value
        self._pending.pop(session_id, None)
        logger.info("OTP received for session %s", session_id)
        return otp

    def submit_otp(self, session_id: str, otp: str) -> bool:
        """Called from Gradio UI when user enters OTP.

        Args:
            session_id: Session that needs the OTP.
            otp: The OTP value entered by user.

        Returns:
            True if OTP was accepted (session was waiting), False otherwise.
        """
        request = self._pending.get(session_id)
        if request is None:
            logger.warning("No pending OTP request for session %s", session_id)
            return False

        request.otp_value = otp
        request.event.set()  # Unblock the waiting coroutine
        return True

    def is_waiting(self, session_id: str) -> bool:
        """Check if a session is currently waiting for OTP."""
        return session_id in self._pending

    def get_prompt(self, session_id: str) -> str | None:
        """Get the OTP prompt for a waiting session."""
        request = self._pending.get(session_id)
        return request.prompt if request else None

    def cancel(self, session_id: str) -> None:
        """Cancel a pending OTP request."""
        request = self._pending.pop(session_id, None)
        if request:
            request.timed_out = True
            request.event.set()
