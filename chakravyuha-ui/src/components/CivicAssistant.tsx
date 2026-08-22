"use client";

import { useCallback, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card } from "@/components/Card";
import { StepWizard } from "@/components/StepWizard";
import {
  draftRTI,
  downloadRTI,
  getRTIGuide,
  guidedSchemeCheck,
  identifyRTIDepartment,
  prepareCPGRAMS,
  queryLegalDomain,
  searchGovernmentSchemes,
  type CivicConfidence,
  type CivicProvenance,
  type CPGRAMSDraft,
  type CPGRAMSPrepareResponse,
  type LegalDomainQueryResponse,
  type RTIDepartmentResponse,
  type RTIDraftRequest,
  type RTIDraftResponse,
  type RTIGuideResponse,
  type SchemeCondition,
  type SchemeEligibilityResult,
  type SchemeProfile,
  type SchemeQuestion,
  type SchemeSummary,
} from "@/services/api";

export type CivicJourney = "rti" | "schemes" | "cpgrams" | "rights";

export interface CivicFilingHandoff {
  portalId: "cpgrams";
  userData: Record<string, string>;
}

interface CivicAssistantProps {
  initialJourney?: CivicJourney;
  onOpenClaw?: (handoff: CivicFilingHandoff) => void;
}

const JOURNEYS: Array<{
  id: CivicJourney;
  icon: string;
  label: string;
  description: string;
}> = [
  {
    id: "rti",
    icon: "📄",
    label: "RTI Assistant",
    description: "Turn an issue into a focused request for government records.",
  },
  {
    id: "schemes",
    icon: "🏛️",
    label: "Scheme Eligibility",
    description: "Check verified eligibility rules and see what is still unknown.",
  },
  {
    id: "cpgrams",
    icon: "📮",
    label: "CPGRAMS",
    description: "Prepare and review a public grievance before any portal action.",
  },
  {
    id: "rights",
    icon: "🧭",
    label: "Rights Navigator",
    description: "Find jurisdiction-aware consumer, tenant, and workplace guidance.",
  },
];

const INPUT_STYLE: CSSProperties = {
  background: "rgba(0,0,0,0.2)",
  color: "var(--color-text)",
  border: "1px solid var(--color-border)",
};

const PRIMARY_BUTTON_STYLE: CSSProperties = {
  background: "var(--color-primary-dim)",
  color: "var(--color-primary)",
  border: "1px solid var(--color-primary)",
};

const SECONDARY_BUTTON_STYLE: CSSProperties = {
  background: "var(--color-surface)",
  color: "var(--color-text-muted)",
  border: "1px solid var(--color-border)",
};

const INDIAN_STATES_AND_UTS = [
  "Andaman and Nicobar Islands",
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chandigarh",
  "Chhattisgarh",
  "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jammu and Kashmir",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Ladakh",
  "Lakshadweep",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Puducherry",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
];

function FieldLabel({ children, optional = false }: { children: ReactNode; optional?: boolean }) {
  return (
    <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>
      {children}
      {optional && <span className="ml-1 normal-case font-normal" style={{ color: "var(--color-text-faint)" }}>(optional)</span>}
    </label>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  optional,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  optional?: boolean;
  type?: "text" | "number" | "date" | "email" | "tel";
}) {
  return (
    <div>
      <FieldLabel optional={optional}>{label}</FieldLabel>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl px-3 py-2.5 text-sm outline-none transition-colors focus:border-violet-400"
        style={INPUT_STYLE}
      />
    </div>
  );
}

function StateField({ value, onChange, optional = true }: { value: string; onChange: (value: string) => void; optional?: boolean }) {
  return (
    <div>
      <FieldLabel optional={optional}>State / Union Territory</FieldLabel>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl px-3 py-2.5 text-sm outline-none"
        style={INPUT_STYLE}
      >
        <option value="">Select only if known</option>
        {INDIAN_STATES_AND_UTS.map((state) => (
          <option key={state} value={state}>{state}</option>
        ))}
      </select>
    </div>
  );
}

function ActionButton({
  children,
  onClick,
  disabled,
  secondary = false,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  secondary?: boolean;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="rounded-xl px-4 py-2.5 text-xs font-semibold transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
      style={secondary ? SECONDARY_BUTTON_STYLE : PRIMARY_BUTTON_STYLE}
      whileHover={disabled ? undefined : { scale: 1.01 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
    >
      {children}
    </motion.button>
  );
}

function BusyLabel({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-t-transparent" style={{ borderColor: "var(--color-primary)", borderTopColor: "transparent" }} />
      {label}
    </span>
  );
}

function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warning" | "error" | "success" }) {
  const colors = {
    info: { color: "var(--color-primary)", background: "var(--color-primary-dim)", border: "rgba(167,139,250,0.3)" },
    warning: { color: "#f59e0b", background: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.3)" },
    error: { color: "#ef4444", background: "rgba(239,68,68,0.1)", border: "rgba(239,68,68,0.3)" },
    success: { color: "#22c55e", background: "rgba(34,197,94,0.1)", border: "rgba(34,197,94,0.3)" },
  }[tone];
  return (
    <div className="rounded-xl px-3 py-2.5 text-xs leading-relaxed" style={{ color: colors.color, background: colors.background, border: `1px solid ${colors.border}` }}>
      {children}
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence?: CivicConfidence | number | null }) {
  if (confidence === undefined || confidence === null || confidence === "") return null;
  const normalized = typeof confidence === "number"
    ? confidence >= 0.75 ? "high" : confidence >= 0.45 ? "medium" : "low"
    : String(confidence).toLowerCase().replace(/\s+/g, "_");
  const config = normalized === "high"
    ? { label: "High confidence", color: "#22c55e", bg: "rgba(34,197,94,0.12)" }
    : normalized === "medium"
      ? { label: "Medium confidence", color: "#f59e0b", bg: "rgba(245,158,11,0.12)" }
      : normalized === "requires_jurisdiction"
        ? { label: "Needs jurisdiction", color: "#f97316", bg: "rgba(249,115,22,0.12)" }
        : normalized === "requires_verification"
          ? { label: "Requires verification", color: "#f97316", bg: "rgba(249,115,22,0.12)" }
          : { label: "Low confidence", color: "#ef4444", bg: "rgba(239,68,68,0.12)" };
  return (
    <span className="inline-flex rounded-full px-2.5 py-1 text-[10px] font-semibold" style={{ color: config.color, background: config.bg, border: `1px solid ${config.color}55` }}>
      {config.label}
    </span>
  );
}

function safeExternalUrl(value?: string | null): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.href : null;
  } catch {
    return null;
  }
}

function metadataText(value: unknown): string {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (value && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .filter(([, item]) => item !== null && item !== undefined && item !== "")
      .map(([key, item]) => `${key.replace(/_/g, " ")}: ${String(item)}`)
      .join(", ");
  }
  return "";
}

function ProvenanceBlock({ provenance, sources }: { provenance?: CivicProvenance; sources?: CivicProvenance[] }) {
  const entries = sources && sources.length > 0 ? sources : provenance ? [provenance] : [];
  const visible = entries.filter((entry) => entry.source || entry.source_url || entry.last_verified || entry.status || entry.jurisdiction);
  if (visible.length === 0) return null;
  return (
    <div className="space-y-1.5 rounded-xl p-3 text-[10px]" style={{ background: "rgba(0,0,0,0.16)", border: "1px solid var(--color-border)" }}>
      <p className="font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>Source and verification</p>
      {visible.map((entry, index) => {
        const href = safeExternalUrl(entry.source_url);
        return (
          <div key={`${entry.source ?? "source"}-${index}`} className="flex flex-wrap gap-x-2 gap-y-1" style={{ color: "var(--color-text-muted)" }}>
            {href ? (
              <a href={href} target="_blank" rel="noreferrer" className="underline" style={{ color: "var(--color-primary)" }}>
                {entry.source || "Official source"}
              </a>
            ) : entry.source ? <span>{entry.source}</span> : null}
            {entry.jurisdiction && <span>Jurisdiction: {metadataText(entry.jurisdiction)}</span>}
            {entry.last_verified && <span>Verified: {entry.last_verified}</span>}
            {entry.status && <span>Status: {entry.status.replace(/_/g, " ")}</span>}
          </div>
        );
      })}
    </div>
  );
}

function MissingInformation({ items }: { items?: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <Notice tone="warning">
      <p className="font-semibold">More information would improve this result:</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-4">
        {items.map((item) => <li key={item}>{item.replace(/_/g, " ")}</li>)}
      </ul>
    </Notice>
  );
}

function JourneyWizard({ current, labels, onStep }: { current: number; labels: string[]; onStep: (step: number) => void }) {
  return (
    <StepWizard currentStep={current} totalSteps={labels.length} setStep={(step) => step <= current && onStep(step)}>
      {labels.map((label, index) => <StepWizard.Step key={label} stepNumber={index + 1} label={label} />)}
    </StepWizard>
  );
}

function SectionTitle({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--color-secondary)" }}>{eyebrow}</p>
      <h3 className="mt-1 text-base font-bold" style={{ color: "var(--color-text)" }}>{title}</h3>
      <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--color-text-muted)" }}>{description}</p>
    </div>
  );
}

function RTIAssistant() {
  const [step, setStep] = useState(1);
  const [issue, setIssue] = useState("");
  const [stateName, setStateName] = useState("");
  const [district, setDistrict] = useState("");
  const [city, setCity] = useState("");
  const [locality, setLocality] = useState("");
  const [authorityHint, setAuthorityHint] = useState("");
  const [roadType, setRoadType] = useState("");
  const [dateRange, setDateRange] = useState("");
  const [applicantName, setApplicantName] = useState("");
  const [applicantAddress, setApplicantAddress] = useState("");
  const [applicantContact, setApplicantContact] = useState("");
  const [isIndianCitizen, setIsIndianCitizen] = useState(false);
  const [routing, setRouting] = useState<RTIDepartmentResponse | null>(null);
  const [draft, setDraft] = useState<RTIDraftResponse | null>(null);
  const [guide, setGuide] = useState<RTIGuideResponse | null>(null);
  const [requests, setRequests] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [downloadMessage, setDownloadMessage] = useState("");

  const baseRequest = useMemo(() => ({
    issue: issue.trim(),
    state: stateName || undefined,
    district: district.trim() || undefined,
    city: city.trim() || undefined,
    locality: locality.trim() || undefined,
    authority_hint: authorityHint.trim() || undefined,
    road_type: roadType.trim() || undefined,
    date_range: dateRange.trim() || undefined,
  }), [issue, stateName, district, city, locality, authorityHint, roadType, dateRange]);

  const buildDraftRequest = useCallback((informationRequests?: string[]): RTIDraftRequest => ({
    ...baseRequest,
    information_requests: informationRequests,
    applicant_name: applicantName.trim() || undefined,
    applicant_address: applicantAddress.trim() || undefined,
    applicant_contact: applicantContact.trim() || undefined,
    is_indian_citizen: isIndianCitizen,
  }), [baseRequest, applicantName, applicantAddress, applicantContact, isIndianCitizen]);

  const identify = useCallback(async () => {
    if (issue.trim().length < 10) {
      setError("Please describe the issue in at least a short sentence.");
      return;
    }
    setBusy(true);
    setError("");
    setDownloadMessage("");
    try {
      const response = await identifyRTIDepartment(baseRequest);
      setRouting(response);
      setDraft(null);
      setRequests([]);
      setStep(2);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not identify an authority.");
    } finally {
      setBusy(false);
    }
  }, [issue, baseRequest]);

  const proposeRequests = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      const response = await draftRTI(buildDraftRequest());
      setDraft(response);
      setRouting(response.routing ?? routing);
      setRequests(response.information_requests ?? []);
      setStep(response.information_requests?.length ? 3 : 2);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not prepare information requests.");
    } finally {
      setBusy(false);
    }
  }, [buildDraftRequest, routing]);

  const generateDraft = useCallback(async () => {
    const cleaned = requests.map((request) => request.trim()).filter(Boolean);
    if (cleaned.length === 0) {
      setError("Keep at least one request for identifiable records or information.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const [draftResponse, guideResponse] = await Promise.all([
        draftRTI(buildDraftRequest(cleaned)),
        getRTIGuide(stateName || undefined, authorityHint.trim() || undefined).catch(() => null),
      ]);
      setDraft(draftResponse);
      setRequests(draftResponse.information_requests?.length ? draftResponse.information_requests : cleaned);
      setGuide(guideResponse);
      setStep(4);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not generate the RTI draft.");
    } finally {
      setBusy(false);
    }
  }, [requests, buildDraftRequest, stateName, authorityHint]);

  const documentText = draft?.document_text ?? draft?.content ?? draft?.draft_text ?? draft?.draft ?? "";

  const download = useCallback(async () => {
    if (!documentText) return;
    setBusy(true);
    setError("");
    setDownloadMessage("");
    try {
      const { blob, filename } = await downloadRTI(buildDraftRequest(requests.filter((request) => request.trim())));
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Download failed.");
    } finally {
      setBusy(false);
    }
  }, [documentText, buildDraftRequest, requests, draft]);

  const guidance = draft?.filing_guidance;
  const guidanceSteps = Array.isArray(guidance)
    ? guidance
    : guidance && "steps" in guidance && Array.isArray(guidance.steps)
      ? guidance.steps
      : guide?.steps ?? (Array.isArray(guide?.guide) ? guide.guide : []);
  const nextStep = guidance && !Array.isArray(guidance) && "next_step" in guidance && typeof guidance.next_step === "string"
    ? guidance.next_step
    : undefined;
  const warnings = guidance && !Array.isArray(guidance) && "warnings" in guidance && Array.isArray(guidance.warnings)
    ? guidance.warnings
    : [];
  const guidanceSources = guidance && !Array.isArray(guidance) && "sources" in guidance && Array.isArray(guidance.sources)
    ? guidance.sources
    : [];

  return (
    <div className="space-y-4">
      <JourneyWizard current={step} labels={["Describe", "Authority", "Requests", "Draft & file"]} onStep={setStep} />
      {error && <Notice tone="error">{error}</Notice>}

      {step === 1 && (
        <Card>
          <Card.Body>
            <div className="space-y-4">
              <SectionTitle eyebrow="Step 1" title="What records do you need?" description="Describe the underlying issue in ordinary language. The assistant will turn it into requests for records—not a grievance accusation." />
              <div>
                <FieldLabel>Describe the issue</FieldLabel>
                <textarea value={issue} onChange={(event) => setIssue(event.target.value)} rows={5} placeholder="Example: The road in my locality has not been repaired for two years. I want to know what work was sanctioned and how funds were used." className="w-full resize-y rounded-xl px-3 py-2.5 text-sm outline-none" style={INPUT_STYLE} />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <StateField value={stateName} onChange={setStateName} />
                <TextField label="District" value={district} onChange={setDistrict} optional placeholder="If known" />
                <TextField label="City / local body" value={city} onChange={setCity} optional placeholder="Municipality, city, or panchayat" />
                <TextField label="Locality" value={locality} onChange={setLocality} optional placeholder="Ward, village, street, landmark" />
                <TextField label="Authority hint" value={authorityHint} onChange={setAuthorityHint} optional placeholder="Department or office, only if known" />
                <TextField label="Relevant period" value={dateRange} onChange={setDateRange} optional placeholder="Example: April 2024 to March 2026" />
                <TextField label="Road / asset type" value={roadType} onChange={setRoadType} optional placeholder="Only when relevant" />
              </div>
              <ActionButton onClick={identify} disabled={busy || issue.trim().length < 10}>
                {busy ? <BusyLabel label="Checking jurisdiction..." /> : "Identify likely authority"}
              </ActionButton>
            </div>
          </Card.Body>
        </Card>
      )}

      {step === 2 && routing && (
        <div className="space-y-3">
          <Card>
            <Card.Body>
              <div className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <SectionTitle eyebrow={routing.domain || "RTI routing"} title={routing.likely_authority || "Authority not yet identified"} description={routing.reason || "More jurisdiction information is required."} />
                  <ConfidenceBadge confidence={routing.confidence} />
                </div>
                {routing.authority_type && <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Authority type: {routing.authority_type}</p>}
                <MissingInformation items={routing.missing_information} />
                <ProvenanceBlock provenance={routing} />
              </div>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body>
              <div className="space-y-3">
                <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Add or correct jurisdiction details, then re-check. Do not select an office merely to force a confident result.</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <StateField value={stateName} onChange={setStateName} />
                  <TextField label="District" value={district} onChange={setDistrict} optional />
                  <TextField label="City / local body" value={city} onChange={setCity} optional />
                  <TextField label="Locality" value={locality} onChange={setLocality} optional />
                  <TextField label="Authority hint" value={authorityHint} onChange={setAuthorityHint} optional />
                  <TextField label="Road / asset type" value={roadType} onChange={setRoadType} optional />
                </div>
                <div className="flex flex-wrap gap-2">
                  <ActionButton onClick={identify} disabled={busy}>{busy ? <BusyLabel label="Re-checking..." /> : "Re-check authority"}</ActionButton>
                  <ActionButton onClick={proposeRequests} disabled={busy || !routing.likely_authority} secondary>
                    {busy ? <BusyLabel label="Preparing..." /> : "Prepare information requests"}
                  </ActionButton>
                </div>
              </div>
            </Card.Body>
          </Card>
        </div>
      )}

      {step === 3 && (
        <Card>
          <Card.Body>
            <div className="space-y-4">
              <SectionTitle eyebrow="Review" title="Edit the information requests" description="Ask for identifiable records, orders, inspections, expenditure, or status information. Remove anything that reads like an accusation or demand for an explanation." />
              <MissingInformation items={draft?.missing_information} />
              <div className="space-y-2">
                {requests.map((request, index) => (
                  <div key={index} className="flex items-start gap-2">
                    <span className="mt-2.5 text-xs font-semibold" style={{ color: "var(--color-primary)" }}>{index + 1}.</span>
                    <textarea value={request} onChange={(event) => setRequests((current) => current.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} rows={3} className="flex-1 resize-y rounded-xl px-3 py-2 text-xs outline-none" style={INPUT_STYLE} />
                    <button type="button" onClick={() => setRequests((current) => current.filter((_, itemIndex) => itemIndex !== index))} className="mt-1 rounded-lg px-2 py-1 text-xs" style={SECONDARY_BUTTON_STYLE} aria-label={`Remove request ${index + 1}`}>×</button>
                  </div>
                ))}
                <ActionButton onClick={() => setRequests((current) => [...current, ""])} secondary>Add another request</ActionButton>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <TextField label="Applicant name" value={applicantName} onChange={setApplicantName} />
                <TextField label="Contact" value={applicantContact} onChange={setApplicantContact} optional placeholder="Only if you want it in the draft" />
                <div className="sm:col-span-2">
                  <TextField label="Applicant postal address" value={applicantAddress} onChange={setApplicantAddress} />
                </div>
              </div>
              <label className="flex cursor-pointer items-start gap-2 rounded-xl p-3 text-xs" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", color: "var(--color-text-muted)" }}>
                <input type="checkbox" checked={isIndianCitizen} onChange={(event) => setIsIndianCitizen(event.target.checked)} className="mt-0.5" />
                <span>I confirm that the applicant is a citizen of India. This confirmation is required to prepare a download-ready RTI application.</span>
              </label>
              <div className="flex flex-wrap gap-2">
                <ActionButton onClick={() => setStep(2)} secondary>Back to authority</ActionButton>
                <ActionButton onClick={generateDraft} disabled={busy || !applicantName.trim() || !applicantAddress.trim() || !isIndianCitizen}>{busy ? <BusyLabel label="Generating..." /> : "Generate reviewed draft"}</ActionButton>
              </div>
            </div>
          </Card.Body>
        </Card>
      )}

      {step === 4 && draft && (
        <div className="space-y-3">
          <Card>
            <Card.Header>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>RTI application preview</h3>
                <ConfidenceBadge confidence={draft.routing?.confidence ?? draft.confidence ?? routing?.confidence} />
              </div>
            </Card.Header>
            <Card.Body>
              <div className="space-y-3">
                <MissingInformation items={draft.missing_information} />
                {documentText ? (
                  <pre className="max-h-[520px] overflow-y-auto whitespace-pre-wrap rounded-xl p-4 text-xs leading-relaxed" style={{ ...INPUT_STYLE, background: "rgba(0,0,0,0.25)" }}>{documentText}</pre>
                ) : (
                  <Notice tone="warning">A document was not generated. Complete the missing information and try again.</Notice>
                )}
                <div className="flex flex-wrap gap-2">
                  <ActionButton onClick={() => setStep(3)} secondary>Edit requests</ActionButton>
                  <ActionButton onClick={download} disabled={busy || !documentText || draft.status !== "ready_for_review"}>{busy ? <BusyLabel label="Preparing download..." /> : "Download text document"}</ActionButton>
                </div>
                {downloadMessage && <Notice tone="info">{downloadMessage}</Notice>}
              </div>
            </Card.Body>
          </Card>
          {(guidanceSteps.length > 0 || nextStep || warnings.length > 0) && (
            <Card>
              <Card.Body>
                <div className="space-y-3 text-xs">
                  <SectionTitle eyebrow="Next practical step" title={nextStep || "Review the filing pathway"} description="Portal availability, fees, and procedures can change. Follow only the sourced guidance returned for this request." />
                  {guidanceSteps.length > 0 && <ol className="list-decimal space-y-1 pl-5" style={{ color: "var(--color-text-muted)" }}>{guidanceSteps.map((item) => <li key={item}>{item}</li>)}</ol>}
                  {warnings.length > 0 && <Notice tone="warning"><ul className="list-disc pl-4">{warnings.map((item) => <li key={item}>{item}</li>)}</ul></Notice>}
                  <ProvenanceBlock sources={guidanceSources} provenance={draft} />
                </div>
              </Card.Body>
            </Card>
          )}
          {draft.disclaimer && <p className="px-2 text-center text-[10px]" style={{ color: "var(--color-text-faint)" }}>{draft.disclaimer}</p>}
        </div>
      )}
    </div>
  );
}

function normalizeSchemeResponse(response: unknown): { results: SchemeEligibilityResult[]; questions: SchemeQuestion[] } {
  if (Array.isArray(response)) return { results: response as SchemeEligibilityResult[], questions: [] };
  if (!response || typeof response !== "object") return { results: [], questions: [] };
  const value = response as Record<string, unknown>;
  const candidateResults = value.results ?? value.schemes ?? value.candidates;
  const results = Array.isArray(candidateResults) ? candidateResults as SchemeEligibilityResult[] : [];
  const candidateQuestions = value.next_questions ?? value.questions;
  const questions = Array.isArray(candidateQuestions) ? candidateQuestions as SchemeQuestion[] : [];
  return { results, questions };
}

function conditionText(condition: SchemeCondition | string): string {
  return typeof condition === "string" ? condition : condition.explanation || condition.field || "Condition evaluated";
}

function SchemeResultCard({ result }: { result: SchemeEligibilityResult }) {
  const status = (result.status || "not enough information").toLowerCase();
  const tone = status.includes("eligible") && !status.includes("not")
    ? "success"
    : status.includes("not eligible") || status.includes("disqual")
      ? "error"
      : "warning";
  const applicationSteps = Array.isArray(result.application_process)
    ? result.application_process
    : result.application_process ? [result.application_process] : [];
  return (
    <Card>
      <Card.Body>
        <div className="space-y-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h4 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>{result.scheme_name}</h4>
              {result.description && <p className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>{result.description}</p>}
            </div>
            <Notice tone={tone}>{result.status}</Notice>
          </div>
          {result.why && <p className="text-xs leading-relaxed" style={{ color: "var(--color-text)" }}>{result.why}</p>}
          <div className="grid gap-3 sm:grid-cols-3">
            <ConditionList title="Matched" items={result.matched_conditions} color="#22c55e" />
            <ConditionList title="Still unknown" items={result.unknown_conditions} color="#f59e0b" />
            <ConditionList title="Potential disqualifiers" items={result.potential_disqualifiers} color="#ef4444" />
          </div>
          {result.required_documents?.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>Documents to prepare</p>
              <ul className="mt-1 grid gap-1 sm:grid-cols-2" style={{ color: "var(--color-text-muted)" }}>{result.required_documents.map((item) => <li key={item} className="text-xs">☐ {item}</li>)}</ul>
            </div>
          )}
          {applicationSteps.length > 0 && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>Application process / next action</p>
              <ol className="mt-1 list-decimal space-y-1 pl-5 text-xs" style={{ color: "var(--color-text-muted)" }}>{applicationSteps.map((item) => <li key={item}>{item}</li>)}</ol>
            </div>
          )}
          {safeExternalUrl(result.official_portal_url) && (
            <a href={safeExternalUrl(result.official_portal_url) ?? undefined} target="_blank" rel="noreferrer" className="inline-flex rounded-xl px-3 py-2 text-xs font-semibold" style={PRIMARY_BUTTON_STYLE}>Open official portal</a>
          )}
          {result.evaluation_warnings && result.evaluation_warnings.length > 0 && <Notice tone="warning"><ul className="list-disc pl-4">{result.evaluation_warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></Notice>}
          {result.verification_note && <p className="text-[10px]" style={{ color: "var(--color-text-faint)" }}>{result.verification_note}</p>}
          <ProvenanceBlock provenance={result.provenance ?? result} />
          {result.disclaimer && <p className="text-[10px]" style={{ color: "var(--color-text-faint)" }}>{result.disclaimer}</p>}
        </div>
      </Card.Body>
    </Card>
  );
}

function ConditionList({ title, items, color }: { title: string; items?: Array<SchemeCondition | string>; color: string }) {
  return (
    <div className="rounded-xl p-3" style={{ background: `${color}12`, border: `1px solid ${color}33` }}>
      <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color }}>{title}</p>
      {items && items.length > 0 ? (
        <ul className="mt-1 list-disc space-y-1 pl-4 text-[11px]" style={{ color: "var(--color-text-muted)" }}>{items.map((item, index) => <li key={`${conditionText(item)}-${index}`}>{conditionText(item)}</li>)}</ul>
      ) : <p className="mt-1 text-[11px]" style={{ color: "var(--color-text-faint)" }}>None reported</p>}
    </div>
  );
}

function SchemeAssistant() {
  const [step, setStep] = useState(1);
  const [stateName, setStateName] = useState("");
  const [age, setAge] = useState("");
  const [occupation, setOccupation] = useState("");
  const [dynamicAnswers, setDynamicAnswers] = useState<Record<string, string>>({});
  const [questions, setQuestions] = useState<SchemeQuestion[]>([]);
  const [results, setResults] = useState<SchemeEligibilityResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<SchemeSummary[]>([]);
  const [searching, setSearching] = useState(false);

  const profile = useMemo<SchemeProfile>(() => {
    const value: SchemeProfile = {};
    if (stateName) value.state = stateName;
    if (age) value.age = Number(age);
    if (occupation.trim()) value.occupation = occupation.trim();
    for (const [field, answer] of Object.entries(dynamicAnswers)) {
      if (!answer.trim()) continue;
      if (["age", "monthly_income", "annual_income", "household_income", "cultivable_land"].includes(field)) {
        const numeric = Number(answer);
        value[field] = Number.isFinite(numeric) ? numeric : answer;
      } else if (answer === "true" || answer === "false") {
        value[field] = answer === "true";
      } else {
        value[field] = answer;
      }
    }
    return value;
  }, [stateName, age, occupation, dynamicAnswers]);

  const check = useCallback(async () => {
    if (!stateName && !age && !occupation.trim()) {
      setError("Provide at least one profile detail to start a targeted check.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await guidedSchemeCheck({ profile });
      const normalized = normalizeSchemeResponse(response);
      setQuestions(normalized.questions);
      setResults(normalized.results);
      setStep(normalized.questions.length > 0 ? 2 : 3);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not check scheme eligibility.");
    } finally {
      setBusy(false);
    }
  }, [profile, stateName, age, occupation]);

  const runSearch = useCallback(async () => {
    if (!search.trim()) return;
    setSearching(true);
    setError("");
    try {
      const response = await searchGovernmentSchemes(search.trim());
      setSearchResults(Array.isArray(response) ? response : []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Scheme search failed.");
    } finally {
      setSearching(false);
    }
  }, [search]);

  return (
    <div className="space-y-4">
      <JourneyWizard current={step} labels={["Basic profile", "Targeted questions", "Explain results"]} onStep={setStep} />
      {error && <Notice tone="error">{error}</Notice>}
      {step === 1 && (
        <div className="space-y-3">
          <Card>
            <Card.Body>
              <div className="space-y-4">
                <SectionTitle eyebrow="Rule-driven check" title="Start with only a few details" description="The service will ask additional questions only when a verified scheme rule needs them. It does not calculate a made-up eligibility percentage." />
                <div className="grid gap-3 sm:grid-cols-3">
                  <StateField value={stateName} onChange={setStateName} />
                  <TextField label="Age" value={age} onChange={setAge} optional type="number" placeholder="In completed years" />
                  <TextField label="Occupation" value={occupation} onChange={setOccupation} optional placeholder="Example: farmer, student, worker" />
                </div>
                <ActionButton onClick={check} disabled={busy}>{busy ? <BusyLabel label="Checking rules..." /> : "Find relevant schemes"}</ActionButton>
              </div>
            </Card.Body>
          </Card>
          <Card>
            <Card.Body>
              <div className="space-y-3">
                <SectionTitle eyebrow="Optional discovery" title="Search the verified scheme catalogue" description="Search shows available records; eligibility is evaluated separately against the structured rules." />
                <div className="flex gap-2">
                  <input value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === "Enter" && runSearch()} placeholder="Search by scheme name or purpose" className="min-w-0 flex-1 rounded-xl px-3 py-2.5 text-sm outline-none" style={INPUT_STYLE} />
                  <ActionButton onClick={runSearch} disabled={searching || !search.trim()}>{searching ? <BusyLabel label="Searching..." /> : "Search"}</ActionButton>
                </div>
                {searchResults.length > 0 && <div className="grid gap-2 sm:grid-cols-2">{searchResults.map((scheme) => <SchemeSummaryCard key={scheme.id} scheme={scheme} />)}</div>}
              </div>
            </Card.Body>
          </Card>
        </div>
      )}
      {step === 2 && (
        <Card>
          <Card.Body>
            <div className="space-y-4">
              <SectionTitle eyebrow="Only what is needed" title="Answer the remaining rule questions" description="Leave a field blank if you do not know. It will remain an unknown condition rather than being guessed." />
              <div className="grid gap-3 sm:grid-cols-2">
                {questions.map((question) => <SchemeQuestionField key={question.field} question={question} value={dynamicAnswers[question.field] ?? ""} onChange={(value) => setDynamicAnswers((current) => ({ ...current, [question.field]: value }))} />)}
              </div>
              <div className="flex flex-wrap gap-2">
                <ActionButton onClick={() => setStep(1)} secondary>Back</ActionButton>
                <ActionButton onClick={check} disabled={busy}>{busy ? <BusyLabel label="Evaluating..." /> : "Evaluate with these answers"}</ActionButton>
              </div>
            </div>
          </Card.Body>
        </Card>
      )}
      {step === 3 && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <SectionTitle eyebrow="Explainable results" title={results.length ? `${results.length} scheme result${results.length === 1 ? "" : "s"}` : "No evaluated scheme returned"} description="Check the matched, unknown, and potentially disqualifying conditions before relying on a result." />
            <ActionButton onClick={() => setStep(1)} secondary>Change profile</ActionButton>
          </div>
          {results.length > 0 ? results.map((result) => <SchemeResultCard key={result.scheme_id} result={result} />) : <Notice tone="warning">No scheme could be evaluated from the supplied profile and verified catalogue. This is not a finding that no scheme exists.</Notice>}
        </div>
      )}
    </div>
  );
}

function SchemeQuestionField({ question, value, onChange }: { question: SchemeQuestion; value: string; onChange: (value: string) => void }) {
  const options = question.options?.map((option) => typeof option === "string" ? { label: option, value: option } : option) ?? [];
  if (question.input_type === "boolean") {
    return (
      <div>
        <FieldLabel optional={!question.required}>{question.question}</FieldLabel>
        <select value={value} onChange={(event) => onChange(event.target.value)} className="w-full rounded-xl px-3 py-2.5 text-sm" style={INPUT_STYLE}>
          <option value="">I do not know</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      </div>
    );
  }
  if (question.input_type === "select" || options.length > 0) {
    return (
      <div>
        <FieldLabel optional={!question.required}>{question.question}</FieldLabel>
        <select value={value} onChange={(event) => onChange(event.target.value)} className="w-full rounded-xl px-3 py-2.5 text-sm" style={INPUT_STYLE}>
          <option value="">Select or leave unknown</option>
          {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </div>
    );
  }
  return <TextField label={question.question} value={value} onChange={onChange} optional={!question.required} type={question.input_type === "number" ? "number" : "text"} />;
}

function SchemeSummaryCard({ scheme }: { scheme: SchemeSummary }) {
  return (
    <div className="rounded-xl p-3" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
      <p className="text-xs font-semibold" style={{ color: "var(--color-text)" }}>{scheme.name}</p>
      {scheme.description && <p className="mt-1 text-[11px] leading-relaxed" style={{ color: "var(--color-text-muted)" }}>{scheme.description}</p>}
      <ProvenanceBlock provenance={scheme} />
    </div>
  );
}

function cpgramsDraftText(draft: CPGRAMSDraft | CPGRAMSPrepareResponse["draft"]): string {
  if (!draft) return "";
  if ("grievance_text" in draft) return draft.grievance_text;
  return draft.formatted_text;
}

function cpgramsDraftSubject(draft: CPGRAMSPrepareResponse["draft"]): string {
  return draft?.subject ?? "";
}

function CPGRAMSAssistant({ onOpenClaw }: { onOpenClaw?: (handoff: CivicFilingHandoff) => void }) {
  const [step, setStep] = useState(1);
  const [grievance, setGrievance] = useState("");
  const [stateName, setStateName] = useState("");
  const [district, setDistrict] = useState("");
  const [locality, setLocality] = useState("");
  const [organisationHint, setOrganisationHint] = useState("");
  const [incidentDate, setIncidentDate] = useState("");
  const [priorReference, setPriorReference] = useState("");
  const [desiredResolution, setDesiredResolution] = useState("");
  const [accountStatus, setAccountStatus] = useState<"registered" | "not_registered" | "unknown">("unknown");
  const [priorStepsText, setPriorStepsText] = useState("");
  const [evidenceText, setEvidenceText] = useState("");
  const [result, setResult] = useState<CPGRAMSPrepareResponse | null>(null);
  const [subject, setSubject] = useState("");
  const [draftText, setDraftText] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const prepare = useCallback(async () => {
    if (grievance.trim().length < 20) {
      setError("Please describe the grievance with enough detail to classify it.");
      return;
    }
    setBusy(true);
    setError("");
    setConfirmed(false);
    try {
      const response = await prepareCPGRAMS({
        grievance: grievance.trim(),
        state: stateName || undefined,
        district: district.trim() || undefined,
        locality: locality.trim() || undefined,
        organisation_hint: organisationHint.trim() || undefined,
        incident_date: incidentDate || undefined,
        prior_reference: priorReference.trim() || undefined,
        desired_resolution: desiredResolution.trim() || undefined,
        cpgrams_account_status: accountStatus,
        prior_steps: priorStepsText.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
        evidence: evidenceText.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
      });
      setResult(response);
      setSubject(cpgramsDraftSubject(response.draft));
      setDraftText(cpgramsDraftText(response.draft));
      setStep(2);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not prepare the grievance.");
    } finally {
      setBusy(false);
    }
  }, [grievance, stateName, district, locality, organisationHint, incidentDate, priorReference, desiredResolution, accountStatus, priorStepsText, evidenceText]);

  const classification = result?.classification;
  const authorities = result?.authority ? [result.authority] : [];
  const isRedirected = result?.suitability?.is_suitable === false;
  const filingSteps = result?.filing_guide?.steps ?? [];
  const trackingSteps = result?.filing_guide?.tracking ?? [];
  const evidence = result?.draft?.evidence ?? [];
  const canHandoff = Boolean(result?.draft && draftText.trim() && result.missing_information.length === 0 && !isRedirected);

  const handoff = useCallback(() => {
    if (!confirmed || !canHandoff || !onOpenClaw) return;
    const userData = Object.fromEntries(Object.entries({
      description: draftText.trim(),
      subject: subject.trim(),
      state: stateName,
      district: district.trim(),
    }).filter(([, value]) => value));
    onOpenClaw({ portalId: "cpgrams", userData });
  }, [confirmed, canHandoff, onOpenClaw, draftText, subject, stateName, district]);

  return (
    <div className="space-y-4">
      <JourneyWizard current={step} labels={["Describe", "Prepare & review", "Confirm hand-off"]} onStep={setStep} />
      <Notice tone="info">This workspace prepares a draft only. Nothing is sent to CPGRAMS from this screen.</Notice>
      {error && <Notice tone="error">{error}</Notice>}
      {step === 1 && (
        <Card>
          <Card.Body>
            <div className="space-y-4">
              <SectionTitle eyebrow="Public grievance" title="Explain what happened" description="Include the public service involved, what you already tried, and the resolution you want. Do not enter passwords, OTPs, or identity numbers here." />
              <div>
                <FieldLabel>Grievance</FieldLabel>
                <textarea value={grievance} onChange={(event) => setGrievance(event.target.value)} rows={6} placeholder="Describe the service problem, relevant dates, office interactions, and current impact." className="w-full resize-y rounded-xl px-3 py-2.5 text-sm outline-none" style={INPUT_STYLE} />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <StateField value={stateName} onChange={setStateName} />
                <TextField label="District" value={district} onChange={setDistrict} optional />
                <TextField label="Locality" value={locality} onChange={setLocality} optional />
                <TextField label="Incident / last action date" value={incidentDate} onChange={setIncidentDate} optional type="date" />
                <TextField label="Organisation hint" value={organisationHint} onChange={setOrganisationHint} optional placeholder="Ministry, department, or office only if already known" />
                <TextField label="Prior reference" value={priorReference} onChange={setPriorReference} optional />
                <TextField label="Desired resolution" value={desiredResolution} onChange={setDesiredResolution} optional />
                <div>
                  <FieldLabel>CPGRAMS account status</FieldLabel>
                  <select value={accountStatus} onChange={(event) => setAccountStatus(event.target.value as typeof accountStatus)} className="w-full rounded-xl px-3 py-2.5 text-sm" style={INPUT_STYLE}>
                    <option value="unknown">I do not know / have not checked</option>
                    <option value="registered">Registered</option>
                    <option value="not_registered">Not registered</option>
                  </select>
                </div>
                <div className="sm:col-span-2 grid gap-3 sm:grid-cols-2">
                  <div><FieldLabel optional>Steps already taken</FieldLabel><textarea value={priorStepsText} onChange={(event) => setPriorStepsText(event.target.value)} rows={3} placeholder="One step per line" className="w-full resize-y rounded-xl px-3 py-2.5 text-xs" style={INPUT_STYLE} /></div>
                  <div><FieldLabel optional>Evidence available</FieldLabel><textarea value={evidenceText} onChange={(event) => setEvidenceText(event.target.value)} rows={3} placeholder="One item per line" className="w-full resize-y rounded-xl px-3 py-2.5 text-xs" style={INPUT_STYLE} /></div>
                </div>
              </div>
              <ActionButton onClick={prepare} disabled={busy}>{busy ? <BusyLabel label="Preparing review..." /> : "Prepare grievance for review"}</ActionButton>
            </div>
          </Card.Body>
        </Card>
      )}
      {step === 2 && result && (
        <div className="space-y-3">
          <Card>
            <Card.Body>
              <div className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <SectionTitle eyebrow={classification?.domain || "Classification"} title={classification?.label || "Classification unavailable"} description={classification?.reason || "Review the result before proceeding."} />
                  <ConfidenceBadge confidence={classification?.confidence} />
                </div>
                {authorities.map((authority, index) => (
                  <div key={`${authority.candidate}-${index}`} className="rounded-xl p-3" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs font-semibold" style={{ color: "var(--color-text)" }}>{authority.candidate || "Authority requires verification"}</p>
                      <ConfidenceBadge confidence={authority.confidence} />
                    </div>
                    <p className="mt-1 text-[11px]" style={{ color: "var(--color-text-muted)" }}>{authority.reason}</p>
                    {authority.requires_verification && <p className="mt-1 text-[10px]" style={{ color: "#f59e0b" }}>Verify the exact portal category before filing.</p>}
                    <ProvenanceBlock provenance={authority.provenance} />
                  </div>
                ))}
                <MissingInformation items={result.missing_information} />
                {isRedirected && <Notice tone="warning">{result.suitability?.alternative_path || result.suitability?.reason || "This issue may need a different pathway. Do not file it on CPGRAMS without verification."}</Notice>}
              </div>
            </Card.Body>
          </Card>
          {result.draft && (
            <Card>
              <Card.Header><h3 className="text-sm font-bold" style={{ color: "var(--color-text)" }}>Editable grievance draft</h3></Card.Header>
              <Card.Body>
                <div className="space-y-3">
                  <TextField label="Subject" value={subject} onChange={setSubject} />
                  <div>
                    <FieldLabel>Grievance text</FieldLabel>
                    <textarea value={draftText} onChange={(event) => setDraftText(event.target.value)} rows={12} className="w-full resize-y rounded-xl px-3 py-2.5 text-xs leading-relaxed outline-none" style={INPUT_STYLE} />
                  </div>
                  {evidence.length > 0 && <div><p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>Evidence checklist</p><ul className="mt-1 grid gap-1 sm:grid-cols-2">{evidence.map((item) => <li key={item} className="text-xs" style={{ color: "var(--color-text-muted)" }}>☐ {item}</li>)}</ul></div>}
                  <div className="flex flex-wrap gap-2">
                    <ActionButton onClick={() => setStep(1)} secondary>Edit issue details</ActionButton>
                    <ActionButton onClick={() => setStep(3)} disabled={!canHandoff}>Review safe hand-off</ActionButton>
                  </div>
                </div>
              </Card.Body>
            </Card>
          )}
          <ProvenanceBlock sources={result.sources} />
          {result.disclaimer && <p className="px-2 text-center text-[10px]" style={{ color: "var(--color-text-faint)" }}>{result.disclaimer}</p>}
        </div>
      )}
      {step === 3 && result && (
        <div className="space-y-3">
          <Card>
            <Card.Body>
              <div className="space-y-4">
                <SectionTitle eyebrow="Human confirmation" title="Review before opening assisted filing" description="Continuing transfers only this reviewed draft and non-sensitive routing hints to the existing filing screen. It does not submit the grievance." />
                <div className="rounded-xl p-3 text-xs" style={{ background: "rgba(0,0,0,0.2)", border: "1px solid var(--color-border)" }}>
                  <p className="font-semibold" style={{ color: "var(--color-text)" }}>{subject}</p>
                  <p className="mt-2 max-h-44 overflow-y-auto whitespace-pre-wrap" style={{ color: "var(--color-text-muted)" }}>{draftText}</p>
                </div>
                <label className="flex cursor-pointer items-start gap-2 rounded-xl p-3 text-xs" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", color: "var(--color-text-muted)" }}>
                  <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-0.5" />
                  <span>I reviewed the classification, authority uncertainty, subject, and grievance text. I understand the next screen will separately require my details, CAPTCHA/OTP actions, and final submission confirmation.</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  <ActionButton onClick={() => setStep(2)} secondary>Back to draft</ActionButton>
                  <ActionButton onClick={handoff} disabled={!confirmed || !canHandoff || !onOpenClaw}>Continue to CPGRAMS filing screen</ActionButton>
                </div>
              </div>
            </Card.Body>
          </Card>
          {(filingSteps.length > 0 || trackingSteps.length > 0) && (
            <Card>
              <Card.Body>
                <div className="grid gap-4 sm:grid-cols-2">
                  <SimpleSteps title="Filing overview" items={filingSteps} />
                  <SimpleSteps title="Tracking after filing" items={trackingSteps} />
                </div>
              </Card.Body>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function SimpleSteps({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>{title}</p>
      {items.length > 0 ? <ol className="mt-1 list-decimal space-y-1 pl-5 text-xs" style={{ color: "var(--color-text-muted)" }}>{items.map((item) => <li key={item}>{item}</li>)}</ol> : <p className="mt-1 text-xs" style={{ color: "var(--color-text-faint)" }}>Unavailable; verify on the official portal.</p>}
    </div>
  );
}

function RightsNavigator() {
  const [step, setStep] = useState(1);
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState<"consumer" | "tenant" | "labour" | "">("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [result, setResult] = useState<LegalDomainQueryResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = useCallback(async () => {
    if (query.trim().length < 10) {
      setError("Describe the issue in at least a short sentence.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await queryLegalDomain({
        query: query.trim(),
        domain: domain || undefined,
        jurisdiction: jurisdiction || undefined,
      });
      setResult(response);
      setStep(2);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not retrieve civic guidance.");
    } finally {
      setBusy(false);
    }
  }, [query, domain, jurisdiction]);

  const sources = result?.sources?.length ? result.sources : result?.results ?? [];
  const answer = result?.answer ?? result?.guidance ?? "";
  const practicalSteps = result?.next_steps?.length
    ? result.next_steps
    : Array.from(new Set(sources.flatMap((source) => source.guidance ?? [])));
  const requiresVerification = Boolean(result?.requires_verification || result?.status === "requires_verification");

  return (
    <div className="space-y-4">
      <JourneyWizard current={step} labels={["Describe & locate", "Understand", "Take action"]} onStep={setStep} />
      {error && <Notice tone="error">{error}</Notice>}
      {step === 1 && (
        <Card>
          <Card.Body>
            <div className="space-y-4">
              <SectionTitle eyebrow="Consumer · Tenant · Labour" title="What happened, and where?" description="Jurisdiction matters—especially for tenancy and local procedures. Leave it blank rather than guessing." />
              <div>
                <FieldLabel>Describe the issue</FieldLabel>
                <textarea value={query} onChange={(event) => setQuery(event.target.value)} rows={5} placeholder="Example: My landlord has withheld my security deposit after I vacated the flat..." className="w-full resize-y rounded-xl px-3 py-2.5 text-sm outline-none" style={INPUT_STYLE} />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <FieldLabel optional>Domain</FieldLabel>
                  <select value={domain} onChange={(event) => setDomain(event.target.value as typeof domain)} className="w-full rounded-xl px-3 py-2.5 text-sm" style={INPUT_STYLE}>
                    <option value="">Let the service classify</option>
                    <option value="consumer">Consumer dispute</option>
                    <option value="tenant">Tenant / landlord</option>
                    <option value="labour">Labour / workplace</option>
                  </select>
                </div>
                <StateField value={jurisdiction} onChange={setJurisdiction} />
              </div>
              <ActionButton onClick={run} disabled={busy}>{busy ? <BusyLabel label="Finding sourced guidance..." /> : "Understand rights and pathway"}</ActionButton>
            </div>
          </Card.Body>
        </Card>
      )}
      {step >= 2 && result && (
        <div className="space-y-3">
          <Card>
            <Card.Body>
              <div className="space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <SectionTitle eyebrow={result.domain || "Civic guidance"} title={result.jurisdiction || "Jurisdiction not established"} description={`Status: ${(result.status || "requires verification").replace(/_/g, " ")}`} />
                  <ConfidenceBadge confidence={result.confidence} />
                </div>
                <MissingInformation items={result.missing_information} />
                {requiresVerification && <Notice tone="warning">This guidance requires verification before you rely on it for a filing or deadline.</Notice>}
                {answer ? <div className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "var(--color-text)" }}>{answer}</div> : <Notice tone="warning">No plain-language answer was available from the sourced records.</Notice>}
                <ProvenanceBlock provenance={result} sources={sources} />
                <div className="flex flex-wrap gap-2">
                  <ActionButton onClick={() => setStep(1)} secondary>Change issue</ActionButton>
                  <ActionButton onClick={() => setStep(3)} disabled={!answer}>Show practical next steps</ActionButton>
                </div>
              </div>
            </Card.Body>
          </Card>
          {sources.length > 0 && (
            <Card>
              <Card.Body>
                <div className="space-y-2">
                  <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>Retrieved records</p>
                  {sources.map((source, index) => {
                    const text = source.excerpt ?? source.summary ?? source.rule ?? source.content ?? source.text;
                    const href = safeExternalUrl(source.source_url);
                    return (
                      <div key={`${source.title ?? source.source ?? "record"}-${index}`} className="rounded-xl p-3" style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}>
                        <p className="text-xs font-semibold" style={{ color: "var(--color-text)" }}>{source.title || source.source || "Source record"}</p>
                        {text && <p className="mt-1 text-[11px] leading-relaxed" style={{ color: "var(--color-text-muted)" }}>{text}</p>}
                        {href && <a href={href} target="_blank" rel="noreferrer" className="mt-1 inline-block text-[10px] underline" style={{ color: "var(--color-primary)" }}>Open source</a>}
                      </div>
                    );
                  })}
                </div>
              </Card.Body>
            </Card>
          )}
          {step === 3 && (
            <Card>
              <Card.Body>
                <div className="grid gap-4 sm:grid-cols-2">
                  <SimpleSteps title="Next practical steps" items={practicalSteps} />
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>Evidence / documents</p>
                    {result.evidence_checklist?.length ? <ul className="mt-1 space-y-1 text-xs" style={{ color: "var(--color-text-muted)" }}>{result.evidence_checklist.map((item) => <li key={item}>☐ {item}</li>)}</ul> : <p className="mt-1 text-xs" style={{ color: "var(--color-text-faint)" }}>No evidence checklist was available.</p>}
                  </div>
                </div>
              </Card.Body>
            </Card>
          )}
          {result.disclaimer && <p className="px-2 text-center text-[10px]" style={{ color: "var(--color-text-faint)" }}>{result.disclaimer}</p>}
        </div>
      )}
    </div>
  );
}

export function CivicAssistant({ initialJourney = "rti", onOpenClaw }: CivicAssistantProps) {
  const [journey, setJourney] = useState<CivicJourney>(initialJourney);
  return (
    <div className="flex flex-col gap-4 px-4">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-center">
        <h2 className="text-xl font-bold gradient-text-hero">Civic Action Assistant</h2>
        <p className="mx-auto mt-1 max-w-xl text-xs leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
          Move from a plain-language problem to a sourced pathway, missing-information check, reviewed action, and next practical step.
        </p>
      </motion.div>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4" role="tablist" aria-label="Civic assistant journeys">
        {JOURNEYS.map((item) => {
          const active = journey === item.id;
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setJourney(item.id)}
              className="rounded-2xl p-3 text-left transition-all hover:scale-[1.01]"
              style={{
                background: active ? "var(--color-primary-dim)" : "var(--color-surface)",
                border: `1px solid ${active ? "var(--color-primary)" : "var(--color-border)"}`,
              }}
            >
              <span className="text-xl" aria-hidden>{item.icon}</span>
              <span className="mt-1 block text-xs font-semibold" style={{ color: active ? "var(--color-primary)" : "var(--color-text)" }}>{item.label}</span>
              <span className="mt-1 hidden text-[10px] leading-relaxed sm:block" style={{ color: "var(--color-text-faint)" }}>{item.description}</span>
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={journey} role="tabpanel" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
          {journey === "rti" && <RTIAssistant />}
          {journey === "schemes" && <SchemeAssistant />}
          {journey === "cpgrams" && <CPGRAMSAssistant onOpenClaw={onOpenClaw} />}
          {journey === "rights" && <RightsNavigator />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
