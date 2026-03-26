"""Step executor — sequential form-filling engine with retry and recovery."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Callable

from backend.agent.openclaw.browser_engine import BrowserEngine
from backend.agent.openclaw.captcha_solver import CaptchaSolver
from backend.agent.openclaw.models import (
    FailureType,
    FlowResult,
    FlowStatus,
    PortalConfig,
    PortalStep,
    StepAction,
    StepResult,
)
from backend.agent.openclaw.otp_gate import OTPGate

logger = logging.getLogger("openclaw.executor")

ProgressCallback = Callable[[str], None]

# Retry configuration
MAX_RETRIES = 2


def _noop_progress(msg: str) -> None:
    pass


def _classify_failure(error_msg: str) -> FailureType:
    """Classify a step failure to determine retry/skip/abort behavior."""
    msg = (error_msg or "").lower()
    if any(kw in msg for kw in ("timeout", "timed out", "navigation timeout")):
        return FailureType.TIMEOUT
    if any(kw in msg for kw in ("not found", "no clickable", "no element", "selector")):
        return FailureType.ELEMENT_NOT_FOUND
    return FailureType.UNKNOWN


class StepExecutor:
    """Execute portal steps sequentially with retry and AI fallback."""

    def __init__(
        self,
        engine: BrowserEngine,
        captcha_solver: CaptchaSolver,
        otp_gate: OTPGate,
    ) -> None:
        self._engine = engine
        self._captcha = captcha_solver
        self._otp_gate = otp_gate

    async def execute_flow(
        self,
        portal: PortalConfig,
        user_data: dict,
        documents: list[str],
        session_id: str,
        on_progress: ProgressCallback | None = None,
        on_otp_waiting: ProgressCallback | None = None,
    ) -> FlowResult:
        """Execute all steps in a portal's form-filling flow.

        Args:
            portal: Portal configuration with steps.
            user_data: User-provided form data.
            documents: List of file paths to upload.
            session_id: Unique session ID (for OTP gate).
            on_progress: Callback for real-time progress updates.

        Returns:
            FlowResult with status and reference number.
        """
        progress = on_progress or _noop_progress
        otp_signal = on_otp_waiting or _noop_progress
        steps_completed: list[str] = []
        screenshots: list[bytes] = []
        doc_index = 0

        for i, step in enumerate(portal.steps):
            step_label = f"[{i + 1}/{len(portal.steps)}] {step.name}"
            progress(step_label)
            logger.info("Executing: %s", step_label)

            # Retry loop with failure classification
            last_result: StepResult | None = None
            succeeded = False

            for attempt in range(1, MAX_RETRIES + 2):  # 1 initial + MAX_RETRIES
                try:
                    result = await self._execute_step(
                        step=step,
                        portal=portal,
                        user_data=user_data,
                        documents=documents,
                        doc_index=doc_index,
                        session_id=session_id,
                        on_otp_waiting=otp_signal,
                    )
                    last_result = result

                    if result.success:
                        steps_completed.append(step.name)
                        if result.screenshot:
                            screenshots.append(result.screenshot)
                        if step.action == StepAction.UPLOAD:
                            doc_index += 1
                        logger.info("Step succeeded: %s (attempt %d)", step.name, attempt)
                        succeeded = True
                        break

                    # Classify the failure
                    failure_type = _classify_failure(result.message)
                    logger.warning(
                        "Step failed: %s — %s [failure_type=%s, attempt=%d/%d]",
                        step.name, result.message, failure_type.value,
                        attempt, MAX_RETRIES + 1,
                    )

                    if failure_type == FailureType.TIMEOUT and attempt <= MAX_RETRIES:
                        progress(f"{step_label} (retry {attempt}/{MAX_RETRIES})")
                        logger.info("Retrying step %s (timeout, attempt %d)", step.name, attempt + 1)
                        await asyncio.sleep(1.0 * attempt)  # backoff
                        continue

                    if failure_type == FailureType.ELEMENT_NOT_FOUND:
                        logger.info("Element not found for %s — skipping", step.name)
                        break  # no point retrying

                    if failure_type == FailureType.UNKNOWN:
                        logger.info("Unknown failure for %s — aborting retries", step.name)
                        break  # abort retries

                except Exception as exc:
                    logger.error("Step exception: %s — %s (attempt %d)", step.name, exc, attempt)
                    last_result = StepResult(step.name, False, str(exc))
                    if attempt <= MAX_RETRIES:
                        await asyncio.sleep(1.0 * attempt)
                        continue
                    break

            if succeeded:
                continue

            # Step failed after retries — try controlled AI fallback
            if (
                last_result
                and not last_result.success
                and step.ai_fallback_instruction
                and step.action == StepAction.FILL_FORM  # Only for FILL_FORM
            ):
                progress(f"{step_label} (AI fallback)")
                logger.info("Attempting AI fallback for step: %s", step.name)
                ai_result = await self._engine.ai_fill_form(
                    step.ai_fallback_instruction, user_data
                )
                if ai_result.get("success") and ai_result.get("confidence", 0) > 0.7:
                    steps_completed.append(f"{step.name} (AI)")
                    logger.info(
                        "AI fallback succeeded for %s (confidence=%.2f)",
                        step.name, ai_result.get("confidence", 0),
                    )
                    continue
                logger.warning(
                    "AI fallback rejected for %s (success=%s, confidence=%.2f)",
                    step.name, ai_result.get("success"), ai_result.get("confidence", 0),
                )

            # Non-critical steps can be skipped
            if step.action in (StepAction.UPLOAD, StepAction.WAIT):
                steps_completed.append(f"{step.name} (skipped)")
                logger.info("Skipped non-critical step: %s", step.name)
                continue

            # Critical step failed — abort flow
            error_msg = last_result.message if last_result else "Unknown error"
            return FlowResult(
                portal_id=portal.portal_id,
                status=FlowStatus.ERROR,
                message=f"Failed at step: {step.name} — {error_msg}",
                steps_completed=steps_completed,
                screenshots=screenshots,
                error=error_msg,
            )

        # All steps completed — take final screenshot
        try:
            final_screenshot = await self._engine.screenshot()
            screenshots.append(final_screenshot)
        except Exception:
            pass

        return FlowResult(
            portal_id=portal.portal_id,
            status=FlowStatus.SUBMITTED,
            message="All steps completed successfully",
            steps_completed=steps_completed,
            screenshots=screenshots,
        )

    async def _execute_step(
        self,
        step: PortalStep,
        portal: PortalConfig,
        user_data: dict,
        documents: list[str],
        doc_index: int,
        session_id: str,
        on_otp_waiting: ProgressCallback | None = None,
    ) -> StepResult:
        """Execute a single step based on its action type."""

        match step.action:
            case StepAction.NAVIGATE:
                url = step.url or portal.base_url
                success = await self._engine.navigate(url, timeout=step.timeout_ms)
                return StepResult(step.name, success, "" if success else f"Failed to navigate to {url}")

            case StepAction.FILL_FORM:
                return await self._fill_form(step, user_data)

            case StepAction.SELECT:
                return await self._select_options(step, user_data)

            case StepAction.CLICK:
                return await self._click_element(step)

            case StepAction.UPLOAD:
                return await self._upload_document(step, documents, doc_index)

            case StepAction.CAPTCHA:
                return await self._solve_captcha(step, portal)

            case StepAction.OTP:
                return await self._handle_otp(step, session_id, on_otp_waiting)

            case StepAction.SUBMIT:
                return await self._submit_form(step)

            case StepAction.WAIT:
                if step.wait_after:
                    await self._engine.wait_for(step.wait_after, timeout=step.timeout_ms)
                return StepResult(step.name, True)

            case _:
                return StepResult(step.name, False, f"Unknown action: {step.action}")

    async def _fill_form(self, step: PortalStep, user_data: dict) -> StepResult:
        """Fill form fields from user data."""
        filled = 0
        for data_key, selector in step.field_mapping.items():
            value = user_data.get(data_key, "")
            if not value:
                continue
            # Try each selector (comma-separated alternatives)
            for sel in selector.split(","):
                sel = sel.strip()
                if await self._engine.fill_field(sel, str(value)):
                    filled += 1
                    break

        return StepResult(
            step.name,
            success=filled > 0,
            message=f"Filled {filled}/{len(step.field_mapping)} fields",
        )

    async def _select_options(self, step: PortalStep, user_data: dict) -> StepResult:
        """Select dropdown options from user data."""
        selected = 0
        for data_key, selector in step.field_mapping.items():
            value = user_data.get(data_key, "")
            if not value:
                continue
            for sel in selector.split(","):
                sel = sel.strip()
                if await self._engine.select_dropdown(sel, str(value)):
                    selected += 1
                    break
                # Dropdowns sometimes need a pause for dependent options to load
                await asyncio.sleep(1)

        return StepResult(
            step.name,
            success=selected > 0,
            message=f"Selected {selected}/{len(step.field_mapping)} dropdowns",
        )

    async def _click_element(self, step: PortalStep) -> StepResult:
        """Click a button or link."""
        for name, selector in step.selectors.items():
            for sel in selector.split(","):
                sel = sel.strip()
                if await self._engine.click(sel):
                    if step.wait_after:
                        await self._engine.wait_for(step.wait_after, timeout=step.timeout_ms)
                    return StepResult(step.name, True, f"Clicked {name}")
        return StepResult(step.name, False, "No clickable element found")

    async def _upload_document(self, step: PortalStep, documents: list[str], doc_index: int) -> StepResult:
        """Upload a document file."""
        if doc_index >= len(documents):
            return StepResult(step.name, False, "No document available for upload")

        file_path = documents[doc_index]
        selector = step.selectors.get("file_input", "input[type='file']")
        for sel in selector.split(","):
            sel = sel.strip()
            if await self._engine.upload_file(sel, file_path):
                return StepResult(step.name, True, f"Uploaded {file_path}")

        return StepResult(step.name, False, "File upload failed")

    async def _solve_captcha(self, step: PortalStep, portal: PortalConfig) -> StepResult:
        """Solve CAPTCHA and fill the answer. Falls back to skip after 3 failures."""
        captcha_img = step.selectors.get("captcha_image", "img.captcha")
        captcha_input = step.selectors.get("captcha_input", "input#captcha")

        for captcha_attempt in range(1, 4):  # 3 attempts
            solution = await self._captcha.solve(
                page=self._engine.page,
                captcha_type=portal.captcha_type,
                captcha_img_selector=captcha_img,
                captcha_input_selector=captcha_input,
            )

            if solution is None:
                logger.warning("CAPTCHA solve attempt %d/3 failed", captcha_attempt)
                if captcha_attempt < 3:
                    await asyncio.sleep(1.0)
                continue

            # Fill the CAPTCHA input
            for sel in captcha_input.split(","):
                sel = sel.strip()
                if await self._engine.fill_field(sel, solution):
                    logger.info("CAPTCHA solved on attempt %d: %s", captcha_attempt, solution)
                    return StepResult(step.name, True, f"CAPTCHA solved: {solution}")

        # All 3 attempts failed — skip to allow flow continuation
        logger.warning("CAPTCHA failed after 3 attempts — skipping to continue flow")
        return StepResult(step.name, True, "CAPTCHA skipped after 3 failures")

    async def _handle_otp(
        self, step: PortalStep, session_id: str, on_otp_waiting: ProgressCallback | None = None,
    ) -> StepResult:
        """Pause for OTP and fill it when provided."""
        # Signal that we're about to block for OTP
        if on_otp_waiting:
            on_otp_waiting("WAITING_OTP")
        otp = await self._otp_gate.wait_for_otp(session_id, "Enter the OTP sent to your mobile/email")

        if otp is None:
            return StepResult(step.name, False, "OTP timed out — no response from user")

        # Fill OTP input
        otp_selector = step.selectors.get("otp_input", "input#otp")
        for sel in otp_selector.split(","):
            sel = sel.strip()
            if await self._engine.fill_field(sel, otp):
                # Click verify/submit button if present
                verify_btns = [
                    "button:has-text('Verify')", "button:has-text('Submit OTP')",
                    "input[value='Verify']", "button#verifyOtp",
                ]
                for btn in verify_btns:
                    if await self._engine.click(btn):
                        break
                await asyncio.sleep(2)
                return StepResult(step.name, True, "OTP entered and verified")

        return StepResult(step.name, False, "Could not fill OTP input")

    async def _submit_form(self, step: PortalStep) -> StepResult:
        """Click submit and wait for confirmation."""
        for name, selector in step.selectors.items():
            for sel in selector.split(","):
                sel = sel.strip()
                if await self._engine.click(sel):
                    # Wait for confirmation page
                    if step.wait_after:
                        await self._engine.wait_for(step.wait_after, timeout=step.timeout_ms)
                    else:
                        await self._engine.wait_for_navigation(timeout=step.timeout_ms)

                    screenshot = await self._engine.screenshot()
                    return StepResult(step.name, True, "Form submitted", screenshot=screenshot)

        return StepResult(step.name, False, "Submit button not found")
