"""CPGRAMS — Centralized Public Grievance Redress and Monitoring System."""

from backend.agent.openclaw.models import CaptchaType, PortalConfig, PortalStep, StepAction

CPGRAMS_CONFIG = PortalConfig(
    portal_id="cpgrams",
    name="CPGRAMS (Public Grievance)",
    base_url="https://pgportal.gov.in",
    description="Lodge grievances with Central/State Government ministries and departments",
    login_required=True,
    registration_url="https://pgportal.gov.in/Registration",
    captcha_type=CaptchaType.IMAGE_TEXT,
    otp_required=True,
    reference_pattern=r"(DARPG/[A-Z]/\d{4}/\d+|[A-Z]{2,}/[A-Z]/\d{4}/\d+)",
    max_file_size_mb=4,
    allowed_file_types=(".pdf", ".jpg", ".png", ".doc", ".docx"),
    required_fields=("name", "gender", "mobile", "email", "state", "district", "pin_code", "address"),
    steps=(
        # ── Registration Flow ──
        PortalStep(
            name="Navigate to registration page",
            action=StepAction.NAVIGATE,
            url="https://pgportal.gov.in/Registration",
        ),
        PortalStep(
            name="Fill personal details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "name": "input#Name, input[name='Name']",
                "gender": "select#Gender, select[name='Gender']",
                "address": "textarea#Address, textarea[name='Address']",
                "pin_code": "input#PinCode, input[name='PinCode']",
                "mobile": "input#MobileNo, input[name='MobileNo']",
                "email": "input#EmailId, input[name='EmailId']",
            },
            ai_fallback_instruction="Fill the registration form with personal details including name, gender, address, pincode, mobile number and email",
        ),
        PortalStep(
            name="Select state and district",
            action=StepAction.SELECT,
            field_mapping={
                "state": "select#StateId, select[name='StateId']",
                "district": "select#DistrictId, select[name='DistrictId']",
            },
            ai_fallback_instruction="Select the state and district from the dropdown menus",
        ),
        PortalStep(
            name="Solve registration CAPTCHA",
            action=StepAction.CAPTCHA,
            selectors={
                "captcha_image": "img#CaptchaImage, img.captcha-image, img[src*='Captcha']",
                "captcha_input": "input#CaptchaInputText, input[name='CaptchaInputText']",
            },
        ),
        PortalStep(
            name="Submit registration",
            action=StepAction.CLICK,
            selectors={"submit": "button#btnRegister, input[type='submit'], button[type='submit']"},
            wait_after="div.otp-section, input#OTP, div.success-message",
        ),
        PortalStep(
            name="Enter mobile OTP",
            action=StepAction.OTP,
            selectors={"otp_input": "input#OTP, input[name='OTP'], input#MobileOTP"},
        ),
        # ── Grievance Filing Flow ──
        PortalStep(
            name="Navigate to grievance form",
            action=StepAction.NAVIGATE,
            url="https://pgportal.gov.in/Grievance/Lodge",
        ),
        PortalStep(
            name="Select ministry and department",
            action=StepAction.SELECT,
            field_mapping={
                "ministry": "select#MinistryId, select[name='MinistryId']",
                "department": "select#DepartmentId, select[name='DepartmentId']",
            },
            ai_fallback_instruction="Select the appropriate ministry and department for the grievance",
        ),
        PortalStep(
            name="Fill grievance details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "subject": "input#Subject, input[name='Subject']",
                "description": "textarea#Description, textarea[name='Description']",
            },
            ai_fallback_instruction="Fill the grievance subject and description fields",
        ),
        PortalStep(
            name="Upload supporting documents",
            action=StepAction.UPLOAD,
            selectors={"file_input": "input[type='file'], input#FileUpload"},
        ),
        PortalStep(
            name="Solve grievance CAPTCHA",
            action=StepAction.CAPTCHA,
            selectors={
                "captcha_image": "img#CaptchaImage, img.captcha-image, img[src*='Captcha']",
                "captcha_input": "input#CaptchaInputText, input[name='CaptchaInputText']",
            },
        ),
        PortalStep(
            name="Submit grievance",
            action=StepAction.SUBMIT,
            selectors={"submit": "button#btnSubmit, input[value='Submit'], button[type='submit']"},
            wait_after="div.success, div.confirmation, span.registration-number",
        ),
    ),
)
