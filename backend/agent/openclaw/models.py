"""Data models for the OpenClaw autonomous form-filling engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class StepAction(str, Enum):
    """Actions a portal step can perform."""

    NAVIGATE = "navigate"
    FILL_FORM = "fill_form"
    SELECT = "select"
    CLICK = "click"
    UPLOAD = "upload"
    CAPTCHA = "captcha"
    OTP = "otp"
    SUBMIT = "submit"
    WAIT = "wait"


class CaptchaType(str, Enum):
    """Types of CAPTCHA encountered on portals."""

    IMAGE_TEXT = "image_text"
    MATH = "math"
    AUDIO = "audio"
    RECAPTCHA = "recaptcha"
    NONE = "none"


class FailureType(str, Enum):
    """Classification of step failures — drives retry/skip/abort logic."""

    TIMEOUT = "timeout"
    ELEMENT_NOT_FOUND = "element_not_found"
    UNKNOWN = "unknown"


class FlowStatus(str, Enum):
    """Status of a form-filling flow."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_OTP = "waiting_otp"
    CAPTCHA_FAILED = "captcha_failed"
    SUBMITTED = "submitted"
    SUCCESS = "success"
    ERROR = "error"


@dataclass(frozen=True)
class PortalStep:
    """A single step in a portal's form-filling flow."""

    name: str
    action: StepAction
    url: str | None = None
    selectors: dict[str, str] = field(default_factory=dict)
    field_mapping: dict[str, str] = field(default_factory=dict)
    wait_after: str | None = None
    timeout_ms: int = 30000
    ai_fallback_instruction: str | None = None


@dataclass(frozen=True)
class PortalConfig:
    """Complete configuration for a government portal."""

    portal_id: str
    name: str
    base_url: str
    description: str = ""
    login_required: bool = False
    registration_url: str | None = None
    steps: tuple[PortalStep, ...] = ()
    captcha_type: CaptchaType = CaptchaType.IMAGE_TEXT
    otp_required: bool = True
    reference_pattern: str = r"([A-Z0-9/\-]+)"
    max_file_size_mb: int = 4
    allowed_file_types: tuple[str, ...] = (".pdf", ".jpg", ".png")
    required_fields: tuple[str, ...] = ()
    human_delay_range: tuple[float, float] = (0.5, 1.5)


@dataclass
class StepResult:
    """Result of executing a single step."""

    step_name: str
    success: bool
    message: str = ""
    screenshot: bytes | None = None
    data: dict = field(default_factory=dict)


@dataclass
class FlowResult:
    """Result of a complete form-filling flow."""

    portal_id: str
    status: FlowStatus
    reference_number: str | None = None
    message: str = ""
    steps_completed: list[str] = field(default_factory=list)
    screenshots: list[bytes] = field(default_factory=list)
    error: str | None = None

    def with_reference(self, ref: str) -> FlowResult:
        """Return a new FlowResult with the reference number set."""
        return FlowResult(
            portal_id=self.portal_id,
            status=FlowStatus.SUCCESS,
            reference_number=ref,
            message=f"Successfully submitted. Reference: {ref}",
            steps_completed=list(self.steps_completed),
            screenshots=list(self.screenshots),
        )


@dataclass(frozen=True)
class FilingRequest:
    """User's request to file a form on a portal."""

    portal_id: str
    user_data: dict = field(default_factory=dict)
    documents: tuple[str, ...] = ()
    session_id: str = ""
