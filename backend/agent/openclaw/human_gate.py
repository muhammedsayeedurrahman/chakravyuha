"""Human-interaction gates for CAPTCHA and external submission consent.

CAPTCHAs are never solved by the agent.  The browser flow pauses, exposes the
challenge to the user, and resumes only after the user supplies the value.
Submission consent is bound to a SHA-256 digest of the exact portal payload and
step, preventing a confirmation from being reused for a changed payload.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


HUMAN_GATE_TIMEOUT_SECONDS = 600


@dataclass
class CaptchaRequest:
    session_id: str
    prompt: str
    image: bytes | None = None
    event: asyncio.Event = field(default_factory=asyncio.Event)
    value: str | None = None


class CaptchaGate:
    """Pause a flow until the citizen manually answers a CAPTCHA."""

    def __init__(self) -> None:
        self._pending: dict[str, CaptchaRequest] = {}

    async def wait_for_captcha(
        self,
        session_id: str,
        prompt: str,
        image: bytes | None = None,
    ) -> str | None:
        request = CaptchaRequest(session_id=session_id, prompt=prompt, image=image)
        self._pending[session_id] = request
        try:
            await asyncio.wait_for(
                request.event.wait(), timeout=HUMAN_GATE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending.pop(session_id, None)
        return request.value

    def submit(self, session_id: str, value: str) -> bool:
        request = self._pending.get(session_id)
        cleaned = str(value or "").strip()
        if (
            request is None
            or request.event.is_set()
            or not cleaned
            or len(cleaned) > 64
        ):
            return False
        request.value = cleaned
        request.event.set()
        return True

    def get_pending(self, session_id: str) -> CaptchaRequest | None:
        return self._pending.get(session_id)

    def cancel(self, session_id: str) -> None:
        request = self._pending.pop(session_id, None)
        if request:
            request.event.set()


@dataclass
class ConfirmationRequest:
    session_id: str
    payload_digest: str
    prompt: str
    event: asyncio.Event = field(default_factory=asyncio.Event)
    confirmed: bool | None = None


class ConfirmationGate:
    """Require explicit, digest-bound consent immediately before submission."""

    def __init__(self) -> None:
        self._pending: dict[str, ConfirmationRequest] = {}

    async def wait_for_confirmation(
        self,
        session_id: str,
        payload_digest: str,
        prompt: str,
    ) -> bool | None:
        request = ConfirmationRequest(
            session_id=session_id,
            payload_digest=payload_digest,
            prompt=prompt,
        )
        self._pending[session_id] = request
        try:
            await asyncio.wait_for(
                request.event.wait(), timeout=HUMAN_GATE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending.pop(session_id, None)
        return request.confirmed

    def submit(
        self,
        session_id: str,
        payload_digest: str,
        confirmed: bool,
    ) -> bool:
        request = self._pending.get(session_id)
        if (
            request is None
            or request.event.is_set()
            or payload_digest != request.payload_digest
        ):
            return False
        request.confirmed = bool(confirmed)
        request.event.set()
        return True

    def get_pending(self, session_id: str) -> ConfirmationRequest | None:
        return self._pending.get(session_id)

    def cancel(self, session_id: str) -> None:
        request = self._pending.pop(session_id, None)
        if request:
            request.confirmed = False
            request.event.set()
