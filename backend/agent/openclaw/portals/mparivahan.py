"""mParivahan / Sarathi — Driving license and vehicle services."""

from backend.agent.openclaw.models import CaptchaType, PortalConfig, PortalStep, StepAction

MPARIVAHAN_CONFIG = PortalConfig(
    portal_id="mparivahan",
    name="mParivahan / Sarathi",
    base_url="https://sarathi.parivahan.gov.in/",
    description="Apply for driving license, learner's permit, and vehicle registration services",
    login_required=False,
    registration_url=None,
    captcha_type=CaptchaType.IMAGE_TEXT,
    otp_required=True,
    reference_pattern=r"(LL/[A-Z]+/\d{4}/\d+|[A-Z]{2}\d{2}\s?\d{4}\s?\d+|[A-Z0-9]{10,})",
    max_file_size_mb=2,
    allowed_file_types=(".pdf", ".jpg", ".jpeg", ".png"),
    required_fields=(
        "state", "rto_office", "name", "father_name", "dob", "gender",
        "blood_group", "mobile", "email", "address",
    ),
    steps=(
        # ── State & RTO Selection ──
        PortalStep(
            name="Navigate to Sarathi portal",
            action=StepAction.NAVIGATE,
            url="https://sarathi.parivahan.gov.in/",
        ),
        PortalStep(
            name="Select state",
            action=StepAction.SELECT,
            field_mapping={
                "state": "select#stateList, select[name='state'], select#state_id",
            },
            ai_fallback_instruction="Select the state from the dropdown on the Sarathi portal homepage",
        ),
        PortalStep(
            name="Navigate to learner license application",
            action=StepAction.CLICK,
            selectors={
                "submit": "a[href*='learner'], a:has-text('Learner'), a:has-text('New Learner')",
            },
            ai_fallback_instruction="Click on 'New Learner Licence' or 'Apply for Learner Licence' link",
        ),
        # ── Application Form ──
        PortalStep(
            name="Select RTO office",
            action=StepAction.SELECT,
            field_mapping={
                "rto_office": "select#rtoOffice, select[name='rto'], select#rto_id",
            },
        ),
        PortalStep(
            name="Fill applicant personal details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "name": "input#applicantName, input[name='applicantName'], input#firstName",
                "father_name": "input#fatherName, input[name='fatherName'], input#relName",
                "dob": "input#dateOfBirth, input[name='dob'], input#dob",
                "mobile": "input#mobileNo, input[name='mobile'], input#mobile",
                "email": "input#emailId, input[name='email'], input#email",
            },
            ai_fallback_instruction="Fill the applicant's name, father's name, date of birth, mobile number and email",
        ),
        PortalStep(
            name="Select gender and blood group",
            action=StepAction.SELECT,
            field_mapping={
                "gender": "select#gender, select[name='gender']",
                "blood_group": "select#bloodGroup, select[name='bloodGroup']",
            },
        ),
        PortalStep(
            name="Fill address details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "address": "textarea#address, input[name='address'], textarea#permanentAddress",
                "pin_code": "input#pinCode, input[name='pinCode']",
            },
        ),
        # ── Document Upload ──
        PortalStep(
            name="Upload identity and address proof",
            action=StepAction.UPLOAD,
            selectors={"file_input": "input[type='file'], input#docUpload"},
        ),
        # ── CAPTCHA & Submit ──
        PortalStep(
            name="Solve CAPTCHA",
            action=StepAction.CAPTCHA,
            selectors={
                "captcha_image": "img#captchaImage, img.captcha, img[src*='captcha'], img[alt*='captcha']",
                "captcha_input": "input#captcha, input[name='captchaText'], input#captchaText",
            },
        ),
        PortalStep(
            name="Submit application",
            action=StepAction.SUBMIT,
            selectors={"submit": "button[type='submit'], input[type='submit'], button#submitBtn"},
            wait_after="div.success, div.confirmation, .application-number, span.ref-number",
        ),
        # ── Payment & OTP ──
        PortalStep(
            name="Enter OTP for payment verification",
            action=StepAction.OTP,
            selectors={"otp_input": "input#otp, input[name='otp'], input#paymentOTP"},
        ),
    ),
)
