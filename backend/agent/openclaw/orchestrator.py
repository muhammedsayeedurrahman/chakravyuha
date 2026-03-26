"""OpenClaw Orchestrator — Async form filing with session tracking."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Callable

from backend.agent.openclaw.browser_engine import BrowserEngine
from backend.agent.openclaw.captcha_solver import CaptchaSolver
from backend.agent.openclaw.models import FilingRequest, FlowResult, FlowStatus
from backend.agent.openclaw.otp_gate import OTPGate
from backend.agent.openclaw.portal_registry import PortalRegistry
from backend.agent.openclaw.step_executor import StepExecutor

logger = logging.getLogger("openclaw")


class SessionState:
    """Tracks a single filing session's live state for polling."""

    __slots__ = (
        "session_id", "portal_id", "status", "message",
        "steps_completed", "current_step", "reference_number",
        "error", "result",
    )

    def __init__(self, session_id: str, portal_id: str) -> None:
        self.session_id = session_id
        self.portal_id = portal_id
        self.status: str = "started"
        self.message: str = "Filing started"
        self.steps_completed: list[str] = []
        self.current_step: str = ""
        self.reference_number: str | None = None
        self.error: str | None = None
        self.result: FlowResult | None = None

    def to_dict(self) -> dict:
        """Serialize to API response with next_actions hint."""
        next_actions: list[str] = []
        if self.status == "waiting_otp":
            next_actions = ["POST /api/openclaw/otp with session_id and otp"]
        elif self.status in ("started", "in_progress"):
            next_actions = ["GET /api/openclaw/status/{session_id} to poll"]
        elif self.status == "error":
            next_actions = ["Fix the issue and POST /api/openclaw/file again"]

        return {
            "session_id": self.session_id,
            "portal_id": self.portal_id,
            "status": self.status,
            "message": self.message,
            "current_step": self.current_step,
            "steps_completed": list(self.steps_completed),
            "reference_number": self.reference_number,
            "error": self.error,
            "next_actions": next_actions,
        }


class OpenClawOrchestrator:
    """Async form-filing orchestrator with session tracking.

    Filing runs as a background asyncio task so the HTTP response
    returns immediately with a session_id for polling.
    """

    def __init__(self) -> None:
        self._registry = PortalRegistry()
        self._otp_gate = OTPGate()
        self._sessions: dict[str, SessionState] = {}
        self._engines: dict[str, BrowserEngine] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    @property
    def otp_gate(self) -> OTPGate:
        return self._otp_gate

    def list_portals(self) -> list[dict]:
        return self._registry.list_portals()

    def validate_request(self, portal_id: str, user_data: dict) -> list[str]:
        return self._registry.validate_user_data(portal_id, user_data)

    def get_session(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    # ── Public API ────────────────────────────────────────────────────────

    def start_filing(
        self,
        portal_id: str,
        user_data: dict,
        documents: list[str] | None = None,
    ) -> SessionState:
        """Start filing in background. Returns session state immediately."""
        session_id = str(uuid.uuid4())[:8]
        state = SessionState(session_id, portal_id)
        self._sessions[session_id] = state

        task = asyncio.create_task(
            self._run_filing(session_id, portal_id, user_data, documents or [])
        )
        self._tasks[session_id] = task

        # Clean up finished tasks to avoid memory leaks
        task.add_done_callback(lambda t: self._tasks.pop(session_id, None))

        logger.info("Filing started: session=%s portal=%s", session_id, portal_id)
        return state

    async def file_form(
        self,
        portal_id: str,
        user_data: dict,
        documents: list[str] | None = None,
        on_progress: Callable[[str], None] | None = None,
        headless: bool = True,
    ) -> FlowResult:
        """Synchronous filing — blocks until complete. Used by Gradio UI."""
        session_id = str(uuid.uuid4())[:8]
        state = SessionState(session_id, portal_id)
        self._sessions[session_id] = state

        await self._run_filing(
            session_id, portal_id, user_data, documents or [], headless=headless
        )

        return state.result or FlowResult(
            portal_id=portal_id,
            status=FlowStatus.ERROR,
            error="Filing completed with no result",
        )

    # ── Background runner ─────────────────────────────────────────────────

    async def _run_filing(
        self,
        session_id: str,
        portal_id: str,
        user_data: dict,
        documents: list[str],
        headless: bool = True,
    ) -> None:
        """Execute the full filing flow, updating session state as it goes."""
        state = self._sessions[session_id]

        def progress(msg: str) -> None:
            state.current_step = msg
            state.message = msg
            logger.info("[%s] %s", session_id, msg)

        # Validate portal
        portal = self._registry.get(portal_id)
        if portal is None:
            state.status = "error"
            state.error = f"Unknown portal: {portal_id}. Available: {self._registry.list_ids()}"
            state.message = state.error
            state.result = FlowResult(
                portal_id=portal_id,
                status=FlowStatus.ERROR,
                error=state.error,
            )
            return

        # Validate required fields
        missing = self._registry.validate_user_data(portal_id, user_data)
        if missing:
            state.status = "error"
            state.error = f"Missing required fields: {', '.join(missing)}"
            state.message = state.error
            state.result = FlowResult(
                portal_id=portal_id,
                status=FlowStatus.ERROR,
                error=state.error,
            )
            return

        engine = BrowserEngine(human_delay=portal.human_delay_range)
        self._engines[session_id] = engine

        try:
            # 1. Launch browser
            state.status = "in_progress"
            progress("Launching browser...")
            await engine.launch(headless=headless)

            # 2. Create step executor
            captcha_solver = CaptchaSolver()
            executor = StepExecutor(engine, captcha_solver, self._otp_gate)

            # 3. Execute flow with session-aware progress
            def on_otp_waiting(msg: str) -> None:
                state.status = "waiting_otp"
                state.message = "OTP required — enter OTP to continue"
                logger.info("[%s] Waiting for OTP", session_id)

            progress(f"Starting {portal.name} flow...")
            result = await executor.execute_flow(
                portal=portal,
                user_data=user_data,
                documents=documents,
                session_id=session_id,
                on_progress=progress,
                on_otp_waiting=on_otp_waiting,
            )

            state.steps_completed = list(result.steps_completed)

            # 4. Extract reference number
            if result.status == FlowStatus.SUBMITTED:
                progress("Extracting reference number...")
                page_text = await engine.get_page_text()
                ref_match = re.search(portal.reference_pattern, page_text)

                if ref_match:
                    ref_number = ref_match.group(1)
                    result = result.with_reference(ref_number)
                    progress(f"Reference number: {ref_number}")
                else:
                    ai_ref = await engine.ai_extract(
                        "Find and return the registration number, reference number, "
                        "docket number, or application number shown on this confirmation page"
                    )
                    if ai_ref:
                        result = result.with_reference(ai_ref)
                        progress(f"Reference number (AI): {ai_ref}")
                    else:
                        result = FlowResult(
                            portal_id=portal.portal_id,
                            status=FlowStatus.SUCCESS,
                            message="Form submitted but could not extract reference number.",
                            steps_completed=result.steps_completed,
                        )

            # Finalize state
            state.result = result
            state.reference_number = result.reference_number
            state.status = result.status.value
            state.message = result.message or "Filing complete"
            state.error = result.error

        except Exception as exc:
            logger.error("OpenClaw flow failed [%s]: %s", session_id, exc)
            state.status = "error"
            state.error = str(exc)
            state.message = str(exc)
            state.result = FlowResult(
                portal_id=portal_id,
                status=FlowStatus.ERROR,
                error=str(exc),
            )

        finally:
            self._engines.pop(session_id, None)
            # Don't auto-close browser so user can see result
            # engine is garbage collected or manually closed

    async def close_session(self, session_id: str) -> None:
        """Cancel a running filing and close browser."""
        task = self._tasks.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        engine = self._engines.pop(session_id, None)
        if engine:
            await engine.close()

        self._sessions.pop(session_id, None)


# ── Singleton ─────────────────────────────────────────────────────────────

_openclaw: OpenClawOrchestrator | None = None


def get_openclaw() -> OpenClawOrchestrator:
    """Get or create the OpenClaw singleton."""
    global _openclaw
    if _openclaw is None:
        _openclaw = OpenClawOrchestrator()
    return _openclaw
