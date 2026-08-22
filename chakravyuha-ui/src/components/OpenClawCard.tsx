"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Card } from "@/components/Card";
import {
  confirmOpenClawSubmission,
  getOpenClawPortals,
  startOpenClawFiling,
  pollOpenClawStatus,
  submitOpenClawCaptcha,
  submitOpenClawOTP,
  type OpenClawPortal,
} from "@/services/api";

const FALLBACK_PORTALS: OpenClawPortal[] = [
  { id: "cpgrams", name: "CPGRAMS (Public Grievance)", url: "", description: "Public grievance portal", required_fields: ["name", "gender", "mobile", "email", "state", "district", "pin_code", "address"] },
  { id: "consumer_helpline", name: "National Consumer Helpline", url: "", description: "Consumer grievance portal", required_fields: ["name", "email", "mobile", "state", "district", "pin_code"] },
  { id: "ecourts", name: "eCourts eFiling", url: "", description: "Court e-filing portal", required_fields: ["name", "mobile", "email", "identity_type", "identity_number", "role", "state", "district"] },
  { id: "mparivahan", name: "mParivahan / Sarathi", url: "", description: "Transport services portal", required_fields: ["state", "rto_office", "name", "father_name", "dob", "gender", "blood_group", "mobile", "email", "address"] },
];

const INDIAN_STATES = [
  "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam",
  "Bihar", "Chandigarh", "Chhattisgarh",
  "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa", "Gujarat",
  "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka",
  "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur",
  "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab",
  "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
  "Uttarakhand", "West Bengal",
];

interface FormData {
  name: string;
  mobile: string;
  email: string;
  state: string;
  district: string;
  pin_code: string;
  gender: string;
  father_name: string;
  dob: string;
  description: string;
  rto_office: string;
  blood_group: string;
  identity_type: string;
  identity_number: string;
  role: string;
  address: string;
  ministry: string;
  department: string;
  subject: string;
}

const INITIAL_FORM: FormData = {
  name: "", mobile: "", email: "", state: "", district: "",
  pin_code: "", gender: "", father_name: "", dob: "", description: "",
  rto_office: "", blood_group: "", identity_type: "", identity_number: "", role: "",
  address: "", ministry: "", department: "", subject: "",
};

function initialForm(userData?: Record<string, string>): FormData {
  if (!userData) return INITIAL_FORM;
  const next = { ...INITIAL_FORM };
  for (const key of Object.keys(next) as Array<keyof FormData>) {
    if (typeof userData[key] === "string") next[key] = userData[key];
  }
  return next;
}

// Terminal statuses that stop polling
const TERMINAL_STATUSES = new Set(["submitted", "success", "error", "not_found", "cancelled"]);

export function OpenClawCard({ initialPortalId = "", initialUserData }: { initialPortalId?: string; initialUserData?: Record<string, string> }) {
  const [portals, setPortals] = useState<OpenClawPortal[]>(FALLBACK_PORTALS);
  const [portalId, setPortalId] = useState(initialPortalId);
  const [form, setForm] = useState<FormData>(() => initialForm(initialUserData));
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [currentStep, setCurrentStep] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [refNumber, setRefNumber] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showOtp, setShowOtp] = useState(false);
  const [otp, setOtp] = useState("");
  const [showCaptcha, setShowCaptcha] = useState(false);
  const [captchaText, setCaptchaText] = useState("");
  const [captchaPrompt, setCaptchaPrompt] = useState("");
  const [captchaImage, setCaptchaImage] = useState("");
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [payloadDigest, setPayloadDigest] = useState("");
  const [pendingAction, setPendingAction] = useState("");
  const [reviewMode, setReviewMode] = useState(false);
  const [reviewAccepted, setReviewAccepted] = useState(false);
  const [nextActions, setNextActions] = useState<string[]>([]);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  useEffect(() => {
    let active = true;
    getOpenClawPortals()
      .then((available) => {
        if (active && available.length > 0) setPortals(available);
      })
      .catch(() => {
        // The fallback list keeps the form usable; the filing API still validates it.
      });
    return () => { active = false; };
  }, []);

  const updateField = useCallback((field: keyof FormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setValidationErrors([]); // clear on edit
    setReviewMode(false);
    setReviewAccepted(false);
  }, []);

  // ── Validation ────────────────────────────────────────────────────────

  const validate = useCallback((): string[] => {
    const errors: string[] = [];
    if (!portalId) errors.push("Select a portal");
    const required = new Set(portals.find((portal) => portal.id === portalId)?.required_fields ?? []);
    const labels: Partial<Record<keyof FormData, string>> = {
      name: "Full name",
      mobile: "Mobile",
      email: "Email",
      state: "State",
      district: "District",
      pin_code: "PIN code",
      gender: "Gender",
      father_name: "Father's name",
      dob: "Date of birth",
      rto_office: "RTO office",
      blood_group: "Blood group",
      identity_type: "Identity type",
      identity_number: "Identity number",
      role: "Role",
      address: "Full address",
    };
    for (const field of required) {
      if (field in form && !form[field as keyof FormData].trim()) {
        errors.push(`${labels[field as keyof FormData] ?? field.replace(/_/g, " ")} is required`);
      }
    }
    if (form.mobile && !/^\d{10}$/.test(form.mobile.trim())) errors.push("Mobile must be 10 digits");
    if (form.email && !/^\S+@\S+\.\S+$/.test(form.email.trim())) errors.push("Enter a valid email address");
    if (form.pin_code && !/^\d{6}$/.test(form.pin_code.trim())) errors.push("PIN code must be 6 digits");
    if (!form.description.trim()) errors.push("Description required");

    return errors;
  }, [portalId, form, portals]);

  // ── Polling ───────────────────────────────────────────────────────────

  const startPolling = useCallback((sid: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);

    pollingRef.current = setInterval(async () => {
      try {
        const res = await pollOpenClawStatus(sid);
        setStatus(res.status);
        setMessage(res.message);
        setCurrentStep(res.current_step);
        setSteps(res.steps_completed);
        setNextActions(res.next_actions ?? []);

        if (res.reference_number) setRefNumber(res.reference_number);
        if (res.error) setError(res.error);

        // Show OTP input when backend is waiting
        if (res.status === "waiting_otp") {
          setShowOtp(true);
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
        }

        if (res.status === "waiting_captcha") {
          setShowCaptcha(true);
          setCaptchaPrompt(res.captcha_prompt || "Enter the CAPTCHA shown by the official portal.");
          setCaptchaImage(res.captcha_image_base64 || "");
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
        }

        if (res.status === "awaiting_confirmation") {
          setShowConfirmation(true);
          setPayloadDigest(res.payload_digest || "");
          setPendingAction(res.pending_action || "Submit the reviewed form to the external portal");
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
        }

        // Stop polling on terminal status
        if (TERMINAL_STATUSES.has(res.status)) {
          if (pollingRef.current) clearInterval(pollingRef.current);
          pollingRef.current = null;
          setLoading(false);
        }
      } catch {
        // Network error — keep polling, it may recover
      }
    }, 2000); // Poll every 2 seconds
  }, []);

  // ── Review and start ─────────────────────────────────────────────────

  const handleReview = useCallback(() => {
    const errors = validate();
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }
    setValidationErrors([]);
    setReviewAccepted(false);
    setReviewMode(true);
  }, [validate]);

  const handleSubmit = useCallback(async () => {
    const errors = validate();
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }
    if (!reviewAccepted) {
      setValidationErrors(["Confirm that you reviewed the filing data before continuing"]);
      return;
    }

    setLoading(true);
    setError(null);
    setMessage("");
    setSteps([]);
    setRefNumber(null);
    setShowOtp(false);
    setShowCaptcha(false);
    setShowConfirmation(false);
    setOtp("");
    setCaptchaText("");
    setCaptchaPrompt("");
    setCaptchaImage("");
    setPayloadDigest("");
    setPendingAction("");
    setNextActions([]);
    setCurrentStep("");
    setStatus("starting");
    setValidationErrors([]);

    try {
      const response = await startOpenClawFiling({
        portal_id: portalId,
        user_data: {
          ...form,
          subject: form.subject.trim() || form.description.slice(0, 100),
          address: form.address.trim(),
        },
      });

      if (response.session_id) {
        setSessionId(response.session_id);
        setStatus(response.status);
        setMessage(response.message);

        if (response.status === "error") {
          setError(response.error);
          setLoading(false);
        } else {
          // Start polling for progress
          startPolling(response.session_id);
        }
      } else {
        // No session_id = immediate error (validation failure)
        setError(response.error);
        setMessage(response.message);
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Filing failed. Is the backend running?");
      setLoading(false);
    }
  }, [portalId, form, validate, startPolling, reviewAccepted]);

  // ── OTP Submit ────────────────────────────────────────────────────────

  const handleOtpSubmit = useCallback(async () => {
    if (!otp || otp.length < 4 || !sessionId) {
      setError("Please enter a valid OTP.");
      return;
    }

    try {
      const response = await submitOpenClawOTP(sessionId, otp);
      if (response.success) {
        setShowOtp(false);
        setOtp("");
        setMessage("OTP submitted — resuming filing...");
        setStatus("in_progress");
        // Resume polling
        startPolling(sessionId);
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "OTP verification failed");
    }
  }, [otp, sessionId, startPolling]);

  const handleCaptchaSubmit = useCallback(async () => {
    if (!captchaText.trim() || !sessionId) {
      setError("Enter the CAPTCHA text shown by the official portal.");
      return;
    }
    try {
      const response = await submitOpenClawCaptcha(sessionId, captchaText.trim());
      if (response.success) {
        setShowCaptcha(false);
        setCaptchaText("");
        setMessage(response.message || "CAPTCHA submitted — resuming assisted filing...");
        setStatus("in_progress");
        setNextActions(response.next_actions ?? []);
        startPolling(sessionId);
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "CAPTCHA verification failed");
    }
  }, [captchaText, sessionId, startPolling]);

  const handleFinalConfirmation = useCallback(async (confirmed: boolean) => {
    if (!sessionId || !payloadDigest) {
      setError("The pending submission could not be verified. Refresh its status before confirming.");
      return;
    }
    try {
      const response = await confirmOpenClawSubmission(sessionId, payloadDigest, confirmed);
      setShowConfirmation(false);
      setMessage(response.message);
      setNextActions(response.next_actions ?? []);
      if (response.success && confirmed) {
        setStatus("in_progress");
        startPolling(sessionId);
      } else {
        setStatus("cancelled");
        setLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Final confirmation failed");
    }
  }, [sessionId, payloadDigest, startPolling]);

  const isActive = loading || (status !== "" && !TERMINAL_STATUSES.has(status));

  return (
    <div className="px-4 flex flex-col gap-4">
      {/* Header */}
      <Card>
        <Card.Header>
          <div className="flex items-center gap-3">
            <span className="text-2xl">{"\uD83E\uDD16"}</span>
            <div>
              <h2 className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                OpenClaw — Assisted Form Filing
              </h2>
              <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                Reviews data first and pauses for CAPTCHA, OTP, and final submission confirmation
              </p>
            </div>
          </div>
        </Card.Header>
        <Card.Body>
          {/* Portal Selection */}
          <div className="mb-4">
            <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>
              Select Government Portal
            </label>
            <select
              value={portalId}
              onChange={(e) => {
                setPortalId(e.target.value);
                setValidationErrors([]);
                setReviewMode(false);
                setReviewAccepted(false);
              }}
              disabled={isActive}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: "var(--color-surface)",
                color: "var(--color-text)",
                border: "1px solid var(--color-border)",
              }}
            >
              <option value="">-- Choose a portal --</option>
              {portals.map((portal) => (
                <option key={portal.id} value={portal.id}>{portal.name}</option>
              ))}
            </select>
          </div>

          {/* Validation Errors */}
          {validationErrors.length > 0 && (
            <div className="p-3 rounded-lg mb-4" style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)" }}>
              <p className="text-xs font-medium mb-1" style={{ color: "rgb(239, 68, 68)" }}>Please fix:</p>
              <ul className="space-y-0.5">
                {validationErrors.map((err, i) => (
                  <li key={i} className="text-xs" style={{ color: "rgb(239, 68, 68)" }}>- {err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Form Fields */}
          {portalId && (
            <div className="grid grid-cols-2 gap-3 mb-4">
              <InputField label="Full Name *" value={form.name} onChange={(v) => updateField("name", v)} placeholder="Enter full name" disabled={isActive} />
              <InputField label="Mobile *" value={form.mobile} onChange={(v) => updateField("mobile", v)} placeholder="10-digit mobile" disabled={isActive} />
              <InputField label="Email *" value={form.email} onChange={(v) => updateField("email", v)} placeholder="email@example.com" disabled={isActive} />
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>Gender</label>
                <select
                  value={form.gender}
                  onChange={(e) => updateField("gender", e.target.value)}
                  disabled={isActive}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
                >
                  <option value="">Select</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>State *</label>
                <select
                  value={form.state}
                  onChange={(e) => updateField("state", e.target.value)}
                  disabled={isActive}
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
                >
                  <option value="">Select state</option>
                  {INDIAN_STATES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <InputField label="District *" value={form.district} onChange={(v) => updateField("district", v)} placeholder="Your district" disabled={isActive} />
              <InputField label="PIN Code *" value={form.pin_code} onChange={(v) => updateField("pin_code", v)} placeholder="6-digit PIN" disabled={isActive} />
              <InputField label="Date of Birth" value={form.dob} onChange={(v) => updateField("dob", v)} placeholder="DD/MM/YYYY" disabled={isActive} />
              <div className="col-span-2">
                <InputField label="Full Address" value={form.address} onChange={(v) => updateField("address", v)} placeholder="House/street/locality — never inferred from PIN code" disabled={isActive} />
              </div>
              {portalId === "cpgrams" && (
                <>
                  <InputField label="Ministry Hint" value={form.ministry} onChange={(v) => updateField("ministry", v)} placeholder="Leave blank unless verified" disabled={isActive} />
                  <InputField label="Department Hint" value={form.department} onChange={(v) => updateField("department", v)} placeholder="Leave blank unless verified" disabled={isActive} />
                  <div className="col-span-2">
                    <InputField label="Grievance Subject" value={form.subject} onChange={(v) => updateField("subject", v)} placeholder="Review the prepared subject" disabled={isActive} />
                  </div>
                </>
              )}
              {portalId === "mparivahan" && (
                <>
                  <InputField label="Father's Name *" value={form.father_name} onChange={(v) => updateField("father_name", v)} placeholder="Father's name" disabled={isActive} />
                  <InputField label="RTO Office *" value={form.rto_office} onChange={(v) => updateField("rto_office", v)} placeholder="e.g. RTO Pune" disabled={isActive} />
                  <div>
                    <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>Blood Group *</label>
                    <select
                      value={form.blood_group}
                      onChange={(e) => updateField("blood_group", e.target.value)}
                      disabled={isActive}
                      className="w-full px-3 py-2 rounded-lg text-sm"
                      style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
                    >
                      <option value="">Select</option>
                      <option value="A+">A+</option>
                      <option value="A-">A-</option>
                      <option value="B+">B+</option>
                      <option value="B-">B-</option>
                      <option value="O+">O+</option>
                      <option value="O-">O-</option>
                      <option value="AB+">AB+</option>
                      <option value="AB-">AB-</option>
                    </select>
                  </div>
                </>
              )}
              {portalId === "ecourts" && (
                <>
                  <div>
                    <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>Role *</label>
                    <select
                      value={form.role}
                      onChange={(e) => updateField("role", e.target.value)}
                      disabled={isActive}
                      className="w-full px-3 py-2 rounded-lg text-sm"
                      style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
                    >
                      <option value="">Select</option>
                      <option value="Advocate">Advocate</option>
                      <option value="Litigant in Person">Litigant in Person</option>
                      <option value="Authorized Representative">Authorized Representative</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>Identity Proof Type *</label>
                    <select
                      value={form.identity_type}
                      onChange={(e) => updateField("identity_type", e.target.value)}
                      disabled={isActive}
                      className="w-full px-3 py-2 rounded-lg text-sm"
                      style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
                    >
                      <option value="">Select</option>
                      <option value="Aadhaar">Aadhaar</option>
                      <option value="PAN">PAN Card</option>
                      <option value="Voter ID">Voter ID</option>
                      <option value="Passport">Passport</option>
                    </select>
                  </div>
                  <InputField label="Identity Number *" value={form.identity_number} onChange={(v) => updateField("identity_number", v)} placeholder="ID number" disabled={isActive} />
                </>
              )}
            </div>
          )}

          {/* Description */}
          {portalId && (
            <div className="mb-4">
              <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>
                Grievance / Complaint / Case Description *
              </label>
              <textarea
                value={form.description}
                onChange={(e) => updateField("description", e.target.value)}
                placeholder="Describe your issue in detail..."
                rows={3}
                maxLength={4000}
                disabled={isActive}
                className="w-full px-3 py-2 rounded-lg text-sm resize-none"
                style={{
                  backgroundColor: "var(--color-surface)",
                  color: "var(--color-text)",
                  border: "1px solid var(--color-border)",
                }}
              />
              <p className="text-xs mt-1" style={{ color: "var(--color-text-faint)" }}>
                {form.description.length}/4000 characters
              </p>
            </div>
          )}

          {/* Review before starting any portal action */}
          {portalId && !reviewMode && (
            <button
              onClick={handleReview}
              disabled={isActive}
              className="w-full py-3 rounded-xl font-bold text-sm transition-all"
              style={{
                background: isActive ? "var(--color-surface)" : "linear-gradient(135deg, var(--color-accent), var(--color-accent-hover))",
                color: isActive ? "var(--color-text-muted)" : "#fff",
                opacity: isActive ? 0.6 : 1,
              }}
            >
              {isActive ? "Assisted filing in progress..." : "Review before assisted filing"}
            </button>
          )}

          {portalId && reviewMode && !isActive && (
            <div className="rounded-xl p-4" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
              <h3 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>Review the data that will be entered</h3>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                <div><dt style={{ color: "var(--color-text-faint)" }}>Portal</dt><dd style={{ color: "var(--color-text)" }}>{portals.find((portal) => portal.id === portalId)?.name ?? portalId}</dd></div>
                <div><dt style={{ color: "var(--color-text-faint)" }}>Name</dt><dd style={{ color: "var(--color-text)" }}>{form.name}</dd></div>
                <div><dt style={{ color: "var(--color-text-faint)" }}>State / district</dt><dd style={{ color: "var(--color-text)" }}>{[form.state, form.district].filter(Boolean).join(", ")}</dd></div>
                <div><dt style={{ color: "var(--color-text-faint)" }}>Contact</dt><dd style={{ color: "var(--color-text)" }}>{form.mobile || form.email}</dd></div>
                {form.subject && <div className="col-span-2"><dt style={{ color: "var(--color-text-faint)" }}>Subject</dt><dd style={{ color: "var(--color-text)" }}>{form.subject}</dd></div>}
                <div className="col-span-2"><dt style={{ color: "var(--color-text-faint)" }}>Description</dt><dd className="mt-1 max-h-36 overflow-y-auto whitespace-pre-wrap rounded-lg p-2" style={{ color: "var(--color-text-muted)", background: "rgba(0,0,0,0.18)" }}>{form.description}</dd></div>
              </dl>
              <label className="mt-3 flex cursor-pointer items-start gap-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
                <input type="checkbox" checked={reviewAccepted} onChange={(event) => setReviewAccepted(event.target.checked)} className="mt-0.5" />
                <span>I reviewed these details. I understand the assistant will pause for CAPTCHA and OTP, and a separate confirmation will be required immediately before external submission.</span>
              </label>
              <div className="mt-3 flex gap-2">
                <button type="button" onClick={() => { setReviewMode(false); setReviewAccepted(false); }} className="rounded-lg px-3 py-2 text-xs" style={{ background: "var(--color-bg-2)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>Edit</button>
                <button type="button" onClick={handleSubmit} disabled={!reviewAccepted} className="flex-1 rounded-lg px-3 py-2 text-xs font-semibold disabled:opacity-40" style={{ background: "var(--color-accent)", color: "#fff" }}>Confirm and start assisted filing</button>
              </div>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Live Progress */}
      {isActive && currentStep && (
        <Card>
          <Card.Header>
            <h3 className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
              Live Progress
            </h3>
          </Card.Header>
          <Card.Body>
            {/* Current step with spinner */}
            <div className="flex items-center gap-2 mb-3">
              <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin"
                style={{ borderColor: "var(--color-accent)", borderTopColor: "transparent" }} />
              <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>
                {currentStep}
              </p>
            </div>

            {/* Completed steps */}
            {steps.length > 0 && (
              <ul className="space-y-1">
                {steps.map((step, i) => (
                  <li key={i} className="text-xs flex items-center gap-2" style={{ color: "var(--color-text-muted)" }}>
                    <span style={{ color: "rgb(34, 197, 94)" }}>{"\u2713"}</span>
                    {step}
                  </li>
                ))}
              </ul>
            )}
          </Card.Body>
        </Card>
      )}

      {/* OTP Section */}
      {showOtp && (
        <Card>
          <Card.Header>
            <h3 className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
              OTP Verification Required
            </h3>
          </Card.Header>
          <Card.Body>
            <p className="text-xs mb-3" style={{ color: "var(--color-text-muted)" }}>
              An OTP has been sent to your registered mobile/email. Enter it below to continue filing.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="Enter 6-digit OTP"
                maxLength={6}
                className="flex-1 px-3 py-2 rounded-lg text-sm"
                style={{
                  backgroundColor: "var(--color-surface)",
                  color: "var(--color-text)",
                  border: "1px solid var(--color-border)",
                }}
              />
              <button
                onClick={handleOtpSubmit}
                className="px-4 py-2 rounded-lg text-sm font-medium"
                style={{ background: "var(--color-accent)", color: "#fff" }}
              >
                Submit OTP
              </button>
            </div>
          </Card.Body>
        </Card>
      )}

      {/* CAPTCHA is always completed by the citizen */}
      {showCaptcha && (
        <Card>
          <Card.Header>
            <h3 className="font-bold text-sm" style={{ color: "var(--color-text)" }}>CAPTCHA action required</h3>
          </Card.Header>
          <Card.Body>
            <p className="text-xs mb-3" style={{ color: "var(--color-text-muted)" }}>{captchaPrompt || "Read the CAPTCHA from the official portal and enter it below."}</p>
            {captchaImage && (
              // The backend returns only the official portal image; it is never solved automatically.
              // eslint-disable-next-line @next/next/no-img-element
              <img src={captchaImage.startsWith("data:") ? captchaImage : `data:image/png;base64,${captchaImage}`} alt="CAPTCHA from the government portal" className="mb-3 max-h-24 rounded-lg" style={{ border: "1px solid var(--color-border)" }} />
            )}
            <div className="flex gap-2">
              <input type="text" value={captchaText} onChange={(event) => setCaptchaText(event.target.value)} placeholder="Enter CAPTCHA exactly" autoComplete="off" className="flex-1 rounded-lg px-3 py-2 text-sm" style={{ backgroundColor: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" }} />
              <button type="button" onClick={handleCaptchaSubmit} className="rounded-lg px-4 py-2 text-sm font-medium" style={{ background: "var(--color-accent)", color: "#fff" }}>Continue</button>
            </div>
          </Card.Body>
        </Card>
      )}

      {/* Exact final external submission gate */}
      {showConfirmation && (
        <Card>
          <Card.Header>
            <h3 className="font-bold text-sm" style={{ color: "var(--color-text)" }}>Final submission confirmation</h3>
          </Card.Header>
          <Card.Body>
            <div className="space-y-3">
              <div className="rounded-lg p-3 text-xs" style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", color: "#f59e0b" }}>
                The next action will affect an external government portal. Nothing will be submitted unless you confirm now.
              </div>
              <p className="text-sm font-medium" style={{ color: "var(--color-text)" }}>{pendingAction}</p>
              <p className="break-all font-mono text-[10px]" style={{ color: "var(--color-text-faint)" }}>Reviewed payload: {payloadDigest}</p>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => handleFinalConfirmation(false)} className="rounded-lg px-4 py-2 text-xs font-semibold" style={{ background: "var(--color-surface)", color: "var(--color-text-muted)", border: "1px solid var(--color-border)" }}>Do not submit</button>
                <button type="button" onClick={() => handleFinalConfirmation(true)} className="rounded-lg px-4 py-2 text-xs font-semibold" style={{ background: "#22c55e", color: "#fff" }}>Confirm external submission</button>
              </div>
            </div>
          </Card.Body>
        </Card>
      )}

      {/* Result Display */}
      {(TERMINAL_STATUSES.has(status) || refNumber || error) && !isActive && (
        <Card>
          <Card.Header>
            <h3 className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
              Filing Result
            </h3>
          </Card.Header>
          <Card.Body>
            {refNumber && (
              <div className="p-3 rounded-lg mb-3" style={{ backgroundColor: "rgba(34, 197, 94, 0.1)", border: "1px solid rgba(34, 197, 94, 0.3)" }}>
                <p className="text-xs font-medium" style={{ color: "rgb(34, 197, 94)" }}>Reference Number</p>
                <p className="font-mono font-bold text-lg" style={{ color: "rgb(34, 197, 94)" }}>{refNumber}</p>
              </div>
            )}

            {nextActions.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-medium mb-2" style={{ color: "var(--color-text-muted)" }}>Next actions:</p>
                <ul className="list-disc space-y-1 pl-4">
                  {nextActions.map((action) => <li key={action} className="text-xs" style={{ color: "var(--color-text-muted)" }}>{action}</li>)}
                </ul>
              </div>
            )}

            {message && !error && (
              <p className="text-sm mb-3" style={{ color: "var(--color-text)" }}>{message}</p>
            )}

            {error && (
              <div className="p-3 rounded-lg mb-3" style={{ backgroundColor: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)" }}>
                <p className="text-sm" style={{ color: "rgb(239, 68, 68)" }}>{error}</p>
              </div>
            )}

            {steps.length > 0 && (
              <div>
                <p className="text-xs font-medium mb-2" style={{ color: "var(--color-text-muted)" }}>Steps Completed:</p>
                <ul className="space-y-1">
                  {steps.map((step, i) => (
                    <li key={i} className="text-xs flex items-center gap-2" style={{ color: "var(--color-text-muted)" }}>
                      <span style={{ color: "rgb(34, 197, 94)" }}>{"\u2713"}</span>
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card.Body>
        </Card>
      )}
    </div>
  );
}

function InputField({
  label, value, onChange, placeholder, disabled,
}: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string; disabled?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>
        {label}
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full px-3 py-2 rounded-lg text-sm"
        style={{
          backgroundColor: "var(--color-surface)",
          color: "var(--color-text)",
          border: "1px solid var(--color-border)",
          opacity: disabled ? 0.6 : 1,
        }}
      />
    </div>
  );
}
