"use client";

import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { autoDraft, type AutoDraftResponse } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { Card } from "@/components/Card";

// ── Quick scenario chips ────────────────────────────────────────────────────

const QUICK_SCENARIOS = [
  { label: "Phone stolen", narrative: "My neighbor stole my mobile phone from my house" },
  { label: "Cheated of money", narrative: "Someone cheated me of Rs 50,000 promising a business deal" },
  { label: "Physical assault", narrative: "I was attacked and beaten by an unknown person at the market" },
  { label: "Domestic violence", narrative: "I am facing domestic violence at home" },
];

// ── Section badge colors ────────────────────────────────────────────────────

const DOC_TYPE_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  FIR: { bg: "rgba(239,68,68,0.15)", color: "#ef4444", label: "First Information Report" },
  LEGAL_NOTICE: { bg: "rgba(249,115,22,0.15)", color: "#f97316", label: "Legal Notice" },
  COMPLAINT: { bg: "rgba(129,140,248,0.15)", color: "#818cf8", label: "Complaint Petition" },
};

// ── Main Component ──────────────────────────────────────────────────────────

export function ComplaintDraftCard() {
  const { state } = useApp();

  // Form state
  const [narrative, setNarrative] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");

  // Pipeline state
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AutoDraftResponse | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [showStrategy, setShowStrategy] = useState(false);

  const resultRef = useRef<HTMLDivElement>(null);

  const handleSubmit = useCallback(async () => {
    const trimmed = narrative.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setResult(null);
    setError("");
    setCopied(false);

    try {
      const res = await autoDraft({
        narrative: trimmed,
        complainant_name: name.trim() || undefined,
        complainant_phone: phone.trim() || undefined,
        language: state.language.code,
      });
      setResult(res);
      // Scroll to result after render
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, [narrative, name, phone, loading, state.language.code]);

  const handleCopy = useCallback(() => {
    if (!result) return;
    navigator.clipboard.writeText(result.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [result]);

  const handleReset = useCallback(() => {
    setResult(null);
    setError("");
    setNarrative("");
    setName("");
    setPhone("");
    setCopied(false);
    setShowStrategy(false);
  }, []);

  const handleQuickFill = useCallback((text: string) => {
    setNarrative(text);
    setResult(null);
    setError("");
  }, []);

  return (
    <div className="flex flex-col gap-4 px-4">
      {/* Header */}
      <motion.div
        className="text-center"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h2 className="text-lg font-bold gradient-text-hero">Draft Legal Document</h2>
        <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
          Describe your situation — AI auto-generates FIR, Legal Notice, or Complaint
        </p>
      </motion.div>

      {/* Input Form */}
      <Card>
        <Card.Body>
          <div className="flex flex-col gap-3">
            {/* Quick scenario chips */}
            <div className="flex flex-wrap gap-1.5">
              {QUICK_SCENARIOS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => handleQuickFill(s.narrative)}
                  disabled={loading}
                  className="px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors disabled:opacity-40"
                  style={{
                    background: "var(--color-primary-dim)",
                    color: "var(--color-primary)",
                    border: "1px solid rgba(167,139,250,0.3)",
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>

            {/* Narrative textarea */}
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block" style={{ color: "var(--color-text-muted)" }}>
                Describe what happened *
              </label>
              <textarea
                value={narrative}
                onChange={(e) => setNarrative(e.target.value)}
                placeholder="E.g., My neighbor stole my phone from my house on March 20. I have CCTV footage..."
                disabled={loading}
                rows={4}
                className="w-full rounded-xl px-3 py-2.5 text-sm resize-none outline-none disabled:opacity-50"
                style={{
                  background: "rgba(0,0,0,0.2)",
                  color: "var(--color-text)",
                  border: "1px solid var(--color-border)",
                }}
              />
            </div>

            {/* Optional fields row */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block" style={{ color: "var(--color-text-muted)" }}>
                  Your Name
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Optional"
                  disabled={loading}
                  className="w-full rounded-lg px-3 py-2 text-xs outline-none disabled:opacity-50"
                  style={{
                    background: "rgba(0,0,0,0.2)",
                    color: "var(--color-text)",
                    border: "1px solid var(--color-border)",
                  }}
                />
              </div>
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block" style={{ color: "var(--color-text-muted)" }}>
                  Phone
                </label>
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="Optional"
                  disabled={loading}
                  className="w-full rounded-lg px-3 py-2 text-xs outline-none disabled:opacity-50"
                  style={{
                    background: "rgba(0,0,0,0.2)",
                    color: "var(--color-text)",
                    border: "1px solid var(--color-border)",
                  }}
                />
              </div>
            </div>

            {/* Submit button */}
            <motion.button
              onClick={handleSubmit}
              disabled={!narrative.trim() || loading}
              className="w-full py-3 rounded-xl text-sm font-semibold tracking-wide uppercase disabled:opacity-40 transition-colors"
              style={{
                background: "var(--color-primary-dim)",
                color: "var(--color-primary)",
                border: "1px solid var(--color-primary)",
              }}
              whileHover={!loading ? { scale: 1.01 } : {}}
              whileTap={!loading ? { scale: 0.98 } : {}}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <motion.span
                    className="inline-block w-4 h-4 rounded-full border-2 border-t-transparent"
                    style={{ borderColor: "var(--color-primary)", borderTopColor: "transparent" }}
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
                  />
                  Generating Document...
                </span>
              ) : (
                "Generate Legal Document"
              )}
            </motion.button>
          </div>
        </Card.Body>
      </Card>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-xl px-4 py-3 text-xs"
            style={{ background: "rgba(239,68,68,0.15)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.3)" }}
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Result */}
      <AnimatePresence>
        {result && (
          <motion.div
            ref={resultRef}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col gap-3"
          >
            {/* Status & extraction summary */}
            <Card>
              <Card.Body>
                <div className="flex flex-col gap-2.5">
                  {/* Doc type badge + offense */}
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider"
                        style={{
                          background: DOC_TYPE_STYLE[result.document_type]?.bg ?? "var(--color-primary-dim)",
                          color: DOC_TYPE_STYLE[result.document_type]?.color ?? "var(--color-primary)",
                        }}
                      >
                        {result.document_type}
                      </span>
                      <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
                        {DOC_TYPE_STYLE[result.document_type]?.label ?? result.document_type}
                      </span>
                    </div>
                    <span
                      className="px-2 py-0.5 rounded-full text-[9px] font-semibold"
                      style={{
                        background: result.status === "success" ? "rgba(34,197,94,0.15)" : "rgba(249,115,22,0.15)",
                        color: result.status === "success" ? "#22c55e" : "#f97316",
                      }}
                    >
                      {result.status === "success" ? "COMPLETE" : result.status.toUpperCase()}
                    </span>
                  </div>

                  {/* Extracted info grid */}
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                    <div>
                      <span style={{ color: "var(--color-text-faint)" }}>Offense: </span>
                      <span className="font-medium" style={{ color: "var(--color-text)" }}>{result.extracted_offense || "N/A"}</span>
                    </div>
                    <div>
                      <span style={{ color: "var(--color-text-faint)" }}>Confidence: </span>
                      <span className="font-medium" style={{ color: "var(--color-text)" }}>{Math.round(result.offense_confidence * 100)}%</span>
                    </div>
                    <div>
                      <span style={{ color: "var(--color-text-faint)" }}>Cognizable: </span>
                      <span className="font-medium" style={{ color: result.cognizable ? "#22c55e" : "var(--color-text)" }}>
                        {result.cognizable ? "Yes" : "No"}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: "var(--color-text-faint)" }}>Bailable: </span>
                      <span className="font-medium" style={{ color: "var(--color-text)" }}>
                        {result.bailable ? "Yes" : "No"}
                      </span>
                    </div>
                  </div>

                  {/* Sections */}
                  {result.applicable_sections.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {result.applicable_sections.map((s) => (
                        <span
                          key={s}
                          className="px-2 py-0.5 rounded-full text-[10px]"
                          style={{ background: "var(--color-secondary-dim)", color: "var(--color-secondary)", border: "1px solid rgba(232,180,184,0.2)" }}
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Punishment + jurisdiction */}
                  {result.punishment_summary && (
                    <div className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                      {result.jurisdiction} | {result.punishment_summary}
                    </div>
                  )}

                  {/* Missing fields warning */}
                  {result.missing_fields.length > 0 && (
                    <div
                      className="rounded-lg px-3 py-2 text-[10px]"
                      style={{ background: "rgba(249,115,22,0.1)", border: "1px solid rgba(249,115,22,0.2)", color: "#f97316" }}
                    >
                      Missing: {result.missing_fields.map((f) => f.replace(/_/g, " ")).join(", ")}
                    </div>
                  )}
                </div>
              </Card.Body>
            </Card>

            {/* Generated document */}
            <Card>
              <Card.Header>
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-sm" style={{ color: "var(--color-text)" }}>
                    Generated Document
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={handleCopy}
                      className="px-3 py-1 rounded-full text-[10px] font-semibold transition-colors"
                      style={{
                        background: copied ? "rgba(34,197,94,0.15)" : "var(--color-primary-dim)",
                        color: copied ? "#22c55e" : "var(--color-primary)",
                        border: `1px solid ${copied ? "rgba(34,197,94,0.3)" : "rgba(167,139,250,0.3)"}`,
                      }}
                    >
                      {copied ? "Copied!" : "Copy"}
                    </button>
                  </div>
                </div>
              </Card.Header>
              <Card.Body>
                <pre
                  className="whitespace-pre-wrap text-xs leading-relaxed max-h-[400px] overflow-y-auto rounded-xl p-3"
                  style={{
                    background: "rgba(0,0,0,0.25)",
                    color: "var(--color-text)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  {result.content}
                </pre>
              </Card.Body>
            </Card>

            {/* Legal strategy */}
            {result.strategy && (
              <Card>
                <Card.Body>
                  <button
                    onClick={() => setShowStrategy((v) => !v)}
                    className="w-full flex items-center justify-between text-sm font-semibold"
                    style={{ color: "var(--color-primary)" }}
                  >
                    <span>Legal Strategy & Next Steps</span>
                    <span>{showStrategy ? "\u25B2" : "\u25BC"}</span>
                  </button>

                  <AnimatePresence>
                    {showStrategy && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="flex flex-col gap-2.5 mt-3 text-xs">
                          {/* Strategy summary */}
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                            {result.strategy.recommended_forum && (
                              <div>
                                <span style={{ color: "var(--color-text-faint)" }}>Forum: </span>
                                <span style={{ color: "var(--color-text)" }}>{result.strategy.recommended_forum}</span>
                              </div>
                            )}
                            {result.strategy.total_timeline && (
                              <div>
                                <span style={{ color: "var(--color-text-faint)" }}>Timeline: </span>
                                <span style={{ color: "var(--color-text)" }}>{result.strategy.total_timeline}</span>
                              </div>
                            )}
                            {result.strategy.total_estimated_cost && (
                              <div>
                                <span style={{ color: "var(--color-text-faint)" }}>Est. Cost: </span>
                                <span style={{ color: "var(--color-text)" }}>{result.strategy.total_estimated_cost}</span>
                              </div>
                            )}
                            {result.strategy.next_immediate_action && (
                              <div className="col-span-2">
                                <span style={{ color: "var(--color-text-faint)" }}>Next Action: </span>
                                <span className="font-medium" style={{ color: "var(--color-primary)" }}>{result.strategy.next_immediate_action}</span>
                              </div>
                            )}
                          </div>

                          {/* Evidence checklist */}
                          {result.strategy.evidence_checklist && result.strategy.evidence_checklist.length > 0 && (
                            <div>
                              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>
                                Evidence Checklist
                              </span>
                              <div className="flex flex-col gap-1 mt-1">
                                {result.strategy.evidence_checklist.map((item, i) => (
                                  <div key={i} className="flex items-start gap-1.5 text-[11px]" style={{ color: "var(--color-text-muted)" }}>
                                    <span style={{ color: "var(--color-text-faint)" }}>[ ]</span>
                                    {item}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Action steps */}
                          {result.strategy.steps && result.strategy.steps.length > 0 && (
                            <div>
                              <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>
                                Action Steps
                              </span>
                              <div className="flex flex-col gap-1.5 mt-1">
                                {result.strategy.steps.map((step) => (
                                  <div
                                    key={step.step}
                                    className="rounded-lg px-2.5 py-1.5 text-[11px]"
                                    style={{ background: "rgba(0,0,0,0.15)", border: "1px solid var(--color-border)" }}
                                  >
                                    <span className="font-semibold" style={{ color: "var(--color-primary)" }}>
                                      {step.step}. {step.title}
                                    </span>
                                    <span style={{ color: "var(--color-text-faint)" }}> — {step.timeline} | {step.cost}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Card.Body>
              </Card>
            )}

            {/* Reset button */}
            <button
              onClick={handleReset}
              className="text-xs underline self-center py-2 transition-opacity opacity-50 hover:opacity-80"
              style={{ color: "var(--color-text-muted)" }}
            >
              Start new draft
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
