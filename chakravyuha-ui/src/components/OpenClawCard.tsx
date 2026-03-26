"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Card } from "@/components/Card";
import {
  startOpenClawFiling,
  pollOpenClawStatus,
  submitOpenClawOTP,
} from "@/services/api";

const PORTALS = [
  { id: "cpgrams", label: "CPGRAMS (Public Grievance)" },
  { id: "consumer_helpline", label: "National Consumer Helpline" },
  { id: "ecourts", label: "eCourts eFiling" },
  { id: "mparivahan", label: "mParivahan / Sarathi" },
];

const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
  "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
  "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
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
}

const INITIAL_FORM: FormData = {
  name: "", mobile: "", email: "", state: "", district: "",
  pin_code: "", gender: "", father_name: "", dob: "", description: "",
  rto_office: "", blood_group: "", identity_type: "", identity_number: "", role: "",
};

// Terminal statuses that stop polling
const TERMINAL_STATUSES = new Set(["submitted", "success", "error", "not_found"]);

export function OpenClawCard() {
  const [portalId, setPortalId] = useState("");
  const [form, setForm] = useState<FormData>(INITIAL_FORM);
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
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const updateField = useCallback((field: keyof FormData, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setValidationErrors([]); // clear on edit
  }, []);

  // ── Validation ────────────────────────────────────────────────────────

  const validate = useCallback((): string[] => {
    const errors: string[] = [];
    if (!portalId) errors.push("Select a portal");
    if (!form.name.trim()) errors.push("Name is required");
    if (!form.mobile.trim() || !/^\d{10}$/.test(form.mobile.trim()))
      errors.push("Valid 10-digit mobile required");
    if (!form.email.trim() || !form.email.includes("@"))
      errors.push("Valid email required");
    if (!form.state) errors.push("State is required");
    if (!form.district.trim()) errors.push("District is required");
    if (!form.pin_code.trim() || !/^\d{6}$/.test(form.pin_code.trim()))
      errors.push("Valid 6-digit PIN required");

    if (portalId === "mparivahan") {
      if (!form.father_name.trim()) errors.push("Father's name required");
      if (!form.rto_office.trim()) errors.push("RTO office required");
      if (!form.blood_group) errors.push("Blood group required");
      if (!form.dob.trim()) errors.push("Date of birth required");
      if (!form.gender) errors.push("Gender required");
    }
    if (portalId === "ecourts") {
      if (!form.role) errors.push("Role required");
      if (!form.identity_type) errors.push("Identity type required");
      if (!form.identity_number.trim()) errors.push("Identity number required");
    }
    if (!form.description.trim()) errors.push("Description required");

    return errors;
  }, [portalId, form]);

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

        if (res.reference_number) setRefNumber(res.reference_number);
        if (res.error) setError(res.error);

        // Show OTP input when backend is waiting
        if (res.status === "waiting_otp") {
          setShowOtp(true);
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

  // ── Submit ────────────────────────────────────────────────────────────

  const handleSubmit = useCallback(async () => {
    const errors = validate();
    if (errors.length > 0) {
      setValidationErrors(errors);
      return;
    }

    setLoading(true);
    setError(null);
    setMessage("");
    setSteps([]);
    setRefNumber(null);
    setShowOtp(false);
    setOtp("");
    setCurrentStep("");
    setStatus("starting");
    setValidationErrors([]);

    try {
      const response = await startOpenClawFiling({
        portal_id: portalId,
        user_data: {
          ...form,
          subject: form.description.slice(0, 100),
          address: `${form.district}, ${form.state} - ${form.pin_code}`,
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
  }, [portalId, form, validate, startPolling]);

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
                OpenClaw — Autonomous Form Filing
              </h2>
              <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                AI agent files government forms, solves CAPTCHAs, pauses for OTP
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
              onChange={(e) => { setPortalId(e.target.value); setValidationErrors([]); }}
              disabled={isActive}
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                backgroundColor: "var(--color-surface)",
                color: "var(--color-text)",
                border: "1px solid var(--color-border)",
              }}
            >
              <option value="">-- Choose a portal --</option>
              {PORTALS.map((p) => (
                <option key={p.id} value={p.id}>{p.label}</option>
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

          {/* Submit Button */}
          {portalId && (
            <button
              onClick={handleSubmit}
              disabled={isActive}
              className="w-full py-3 rounded-xl font-bold text-sm transition-all"
              style={{
                background: isActive ? "var(--color-surface)" : "linear-gradient(135deg, var(--color-accent), var(--color-accent-hover))",
                color: isActive ? "var(--color-text-muted)" : "#fff",
                opacity: isActive ? 0.6 : 1,
              }}
            >
              {isActive ? "Filing in progress..." : "Start Autonomous Filing"}
            </button>
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
