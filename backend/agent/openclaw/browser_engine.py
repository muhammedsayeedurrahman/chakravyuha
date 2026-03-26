"""Browser engine — Playwright with browser-use AI fallback."""

from __future__ import annotations

import asyncio
import logging
import random

logger = logging.getLogger("openclaw.browser")

# Lazy imports — Playwright is optional at module load time
Page = None
Browser = None
BrowserContext = None


class BrowserEngine:
    """Dual-mode browser controller.

    Primary: Direct Playwright selectors (fast, reliable for known DOM).
    Fallback: browser-use AI navigation (handles DOM changes).
    """

    def __init__(self, human_delay: tuple[float, float] = (0.3, 1.0)) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._human_delay = human_delay

    @property
    def page(self) -> Page:
        """Current Playwright page."""
        if self._page is None:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return self._page

    async def launch(self, headless: bool = False) -> None:
        """Launch Chromium browser.

        Raises:
            RuntimeError: If Playwright is not installed or browser binaries are missing.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright is not installed. "
                "Run: pip install playwright && python -m playwright install chromium"
            )

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as exc:
            # Clean up partial state
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            raise RuntimeError(
                f"Failed to launch browser. Ensure browser binaries are installed: "
                f"python -m playwright install chromium. Error: {exc}"
            ) from exc

        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        logger.info("Browser launched (headless=%s)", headless)

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

    async def navigate(self, url: str, timeout: int = 30000) -> bool:
        """Navigate to URL and wait for load."""
        try:
            await self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            await self._human_pause()
            logger.info("Navigated to %s", url)
            return True
        except Exception as exc:
            logger.error("Navigation failed: %s", exc)
            return False

    async def fill_field(self, selector: str, value: str) -> bool:
        """Fill a text input field with human-like typing."""
        try:
            element = self.page.locator(selector)
            if await element.count() == 0:
                logger.warning("Selector not found: %s", selector)
                return False
            await element.click()
            await self._human_pause(0.2, 0.5)
            await element.fill("")
            # Type character by character for human-like behavior
            for char in value:
                await self.page.keyboard.type(char, delay=random.randint(30, 100))
            await self._human_pause()
            logger.info("Filled field %s", selector)
            return True
        except Exception as exc:
            logger.warning("fill_field failed for %s: %s", selector, exc)
            return False

    async def select_dropdown(self, selector: str, value: str) -> bool:
        """Select an option from a dropdown by label or value."""
        try:
            element = self.page.locator(selector)
            if await element.count() == 0:
                return False
            try:
                await element.select_option(label=value)
            except Exception:
                await element.select_option(value=value)
            await self._human_pause()
            logger.info("Selected '%s' in %s", value, selector)
            return True
        except Exception as exc:
            logger.warning("select_dropdown failed for %s: %s", selector, exc)
            return False

    async def click(self, selector: str) -> bool:
        """Click an element."""
        try:
            element = self.page.locator(selector)
            if await element.count() == 0:
                return False
            await element.click()
            await self._human_pause()
            logger.info("Clicked %s", selector)
            return True
        except Exception as exc:
            logger.warning("click failed for %s: %s", selector, exc)
            return False

    async def upload_file(self, selector: str, file_path: str) -> bool:
        """Upload a file to a file input."""
        try:
            element = self.page.locator(selector)
            if await element.count() == 0:
                return False
            await element.set_input_files(file_path)
            await self._human_pause()
            logger.info("Uploaded file to %s", selector)
            return True
        except Exception as exc:
            logger.warning("upload_file failed for %s: %s", selector, exc)
            return False

    async def screenshot(self) -> bytes:
        """Take a full-page screenshot."""
        return await self.page.screenshot(full_page=True)

    async def screenshot_element(self, selector: str) -> bytes | None:
        """Screenshot a specific element (e.g., CAPTCHA image)."""
        try:
            element = self.page.locator(selector)
            if await element.count() == 0:
                return None
            return await element.screenshot()
        except Exception:
            return None

    async def get_page_text(self) -> str:
        """Extract all visible text from the page."""
        return await self.page.inner_text("body")

    async def wait_for(self, selector: str, timeout: int = 30000) -> bool:
        """Wait for an element to appear."""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    async def wait_for_navigation(self, timeout: int = 30000) -> bool:
        """Wait for page navigation to complete."""
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return True
        except Exception:
            return False

    # ── AI-powered fallback methods ───────────────────────────────────────

    async def ai_fill_form(self, instruction: str, data: dict) -> dict:
        """Use browser-use Agent to fill a form with AI guidance.

        Falls back to this when direct selectors fail.
        """
        try:
            from browser_use import Agent
            from langchain_google_genai import ChatGoogleGenerativeAI

            from backend.config import GEMINI_API_KEY

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=GEMINI_API_KEY,
            )

            fields_desc = ", ".join(f"{k}={v}" for k, v in data.items())
            task = f"{instruction}. Fill these values: {fields_desc}"

            agent = Agent(task=task, llm=llm, browser=self._browser)
            result = await agent.run()

            return {"success": True, "result": str(result)}
        except ImportError:
            logger.warning("browser-use not installed, AI fallback unavailable")
            return {"success": False, "error": "browser-use not installed"}
        except Exception as exc:
            logger.error("AI fill_form failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def ai_navigate(self, goal: str) -> bool:
        """Use browser-use to navigate via natural language."""
        result = await self.ai_fill_form(goal, {})
        return result.get("success", False)

    async def ai_extract(self, what: str) -> str | None:
        """Use AI to extract specific information from the page."""
        try:
            from browser_use import Agent
            from langchain_google_genai import ChatGoogleGenerativeAI

            from backend.config import GEMINI_API_KEY

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=GEMINI_API_KEY,
            )

            agent = Agent(
                task=f"Extract this from the current page: {what}",
                llm=llm,
                browser=self._browser,
            )
            result = await agent.run()
            return str(result) if result else None
        except Exception as exc:
            logger.error("AI extract failed: %s", exc)
            return None

    # ── Private helpers ───────────────────────────────────────────────────

    async def _human_pause(self, min_s: float | None = None, max_s: float | None = None) -> None:
        """Random delay to mimic human behavior."""
        lo = min_s if min_s is not None else self._human_delay[0]
        hi = max_s if max_s is not None else self._human_delay[1]
        await asyncio.sleep(random.uniform(lo, hi))
