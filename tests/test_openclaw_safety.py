"""Safety regression tests for OpenClaw human interaction gates."""

from __future__ import annotations

import asyncio

from backend.agent.openclaw.human_gate import CaptchaGate, ConfirmationGate
from backend.agent.openclaw.captcha_solver import CaptchaSolver
from backend.agent.openclaw.models import (
    CaptchaType,
    FlowStatus,
    PortalConfig,
    PortalStep,
    StepAction,
)
from backend.agent.openclaw.otp_gate import OTPGate
from backend.agent.openclaw.portals.cpgrams import CPGRAMS_CONFIG
from backend.agent.openclaw.step_executor import StepExecutor


class FakeEngine:
    def __init__(
        self,
        *,
        confirmation_observed: bool = True,
        raise_on_click: bool = False,
        fill_success: bool = True,
    ):
        self.confirmation_observed = confirmation_observed
        self.raise_on_click = raise_on_click
        self.fill_success = fill_success
        self.click_count = 0
        self.ai_fill_count = 0
        self.filled: list[tuple[str, str]] = []

    async def click(self, selector: str) -> bool:
        self.click_count += 1
        if self.raise_on_click:
            raise TimeoutError("portal click timed out")
        return True

    async def wait_for(self, selector: str, timeout: int = 30000) -> bool:
        return self.confirmation_observed

    async def wait_for_navigation(self, timeout: int = 30000) -> bool:
        return self.confirmation_observed

    async def screenshot(self) -> bytes:
        return b"portal-screen"

    async def screenshot_element(self, selector: str) -> bytes:
        return b"captcha-image"

    async def fill_field(self, selector: str, value: str) -> bool:
        self.filled.append((selector, value))
        return self.fill_success

    async def ai_fill_form(self, instruction: str, user_data: dict) -> dict:
        self.ai_fill_count += 1
        return {"success": True, "confidence": 1.0}


class ForbiddenLegacySolver:
    def __init__(self):
        self.called = False

    async def solve(self, *args, **kwargs):
        self.called = True
        raise AssertionError("Automated CAPTCHA solving must never be called")


def test_legacy_captcha_solver_fails_closed_without_touching_page():
    class ForbiddenPage:
        def __getattr__(self, name):
            raise AssertionError(f"Legacy solver touched portal page: {name}")

    result = asyncio.run(
        CaptchaSolver().solve(ForbiddenPage(), CaptchaType.IMAGE_TEXT)
    )
    assert result is None


async def _wait_until(predicate, attempts: int = 100):
    for _ in range(attempts):
        value = predicate()
        if value:
            return value
        await asyncio.sleep(0)
    raise AssertionError("Expected asynchronous gate was not created")


def _submission_portal() -> PortalConfig:
    return PortalConfig(
        portal_id="test-portal",
        name="Test portal",
        base_url="https://example.invalid",
        captcha_type=CaptchaType.NONE,
        otp_required=False,
        steps=(
            PortalStep(
                name="Submit grievance",
                action=StepAction.SUBMIT,
                selectors={"submit": "button#submit"},
                wait_after="div.confirmation",
            ),
        ),
    )


def test_captcha_is_handed_to_human_and_legacy_solver_is_never_called():
    async def scenario():
        engine = FakeEngine()
        solver = ForbiddenLegacySolver()
        captcha_gate = CaptchaGate()
        executor = StepExecutor(
            engine, solver, OTPGate(), captcha_gate, ConfirmationGate()
        )
        step = PortalStep(
            name="Enter CAPTCHA",
            action=StepAction.CAPTCHA,
            selectors={
                "captcha_image": "img.captcha",
                "captcha_input": "input#captcha",
            },
        )
        callback_values = []
        task = asyncio.create_task(
            executor._handle_captcha(
                step,
                "captcha-session",
                lambda prompt, image: callback_values.append((prompt, image)),
            )
        )

        await _wait_until(lambda: captcha_gate.get_pending("captcha-session"))
        assert solver.called is False
        assert callback_values[0][1] == b"captcha-image"
        assert captcha_gate.submit("captcha-session", "HUMAN7") is True

        result = await task
        assert result.success is True
        assert "by user" in result.message
        assert engine.filled == [("input#captcha", "HUMAN7")]
        assert solver.called is False

    asyncio.run(scenario())


def test_submit_does_not_click_until_matching_payload_confirmation():
    async def scenario():
        engine = FakeEngine()
        gate = ConfirmationGate()
        executor = StepExecutor(engine, None, OTPGate(), CaptchaGate(), gate)
        callback_values = []
        task = asyncio.create_task(
            executor.execute_flow(
                portal=_submission_portal(),
                user_data={"subject": "Reviewed subject", "description": "Reviewed facts"},
                documents=["evidence.pdf"],
                session_id="confirm-session",
                on_confirmation_waiting=lambda digest, action: callback_values.append(
                    (digest, action)
                ),
            )
        )

        pending = await _wait_until(lambda: gate.get_pending("confirm-session"))
        assert engine.click_count == 0
        assert callback_values[0][1]["subject"] == "Reviewed subject"
        assert gate.submit("confirm-session", "0" * 64, True) is False
        assert engine.click_count == 0
        assert gate.submit("confirm-session", pending.payload_digest, True) is True
        assert gate.submit("confirm-session", pending.payload_digest, False) is False

        result = await task
        assert result.status == FlowStatus.SUBMITTED
        assert engine.click_count == 1
        assert "confirmation evidence" in result.message

    asyncio.run(scenario())


def test_declined_confirmation_cancels_without_clicking():
    async def scenario():
        engine = FakeEngine()
        gate = ConfirmationGate()
        executor = StepExecutor(engine, None, OTPGate(), CaptchaGate(), gate)
        task = asyncio.create_task(
            executor.execute_flow(
                portal=_submission_portal(),
                user_data={"description": "Do not submit"},
                documents=[],
                session_id="decline-session",
            )
        )

        pending = await _wait_until(lambda: gate.get_pending("decline-session"))
        assert gate.submit("decline-session", pending.payload_digest, False) is True
        result = await task

        assert result.status == FlowStatus.CANCELLED
        assert engine.click_count == 0

    asyncio.run(scenario())


def test_submit_requires_portal_confirmation_and_is_not_retried():
    async def scenario():
        engine = FakeEngine(confirmation_observed=False)
        gate = ConfirmationGate()
        executor = StepExecutor(engine, None, OTPGate(), CaptchaGate(), gate)
        task = asyncio.create_task(
            executor.execute_flow(
                portal=_submission_portal(),
                user_data={"description": "Reviewed grievance"},
                documents=[],
                session_id="evidence-session",
            )
        )

        pending = await _wait_until(lambda: gate.get_pending("evidence-session"))
        gate.submit("evidence-session", pending.payload_digest, True)
        result = await task

        assert result.status == FlowStatus.ERROR
        assert "confirmation" in (result.error or "").lower()
        assert engine.click_count == 1

    asyncio.run(scenario())


def test_external_click_exception_is_never_automatically_retried():
    async def scenario():
        engine = FakeEngine(raise_on_click=True)
        gate = ConfirmationGate()
        executor = StepExecutor(engine, None, OTPGate(), CaptchaGate(), gate)
        task = asyncio.create_task(
            executor.execute_flow(
                portal=_submission_portal(),
                user_data={"description": "Reviewed grievance"},
                documents=[],
                session_id="exception-session",
            )
        )

        pending = await _wait_until(lambda: gate.get_pending("exception-session"))
        gate.submit("exception-session", pending.payload_digest, True)
        result = await task

        assert result.status == FlowStatus.ERROR
        assert engine.click_count == 1

    asyncio.run(scenario())


def test_payload_digest_changes_when_reviewed_payload_changes():
    step = _submission_portal().steps[0]
    first = StepExecutor._payload_digest(
        portal_id="test-portal",
        step=step,
        user_data={"description": "Version one"},
        documents=[],
    )
    second = StepExecutor._payload_digest(
        portal_id="test-portal",
        step=step,
        user_data={"description": "Version two"},
        documents=[],
    )

    assert len(first) == 64
    assert first != second


def test_ai_form_fallback_is_disabled_for_any_transmitting_flow():
    async def scenario():
        engine = FakeEngine(fill_success=False)
        executor = StepExecutor(
            engine, None, OTPGate(), CaptchaGate(), ConfirmationGate()
        )
        portal = PortalConfig(
            portal_id="external-flow",
            name="External flow",
            base_url="https://example.invalid",
            steps=(
                PortalStep(
                    name="Fill grievance",
                    action=StepAction.FILL_FORM,
                    field_mapping={"description": "textarea#description"},
                    ai_fallback_instruction="Infer and fill the form",
                ),
                PortalStep(
                    name="Submit grievance",
                    action=StepAction.SUBMIT,
                    selectors={"submit": "button#submit"},
                    wait_after="div.confirmation",
                ),
            ),
        )

        result = await executor.execute_flow(
            portal=portal,
            user_data={"description": "Citizen-reviewed text"},
            documents=[],
            session_id="no-ai-session",
        )

        assert result.status == FlowStatus.ERROR
        assert engine.ai_fill_count == 0
        assert engine.click_count == 0

    asyncio.run(scenario())


def test_cpgrams_confirmation_review_is_scoped_to_each_transmitting_action():
    registration_submit = next(
        step for step in CPGRAMS_CONFIG.steps if step.name == "Submit registration"
    )
    grievance_submit = next(
        step for step in CPGRAMS_CONFIG.steps if step.name == "Submit grievance"
    )
    user_data = {
        "name": "Citizen",
        "mobile": "9000000000",
        "subject": "Road grievance",
        "description": "Reviewed grievance facts",
        "ministry": "Citizen-selected live option",
        "department": "Citizen-selected live option",
    }

    registration_fields = StepExecutor._review_fields(
        CPGRAMS_CONFIG, registration_submit, user_data
    )
    grievance_fields = StepExecutor._review_fields(
        CPGRAMS_CONFIG, grievance_submit, user_data
    )

    assert registration_fields["name"] == "Citizen"
    assert registration_fields["mobile"] == "9000000000"
    assert "description" not in registration_fields
    assert grievance_fields == {
        "ministry": "Citizen-selected live option",
        "department": "Citizen-selected live option",
        "subject": "Road grievance",
        "description": "Reviewed grievance facts",
    }
    assert StepExecutor._review_document_names(
        CPGRAMS_CONFIG, registration_submit, [r"C:\evidence\proof.pdf"]
    ) == []
    assert StepExecutor._review_document_names(
        CPGRAMS_CONFIG, grievance_submit, [r"C:\evidence\proof.pdf"]
    ) == ["proof.pdf"]
