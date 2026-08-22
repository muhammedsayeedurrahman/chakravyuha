"""Step executor — sequential form-filling engine with retry and recovery."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Awaitable, Callable

from backend.agent.openclaw.browser_engine import BrowserEngine
from backend.agent.openclaw.human_gate import CaptchaGate, ConfirmationGate
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
CaptchaCallback = Callable[[str, bytes | None], None]
ConfirmationCallback = Callable[[str, dict], None]

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
        captcha_solver: object | None,
        otp_gate: OTPGate,
        captcha_gate: CaptchaGate | None = None,
        confirmation_gate: ConfirmationGate | None = None,
    ) -> None:
        self._engine = engine
        # Retained as a positional argument for backwards compatibility only.
        # Automated CAPTCHA solving is deliberately disabled.
        self._legacy_captcha_solver = captcha_solver
        self._otp_gate = otp_gate
        self._captcha_gate = captcha_gate or CaptchaGate()
        self._confirmation_gate = confirmation_gate or ConfirmationGate()

    async def execute_flow(
        self,
        portal: PortalConfig,
        user_data: dict,
        documents: list[str],
        session_id: str,
        on_progress: ProgressCallback | None = None,
        on_otp_waiting: ProgressCallback | None = None,
        on_captcha_waiting: CaptchaCallback | None = None,
        on_confirmation_waiting: ConfirmationCallback | None = None,
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
        external_actions_required = sum(
            1
            for portal_step in portal.steps
            if portal_step.action == StepAction.SUBMIT
            or portal_step.requires_confirmation
        )
        externally_confirmed = 0

        for i, step in enumerate(portal.steps):
            step_label = f"[{i + 1}/{len(portal.steps)}] {step.name}"
            is_external_action = (
                step.action == StepAction.SUBMIT or step.requires_confirmation
            )
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
                        on_captcha_waiting=on_captcha_waiting,
                        on_confirmation_waiting=on_confirmation_waiting,
                    )
                    last_result = result

                    if result.success:
                        steps_completed.append(step.name)
                        if result.screenshot:
                            screenshots.append(result.screenshot)
                        if step.action == StepAction.UPLOAD:
                            doc_index += 1
                        if (
                            step.action == StepAction.SUBMIT
                            or step.requires_confirmation
                        ):
                            if not (
                                result.data.get("human_confirmed")
                                and result.data.get("confirmation_evidence")
                            ):
                                return FlowResult(
                                    portal_id=portal.portal_id,
                                    status=FlowStatus.ERROR,
                                    message=(
                                        "External action lacked required human-confirmation "
                                        "or portal-confirmation evidence."
                                    ),
                                    steps_completed=steps_completed,
                                    screenshots=screenshots,
                                    error="Missing submission confirmation evidence",
                                )
                            externally_confirmed += 1
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

                    # A transmitting click may have reached the portal even if
                    # its confirmation page timed out. Never risk a duplicate
                    # submission by retrying that action automatically.
                    if (
                        failure_type == FailureType.TIMEOUT
                        and attempt <= MAX_RETRIES
                        and not is_external_action
                    ):
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
                    if attempt <= MAX_RETRIES and not is_external_action:
                        await asyncio.sleep(1.0 * attempt)
                        continue
                    break

            if succeeded:
                continue

            # AI fallback is never allowed in a flow that can transmit data:
            # confirmation must correspond to deterministic, user-supplied
            # values rather than inferred DOM interactions.
            if (
                last_result
                and not last_result.success
                and step.ai_fallback_instruction
                and step.action == StepAction.FILL_FORM  # Only for FILL_FORM
                and external_actions_required == 0
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
            if "cancelled by user" in error_msg.lower() or "declined by user" in error_msg.lower():
                failure_status = FlowStatus.CANCELLED
            elif step.action == StepAction.CAPTCHA:
                failure_status = FlowStatus.CAPTCHA_FAILED
            else:
                failure_status = FlowStatus.ERROR
            return FlowResult(
                portal_id=portal.portal_id,
                status=failure_status,
                message=f"Failed at step: {step.name} — {error_msg}",
                steps_completed=steps_completed,
                screenshots=screenshots,
                error=error_msg,
            )

        if externally_confirmed != external_actions_required:
            return FlowResult(
                portal_id=portal.portal_id,
                status=FlowStatus.ERROR,
                message="Flow ended without confirmation for every external submission.",
                steps_completed=steps_completed,
                screenshots=screenshots,
                error="Incomplete external-action confirmation",
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
            message="All configured steps completed with portal confirmation evidence",
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
        on_captcha_waiting: CaptchaCallback | None = None,
        on_confirmation_waiting: ConfirmationCallback | None = None,
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
                if step.requires_confirmation:
                    return await self._confirm_then_execute(
                        step=step,
                        portal=portal,
                        user_data=user_data,
                        documents=documents,
                        session_id=session_id,
                        execute=lambda: self._click_element(step),
                        on_confirmation_waiting=on_confirmation_waiting,
                    )
                return await self._click_element(step)

            case StepAction.UPLOAD:
                return await self._upload_document(step, documents, doc_index)

            case StepAction.CAPTCHA:
                return await self._handle_captcha(
                    step, session_id, on_captcha_waiting
                )

            case StepAction.OTP:
                return await self._handle_otp(step, session_id, on_otp_waiting)

            case StepAction.SUBMIT:
                return await self._confirm_then_execute(
                    step=step,
                    portal=portal,
                    user_data=user_data,
                    documents=documents,
                    session_id=session_id,
                    execute=lambda: self._submit_form(step),
                    on_confirmation_waiting=on_confirmation_waiting,
                )

            case StepAction.WAIT:
                if step.wait_after:
                    await self._engine.wait_for(step.wait_after, timeout=step.timeout_ms)
                return StepResult(step.name, True)

            case _:
                return StepResult(step.name, False, f"Unknown action: {step.action}")

    async def _fill_form(self, step: PortalStep, user_data: dict) -> StepResult:
        """Fill form fields from user data."""
        filled = 0
        missing_keys: list[str] = []
        for data_key, selector in step.field_mapping.items():
            value = user_data.get(data_key, "")
            if not value:
                missing_keys.append(data_key)
                continue
            # Try each selector (comma-separated alternatives)
            for sel in selector.split(","):
                sel = sel.strip()
                if await self._engine.fill_field(sel, str(value)):
                    filled += 1
                    break

        return StepResult(
            step.name,
            success=filled == len(step.field_mapping),
            message=(
                f"Filled {filled}/{len(step.field_mapping)} fields"
                + (f"; missing values: {', '.join(missing_keys)}" if missing_keys else "")
            ),
        )

    async def _select_options(self, step: PortalStep, user_data: dict) -> StepResult:
        """Select dropdown options from user data."""
        selected = 0
        missing_keys: list[str] = []
        for data_key, selector in step.field_mapping.items():
            value = user_data.get(data_key, "")
            if not value:
                missing_keys.append(data_key)
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
            success=selected == len(step.field_mapping),
            message=(
                f"Selected {selected}/{len(step.field_mapping)} dropdowns"
                + (f"; missing values: {', '.join(missing_keys)}" if missing_keys else "")
            ),
        )

    async def _click_element(self, step: PortalStep) -> StepResult:
        """Click a button or link."""
        for name, selector in step.selectors.items():
            for sel in selector.split(","):
                sel = sel.strip()
                if await self._engine.click(sel):
                    confirmation_evidence = False
                    if step.wait_after:
                        confirmation_evidence = await self._engine.wait_for(
                            step.wait_after, timeout=step.timeout_ms
                        )
                        if not confirmation_evidence:
                            return StepResult(
                                step.name,
                                False,
                                "Button clicked, but expected portal confirmation was not observed",
                            )
                    return StepResult(
                        step.name,
                        True,
                        f"Clicked {name}",
                        data={"confirmation_evidence": confirmation_evidence},
                    )
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

    async def _handle_captcha(
        self,
        step: PortalStep,
        session_id: str,
        on_captcha_waiting: CaptchaCallback | None = None,
    ) -> StepResult:
        """Pause for a human-supplied CAPTCHA value; never auto-solve it."""
        captcha_img = step.selectors.get("captcha_image", "img.captcha")
        captcha_input = step.selectors.get("captcha_input", "input#captcha")

        image: bytes | None = None
        try:
            image = await self._engine.screenshot_element(captcha_img)
        except Exception:
            logger.warning("Could not capture CAPTCHA image for human handoff")

        prompt = "Enter the CAPTCHA exactly as shown on the government portal"
        if on_captcha_waiting:
            on_captcha_waiting(prompt, image)

        value = await self._captcha_gate.wait_for_captcha(
            session_id=session_id,
            prompt=prompt,
            image=image,
        )
        if value is None:
            return StepResult(step.name, False, "Human CAPTCHA entry timed out")

        for sel in captcha_input.split(","):
            sel = sel.strip()
            if await self._engine.fill_field(sel, value):
                return StepResult(step.name, True, "CAPTCHA entered by user")

        return StepResult(step.name, False, "Could not fill CAPTCHA input")

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

    async def _confirm_then_execute(
        self,
        *,
        step: PortalStep,
        portal: PortalConfig,
        user_data: dict,
        documents: list[str],
        session_id: str,
        execute: Callable[[], Awaitable[StepResult]],
        on_confirmation_waiting: ConfirmationCallback | None,
    ) -> StepResult:
        """Bind consent to the exact payload, then perform one external action."""

        payload_digest = self._payload_digest(
            portal_id=portal.portal_id,
            step=step,
            user_data=user_data,
            documents=documents,
        )
        pending_action = {
            "portal_id": portal.portal_id,
            "portal_name": portal.name,
            "step_name": step.name,
            "action": step.action.value,
            "subject": str(user_data.get("subject", ""))[:160] or None,
            "ministry": user_data.get("ministry") or None,
            "department": user_data.get("department") or None,
            "description_preview": str(user_data.get("description", ""))[:240] or None,
            "reviewed_fields": self._review_fields(portal, step, user_data),
            "document_names": self._review_document_names(portal, step, documents),
        }
        if on_confirmation_waiting:
            on_confirmation_waiting(payload_digest, pending_action)

        confirmed = await self._confirmation_gate.wait_for_confirmation(
            session_id=session_id,
            payload_digest=payload_digest,
            prompt=f"Confirm the reviewed payload before: {step.name}",
        )
        if confirmed is None:
            return StepResult(step.name, False, "Submission confirmation timed out")
        if not confirmed:
            return StepResult(step.name, False, "Submission cancelled by user")

        result = await execute()
        evidence = bool(result.data.get("confirmation_evidence"))
        if result.success and not evidence:
            return StepResult(
                step.name,
                False,
                "External action occurred, but portal confirmation evidence was not observed",
                screenshot=result.screenshot,
                data={
                    **result.data,
                    "human_confirmed": True,
                    "payload_digest": payload_digest,
                    "confirmation_evidence": False,
                },
            )

        return StepResult(
            step_name=result.step_name,
            success=result.success,
            message=result.message,
            screenshot=result.screenshot,
            data={
                **result.data,
                "human_confirmed": True,
                "payload_digest": payload_digest,
                "confirmation_evidence": evidence,
            },
        )

    @staticmethod
    def _review_fields(
        portal: PortalConfig,
        step: PortalStep,
        user_data: dict,
    ) -> dict:
        """Expose the fields relevant to this action for human review.

        Only fields configured since the preceding external action are shown.
        Authentication secrets are represented as present but never echoed via
        the polling API.
        """

        current_index = next(
            (index for index, candidate in enumerate(portal.steps) if candidate is step),
            len(portal.steps) - 1,
        )
        start_index = 0
        for index, candidate in enumerate(portal.steps[:current_index]):
            if (
                candidate.action == StepAction.SUBMIT
                or candidate.requires_confirmation
            ):
                start_index = index + 1

        keys: list[str] = []
        for candidate in portal.steps[start_index : current_index + 1]:
            for key in candidate.field_mapping:
                if key not in keys:
                    keys.append(key)

        secret_terms = ("password", "otp", "captcha", "secret", "token")
        reviewed: dict = {}
        for key in keys:
            value = user_data.get(key)
            if value in (None, ""):
                continue
            if any(term in key.lower() for term in secret_terms):
                reviewed[key] = "(provided; hidden)"
            else:
                reviewed[key] = value
        return reviewed

    @staticmethod
    def _review_document_names(
        portal: PortalConfig,
        step: PortalStep,
        documents: list[str],
    ) -> list[str]:
        """Show document names only when this submission segment uploads them."""

        current_index = next(
            (index for index, candidate in enumerate(portal.steps) if candidate is step),
            len(portal.steps) - 1,
        )
        start_index = 0
        for index, candidate in enumerate(portal.steps[:current_index]):
            if (
                candidate.action == StepAction.SUBMIT
                or candidate.requires_confirmation
            ):
                start_index = index + 1
        segment = portal.steps[start_index : current_index + 1]
        if not any(candidate.action == StepAction.UPLOAD for candidate in segment):
            return []
        return [Path(path).name for path in documents]

    @staticmethod
    def _payload_digest(
        *,
        portal_id: str,
        step: PortalStep,
        user_data: dict,
        documents: list[str],
    ) -> str:
        payload = {
            "portal_id": portal_id,
            "step_name": step.name,
            "action": step.action.value,
            "user_data": user_data,
            "documents": documents,
        }
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    async def _submit_form(self, step: PortalStep) -> StepResult:
        """Click submit and wait for confirmation."""
        for name, selector in step.selectors.items():
            for sel in selector.split(","):
                sel = sel.strip()
                if await self._engine.click(sel):
                    # Wait for confirmation page
                    if step.wait_after:
                        confirmed = await self._engine.wait_for(
                            step.wait_after, timeout=step.timeout_ms
                        )
                    else:
                        confirmed = await self._engine.wait_for_navigation(
                            timeout=step.timeout_ms
                        )

                    if not confirmed:
                        return StepResult(
                            step.name,
                            False,
                            "Submit clicked, but portal confirmation was not observed",
                            data={"confirmation_evidence": False},
                        )

                    screenshot = await self._engine.screenshot()
                    return StepResult(
                        step.name,
                        True,
                        "Portal confirmation observed after submission",
                        screenshot=screenshot,
                        data={"confirmation_evidence": True},
                    )

        return StepResult(step.name, False, "Submit button not found")
