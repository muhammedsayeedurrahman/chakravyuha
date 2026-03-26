"""National Consumer Helpline (INGRAM) — Consumer complaint filing."""

from backend.agent.openclaw.models import CaptchaType, PortalConfig, PortalStep, StepAction

CONSUMER_HELPLINE_CONFIG = PortalConfig(
    portal_id="consumer_helpline",
    name="National Consumer Helpline (NCH)",
    base_url="https://consumerhelpline.gov.in",
    description="File consumer complaints against companies and service providers",
    login_required=True,
    registration_url="https://consumerhelpline.gov.in/user/signup",
    captcha_type=CaptchaType.IMAGE_TEXT,
    otp_required=True,
    reference_pattern=r"(NCH/\d{4}/\d+|\d{10,})",
    max_file_size_mb=5,
    allowed_file_types=(".pdf", ".jpg", ".png", ".jpeg"),
    required_fields=("name", "email", "mobile", "state", "district", "pin_code"),
    steps=(
        # ── Registration ──
        PortalStep(
            name="Navigate to registration",
            action=StepAction.NAVIGATE,
            url="https://consumerhelpline.gov.in/user/signup",
        ),
        PortalStep(
            name="Fill registration details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "name": "input#name, input[name='name']",
                "email": "input#email, input[name='email']",
                "mobile": "input#mobile, input[name='mobile']",
                "pin_code": "input#pincode, input[name='pincode']",
            },
            ai_fallback_instruction="Fill the consumer registration form with name, email, mobile number and pincode",
        ),
        PortalStep(
            name="Select state and district",
            action=StepAction.SELECT,
            field_mapping={
                "state": "select#state, select[name='state']",
                "district": "select#district, select[name='district']",
            },
        ),
        PortalStep(
            name="Solve registration CAPTCHA",
            action=StepAction.CAPTCHA,
            selectors={
                "captcha_image": "img#captchaImage, img.captcha, img[src*='captcha']",
                "captcha_input": "input#captcha, input[name='captcha']",
            },
        ),
        PortalStep(
            name="Submit registration",
            action=StepAction.CLICK,
            selectors={"submit": "button[type='submit'], input[type='submit'], #registerBtn"},
        ),
        PortalStep(
            name="Enter OTP for verification",
            action=StepAction.OTP,
            selectors={"otp_input": "input#otp, input[name='otp']"},
        ),
        # ── Complaint Filing ──
        PortalStep(
            name="Navigate to complaint form",
            action=StepAction.NAVIGATE,
            url="https://consumerhelpline.gov.in/user/complaint",
        ),
        PortalStep(
            name="Select complaint sector and company",
            action=StepAction.SELECT,
            field_mapping={
                "sector": "select#sector, select[name='sector']",
                "company": "select#company, select[name='company']",
                "complaint_category": "select#category, select[name='category']",
            },
            ai_fallback_instruction="Select the sector, company name, and complaint category from the dropdown menus",
        ),
        PortalStep(
            name="Fill complaint details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "complaint_details": "textarea#complaint, textarea[name='complaint_details']",
                "brand": "input#brand, input[name='brand']",
            },
            ai_fallback_instruction="Fill in the complaint description and brand name",
        ),
        PortalStep(
            name="Upload evidence documents",
            action=StepAction.UPLOAD,
            selectors={"file_input": "input[type='file'], input#document"},
        ),
        PortalStep(
            name="Submit complaint",
            action=StepAction.SUBMIT,
            selectors={"submit": "button[type='submit'], input[value='Submit'], #submitBtn"},
            wait_after="div.success, div.confirmation, .docket-number",
        ),
    ),
)
