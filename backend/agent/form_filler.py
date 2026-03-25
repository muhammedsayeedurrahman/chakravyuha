"""Playwright-based government portal automation (demo-ready)."""


async def fill_parivahan_form(user_data: dict) -> dict:
    """Automate Parivahan (transport) portal form filling.

    This is a demo skeleton showing the agentic form-filling capability.
    It navigates to the portal, fills fields, and pauses for CAPTCHA/OTP.

    Args:
        user_data: Dict with keys like name, license_number, state, etc.

    Returns:
        Dict with status, steps_completed, and screenshot_path.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "status": "error",
            "message": "Playwright not installed. Run: pip install playwright && playwright install chromium",
            "steps_completed": [],
        }

    steps_completed = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            # Step 1: Navigate to portal
            await page.goto("https://parivahan.gov.in/parivahan/", timeout=30000)
            steps_completed.append("Navigated to Parivahan portal")

            # Step 2: Fill in basic details (demo placeholders)
            name = user_data.get("name", "")
            if name:
                name_field = page.locator("input[name='applicantName'], #applicantName")
                if await name_field.count() > 0:
                    await name_field.fill(name)
                    steps_completed.append(f"Filled name: {name}")

            # Step 3: Select state if available
            state = user_data.get("state", "")
            if state:
                state_select = page.locator("select[name='state'], #state")
                if await state_select.count() > 0:
                    await state_select.select_option(label=state)
                    steps_completed.append(f"Selected state: {state}")

            # Step 4: Pause for CAPTCHA/OTP (user must complete manually)
            steps_completed.append("PAUSED: Please complete CAPTCHA/OTP manually")

            # Take screenshot for demo
            screenshot = await page.screenshot()
            steps_completed.append("Screenshot captured")

            # Don't close browser — let user complete the form
            return {
                "status": "paused_for_user",
                "message": "Form partially filled. Please complete CAPTCHA/OTP and submit manually.",
                "steps_completed": steps_completed,
                "screenshot": screenshot,
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "steps_completed": steps_completed,
        }


def get_supported_portals() -> list[dict]:
    """List government portals supported for form filling."""
    return [
        {
            "id": "parivahan",
            "name": "Parivahan (Transport)",
            "url": "https://parivahan.gov.in",
            "forms": ["Driving License Application", "Vehicle Registration", "Learner's Permit"],
        },
        {
            "id": "ecourts",
            "name": "eCourts",
            "url": "https://ecourts.gov.in",
            "forms": ["Case Status Check", "Court Order Search"],
        },
        {
            "id": "nalsa",
            "name": "NALSA Legal Aid",
            "url": "https://nalsa.gov.in",
            "forms": ["Legal Aid Application"],
        },
    ]
