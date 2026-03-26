"""eCourts eFiling — Online case filing for Indian courts."""

from backend.agent.openclaw.models import CaptchaType, PortalConfig, PortalStep, StepAction

ECOURTS_CONFIG = PortalConfig(
    portal_id="ecourts",
    name="eCourts eFiling",
    base_url="https://filing.ecourts.gov.in/pdedev/",
    description="File new cases online in High Courts and District Courts",
    login_required=True,
    registration_url="https://filing.ecourts.gov.in/pdedev/?p=registration",
    captcha_type=CaptchaType.IMAGE_TEXT,
    otp_required=True,
    reference_pattern=r"(EFIL/[A-Z]+/[A-Z]+/\d{4}/\d+|[A-Z0-9]{8,})",
    max_file_size_mb=10,
    allowed_file_types=(".pdf",),
    required_fields=(
        "name", "mobile", "email", "identity_type", "identity_number",
        "role", "state", "district",
    ),
    steps=(
        # ── Registration ──
        PortalStep(
            name="Navigate to eFiling registration",
            action=StepAction.NAVIGATE,
            url="https://filing.ecourts.gov.in/pdedev/?p=registration",
        ),
        PortalStep(
            name="Select user role",
            action=StepAction.SELECT,
            field_mapping={
                "role": "select#userType, select[name='userType']",
            },
            ai_fallback_instruction="Select user role: Advocate, Litigant in Person, or Authorized Representative",
        ),
        PortalStep(
            name="Fill registration details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "name": "input#name, input[name='name']",
                "mobile": "input#mobile, input[name='mobile']",
                "email": "input#email, input[name='email']",
                "identity_number": "input#identityNo, input[name='identityNo']",
            },
        ),
        PortalStep(
            name="Select identity proof type",
            action=StepAction.SELECT,
            field_mapping={
                "identity_type": "select#identityType, select[name='identityType']",
            },
        ),
        PortalStep(
            name="Verify with OTP",
            action=StepAction.OTP,
            selectors={"otp_input": "input#otp, input[name='otp']"},
        ),
        # ── Case Filing (5-tab flow) ──
        # Tab 1: Initial Inputs
        PortalStep(
            name="Navigate to new case filing",
            action=StepAction.NAVIGATE,
            url="https://filing.ecourts.gov.in/pdedev/?p=casefiling",
        ),
        PortalStep(
            name="Tab 1: Fill initial inputs",
            action=StepAction.SELECT,
            field_mapping={
                "state": "select#state, select[name='state']",
                "district": "select#district, select[name='district']",
                "establishment": "select#establishment, select[name='establishment']",
                "case_type": "select#caseType, select[name='caseType']",
            },
            ai_fallback_instruction="Select state, district, court establishment, and case type from dropdowns in the Initial Inputs tab",
        ),
        PortalStep(
            name="Click next to litigant details",
            action=StepAction.CLICK,
            selectors={"submit": "button#nextBtn, button.next-btn, input[value='Next']"},
        ),
        # Tab 2: Litigant Details
        PortalStep(
            name="Tab 2: Fill petitioner details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "petitioner_name": "input#petitionerName, input[name='petitionerName']",
                "petitioner_address": "textarea#petitionerAddress, textarea[name='petitionerAddress']",
                "respondent_name": "input#respondentName, input[name='respondentName']",
                "respondent_address": "textarea#respondentAddress, textarea[name='respondentAddress']",
            },
            ai_fallback_instruction="Fill petitioner and respondent details in the Litigant tab",
        ),
        PortalStep(
            name="Click next to fact details",
            action=StepAction.CLICK,
            selectors={"submit": "button#nextBtn, button.next-btn, input[value='Next']"},
        ),
        # Tab 3: Fact Details
        PortalStep(
            name="Tab 3: Fill fact details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "cause_of_action": "textarea#causeOfAction, textarea[name='causeOfAction']",
                "date_of_cause": "input#dateOfCause, input[name='dateOfCause']",
                "facts_description": "textarea#factsDescription, textarea[name='facts']",
            },
            ai_fallback_instruction="Fill the cause of action, date, and facts description in the Fact Details tab",
        ),
        PortalStep(
            name="Click next to case details",
            action=StepAction.CLICK,
            selectors={"submit": "button#nextBtn, button.next-btn, input[value='Next']"},
        ),
        # Tab 4: Case Details
        PortalStep(
            name="Tab 4: Fill case details",
            action=StepAction.FILL_FORM,
            field_mapping={
                "prayer": "textarea#prayer, textarea[name='prayer']",
                "valuation": "input#valuation, input[name='valuation']",
            },
            ai_fallback_instruction="Fill the prayer and case valuation in the Case Details tab",
        ),
        # Tab 5: Document Upload
        PortalStep(
            name="Tab 5: Upload petition and documents",
            action=StepAction.UPLOAD,
            selectors={"file_input": "input[type='file'], input#documentUpload"},
        ),
        PortalStep(
            name="Submit eFiling",
            action=StepAction.SUBMIT,
            selectors={"submit": "button#submitBtn, button[type='submit'], input[value='Submit']"},
            wait_after="div.success, div.confirmation, .efiling-number",
        ),
    ),
)
