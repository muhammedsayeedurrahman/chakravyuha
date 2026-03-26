"""CAPTCHA solver — Gemini Vision for image CAPTCHAs, LLM for text/math."""

from __future__ import annotations

import base64
import logging
import re

from backend.agent.openclaw.models import CaptchaType

logger = logging.getLogger("openclaw.captcha")

MAX_RETRIES = 3


class CaptchaSolver:
    """Multi-strategy CAPTCHA solver using Gemini Vision and LLM."""

    def __init__(self) -> None:
        self._gemini_model = None

    def _get_gemini(self):
        """Lazy-load Gemini generative model."""
        if self._gemini_model is None:
            try:
                import google.generativeai as genai
                from backend.config import GEMINI_API_KEY

                genai.configure(api_key=GEMINI_API_KEY)
                self._gemini_model = genai.GenerativeModel("gemini-2.0-flash")
            except Exception as exc:
                logger.error("Failed to initialize Gemini: %s", exc)
        return self._gemini_model

    async def solve(
        self,
        page,
        captcha_type: CaptchaType,
        captcha_img_selector: str = "img#captchaImage, img.captcha, img[alt*='captcha'], img[alt*='CAPTCHA'], img[src*='captcha']",
        captcha_input_selector: str = "input#captcha, input[name='captcha'], input[name='securityCode'], input#securityCode",
    ) -> str | None:
        """Attempt to solve CAPTCHA on the current page.

        Returns the solution text, or None if all attempts fail.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            logger.info("CAPTCHA solve attempt %d/%d (type=%s)", attempt, MAX_RETRIES, captcha_type)

            solution = None

            if captcha_type == CaptchaType.IMAGE_TEXT:
                solution = await self._solve_image_captcha(page, captcha_img_selector)
            elif captcha_type == CaptchaType.MATH:
                solution = await self._solve_math_captcha(page, captcha_img_selector)
            elif captcha_type == CaptchaType.AUDIO:
                solution = await self._solve_audio_captcha(page)
            elif captcha_type == CaptchaType.NONE:
                return ""

            if solution:
                logger.info("CAPTCHA solution (attempt %d): %s", attempt, solution)
                return solution

            # If we have a refresh button, try refreshing the CAPTCHA
            if attempt < MAX_RETRIES:
                refresh_selectors = [
                    "a[href*='captcha'], button[onclick*='captcha']",
                    "img[onclick*='captcha']",
                    ".captcha-refresh, .refresh-captcha, #refreshCaptcha",
                ]
                for sel in refresh_selectors:
                    try:
                        element = page.locator(sel)
                        if await element.count() > 0:
                            await element.first.click()
                            import asyncio
                            await asyncio.sleep(1.5)
                            break
                    except Exception:
                        continue

        logger.warning("All CAPTCHA attempts exhausted")
        return None

    async def _solve_image_captcha(self, page, img_selector: str) -> str | None:
        """Screenshot the CAPTCHA image and use Gemini Vision to read it."""
        try:
            element = page.locator(img_selector)
            if await element.count() == 0:
                logger.warning("CAPTCHA image not found: %s", img_selector)
                # Fallback: screenshot the whole page and try
                screenshot = await page.screenshot()
            else:
                screenshot = await element.first.screenshot()

            return self._read_captcha_image(screenshot)
        except Exception as exc:
            logger.error("Image CAPTCHA solve failed: %s", exc)
            return None

    async def _solve_math_captcha(self, page, img_selector: str) -> str | None:
        """Solve math-based CAPTCHAs (e.g., 'What is 5 + 3?')."""
        try:
            element = page.locator(img_selector)
            if await element.count() == 0:
                return None

            screenshot = await element.first.screenshot()
            text = self._read_captcha_image(screenshot)

            if text:
                # Try to evaluate math expressions
                math_match = re.search(r"(\d+)\s*([+\-*/x×])\s*(\d+)", text)
                if math_match:
                    a = int(math_match.group(1))
                    op = math_match.group(2)
                    b = int(math_match.group(3))
                    ops = {"+": a + b, "-": a - b, "*": a * b, "x": a * b, "×": a * b, "/": a // b if b else 0}
                    return str(ops.get(op, text))

            return text
        except Exception as exc:
            logger.error("Math CAPTCHA solve failed: %s", exc)
            return None

    async def _solve_audio_captcha(self, page) -> str | None:
        """Download and transcribe audio CAPTCHA."""
        try:
            # Try to find audio CAPTCHA button and switch to it
            audio_btn = page.locator("button[title*='audio'], a[href*='audio'], #audioButton")
            if await audio_btn.count() > 0:
                await audio_btn.first.click()
                import asyncio
                await asyncio.sleep(2)

            # Try to find audio element
            audio_el = page.locator("audio source, audio[src]")
            if await audio_el.count() == 0:
                return None

            audio_src = await audio_el.first.get_attribute("src")
            if not audio_src:
                return None

            # Download and transcribe via Sarvam ASR (already in project)
            from backend.voice.asr import transcribe as sarvam_transcribe

            # Fetch audio bytes
            response = await page.request.get(audio_src)
            audio_bytes = await response.body()

            result = sarvam_transcribe(audio_bytes, language="en-IN")
            return result.get("text")
        except Exception as exc:
            logger.error("Audio CAPTCHA solve failed: %s", exc)
            return None

    def _read_captcha_image(self, image_bytes: bytes) -> str | None:
        """Use Gemini Vision to read text from a CAPTCHA image."""
        model = self._get_gemini()
        if model is None:
            return None

        try:
            b64 = base64.b64encode(image_bytes).decode("utf-8")

            response = model.generate_content([
                {
                    "parts": [
                        {
                            "text": (
                                "Read the CAPTCHA text in this image. "
                                "Return ONLY the exact characters shown, nothing else. "
                                "No spaces, no explanation. Just the raw text/numbers."
                            ),
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": b64,
                            },
                        },
                    ],
                }
            ])

            if response and response.text:
                # Clean up the response — strip whitespace, quotes
                result = response.text.strip().strip("'\"` ")
                logger.info("Gemini CAPTCHA read: '%s'", result)
                return result

        except Exception as exc:
            logger.error("Gemini Vision CAPTCHA read failed: %s", exc)

        return None
