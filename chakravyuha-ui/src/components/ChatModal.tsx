"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { smartQuery, type SmartResponse } from "@/services/api";
import { useApp } from "@/context/AppContext";
import { Logo } from "@/components/Logo";

const QUICK_CHIPS = [
  "My license is lost",
  "Traffic challan help",
  "File an FIR",
  "Domestic violence",
  "Consumer complaint",
  "Bail process",
  "Property dispute",
  "Right to Information",
];

// Map Sarvam language codes to native script labels
const LANG_LABELS: Record<string, string> = {
  "hi-IN": "\u0939\u093F\u0928\u094D\u0926\u0940",
  "ta-IN": "\u0BA4\u0BAE\u0BBF\u0BB4\u0BCD",
  "te-IN": "\u0C24\u0C46\u0C32\u0C41\u0C17\u0C41",
  "kn-IN": "\u0C95\u0CA8\u0CCD\u0CA8\u0CA1",
  "ml-IN": "\u0D2E\u0D32\u0D2F\u0D3E\u0D33\u0D02",
  "bn-IN": "\u09AC\u09BE\u0982\u09B2\u09BE",
  "gu-IN": "\u0A97\u0AC1\u0A9C\u0AB0\u0ABE\u0AA4\u0AC0",
  "pa-IN": "\u0A2A\u0A70\u0A1C\u0A3E\u0A2C\u0A40",
  "od-IN": "\u0B13\u0B21\u0B3C\u0B3F\u0B06",
  "mr-IN": "\u092E\u0930\u093E\u0920\u0940",
};

/** Extract phone number from helpline string like "1091 (Women helpline)" */
function parseHelplineNumber(h: string): string | null {
  const m = h.match(/\d{3,5}/);
  return m ? m[0] : null;
}

interface ChatMessage {
  role: "user" | "ai";
  text: string;
  smartData?: SmartResponse;
}

interface ChatModalProps {
  open: boolean;
  onClose: () => void;
}

// ── Fallback categories when classifier returns "unknown" ────────────────────
const FALLBACK_CATEGORIES = [
  { label: "Theft", query: "Someone stole my belongings, what are my legal options" },
  { label: "Assault", query: "I was physically assaulted, what legal action can I take" },
  { label: "Fraud", query: "I have been cheated in a financial fraud" },
  { label: "Property", query: "I have a property dispute that needs legal resolution" },
  { label: "Family", query: "I am facing domestic violence at home" },
  { label: "Consumer", query: "I bought a defective product and want a refund" },
  { label: "Employment", query: "My employer has not paid my salary" },
  { label: "Emergency", query: "I need emergency legal help right now" },
];

// ── Severity config ─────────────────────────────────────────────────────────
const SEVERITY: Record<string, { bg: string; text: string; label: string }> = {
  critical: { bg: "rgba(239,68,68,0.2)", text: "#ef4444", label: "CRITICAL" },
  high: { bg: "rgba(249,115,22,0.2)", text: "#f97316", label: "HIGH" },
  medium: { bg: "rgba(232,180,184,0.2)", text: "#e8b4b8", label: "MEDIUM" },
  low: { bg: "rgba(167,139,250,0.2)", text: "#a78bfa", label: "LOW" },
};

// ── Category picker for unknown scenarios ────────────────────────────────────
function CategoryPicker({ onSelect, disabled }: { onSelect: (query: string) => void; disabled?: boolean }) {
  return (
    <div
      className="rounded-2xl p-3.5 flex flex-col gap-2.5 text-xs"
      style={{ background: "rgba(0,0,0,0.25)", border: "1px solid var(--color-border)" }}
    >
      <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
        I couldn&apos;t identify your specific issue. Please choose a category:
      </p>
      <div className="flex flex-wrap gap-2">
        {FALLBACK_CATEGORIES.map((cat) => (
          <button
            key={cat.label}
            onClick={() => onSelect(cat.query)}
            disabled={disabled}
            className="px-3 py-1.5 rounded-full text-xs font-medium transition-colors disabled:opacity-40"
            style={{
              background: "var(--color-primary-dim)",
              color: "var(--color-primary)",
              border: "1px solid rgba(167,139,250,0.3)",
            }}
          >
            {cat.label}
          </button>
        ))}
      </div>
      <p className="text-[10px]" style={{ color: "var(--color-text-faint)" }}>
        Or call NALSA at 15100 for free legal aid
      </p>
    </div>
  );
}

// ── Structured response card ────────────────────────────────────────────────
function ResponseCard({ data }: { data: SmartResponse }) {
  const [showDraft, setShowDraft] = useState(false);
  const sev = SEVERITY[data.severity] || SEVERITY.medium;

  return (
    <div
      className="rounded-2xl p-3.5 flex flex-col gap-2.5 text-xs"
      style={{ background: "rgba(0,0,0,0.25)", border: "1px solid var(--color-border)" }}
    >
      {/* Header: title + severity */}
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold text-sm" style={{ color: "var(--color-primary)" }}>
          {data.title}
        </span>
        <span
          className="px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider uppercase shrink-0"
          style={{ background: sev.bg, color: sev.text }}
        >
          {sev.label}
        </span>
      </div>

      {/* Guidance */}
      <div className="whitespace-pre-line leading-relaxed" style={{ color: "var(--color-text)" }}>
        {data.guidance}
      </div>

      {/* Sections */}
      {data.sections.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="font-semibold uppercase tracking-wider text-[9px]" style={{ color: "var(--color-secondary)" }}>
            Applicable Sections
          </span>
          <div className="flex flex-wrap gap-1">
            {data.sections.map((s, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded-full text-[10px]"
                style={{ background: "var(--color-secondary-dim)", color: "var(--color-secondary)", border: "1px solid rgba(232,180,184,0.2)" }}
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Outcome */}
      {data.outcome && (
        <div
          className="rounded-xl px-3 py-2"
          style={{ background: "var(--color-primary-dim)", border: "1px solid rgba(167,139,250,0.15)" }}
        >
          <span className="font-semibold" style={{ color: "var(--color-primary)" }}>Likely Outcome: </span>
          <span style={{ color: "var(--color-text)" }}>{data.outcome}</span>
        </div>
      )}

      {/* Complaint draft */}
      {data.complaint_draft && (
        <div>
          <button
            onClick={() => setShowDraft((p) => !p)}
            className="text-[10px] font-semibold px-2.5 py-1 rounded-full"
            style={{ background: "var(--color-accent-dim)", color: "var(--color-accent)", border: "1px solid rgba(129,140,248,0.2)" }}
          >
            {showDraft ? "Hide Draft" : "View Complaint Draft"}
          </button>
          <AnimatePresence>
            {showDraft && (
              <motion.pre
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-1.5 whitespace-pre-wrap text-[11px] leading-relaxed rounded-xl p-2.5 overflow-hidden"
                style={{ background: "rgba(0,0,0,0.3)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
              >
                {data.complaint_draft}
              </motion.pre>
            )}
          </AnimatePresence>
        </div>
      )}

      {/* Emergency call button for critical/high severity */}
      {(data.severity === "critical" || data.severity === "high") && data.helplines.length > 0 && (() => {
        const num = parseHelplineNumber(data.helplines[0]);
        return num ? (
          <a
            href={`tel:${num}`}
            className="flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold tracking-wide animate-pulse"
            style={{
              background: "rgba(239,68,68,0.25)",
              color: "#ef4444",
              border: "2px solid rgba(239,68,68,0.5)",
            }}
          >
            <span className="text-lg">📞</span> Call {data.helplines[0]}
          </a>
        ) : null;
      })()}

      {/* Helplines */}
      {data.helplines.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {data.helplines.map((h, i) => {
            const num = parseHelplineNumber(h);
            return num ? (
              <a
                key={i}
                href={`tel:${num}`}
                className="px-2 py-0.5 rounded-full text-[10px] font-bold inline-flex items-center gap-1"
                style={{ background: "rgba(239,68,68,0.15)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}
              >
                📞 {h}
              </a>
            ) : (
              <span
                key={i}
                className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                style={{ background: "rgba(239,68,68,0.15)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.2)" }}
              >
                {h}
              </span>
            );
          })}
        </div>
      )}

      {/* Language badge + Source */}
      <div className="flex items-center justify-between">
        {data.response_language && data.response_language !== "en-IN" ? (
          <span
            className="px-2 py-0.5 rounded-full text-[9px] font-semibold"
            style={{ background: "var(--color-primary-dim)", color: "var(--color-primary)", border: "1px solid rgba(167,139,250,0.2)" }}
          >
            Responded in {LANG_LABELS[data.response_language] || data.response_language}
          </span>
        ) : <span />}
        <span className="text-[9px] uppercase tracking-widest" style={{ color: "var(--color-text-faint)" }}>
          {data.source === "classifier" ? "Verified Legal Database" : "Keyword Search"}
        </span>
      </div>
    </div>
  );
}

export function ChatModal({ open, onClose }: ChatModalProps) {
  const { state } = useApp();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
      setInput("");
      setIsLoading(true);

      try {
        const res = await smartQuery(trimmed, state.language.code);

        setMessages((prev) => [
          ...prev,
          { role: "ai", text: "", smartData: res },
        ]);
      } catch (err) {
        console.error("Chat query error:", err);
        setMessages((prev) => [
          ...prev,
          { role: "ai", text: "Could not reach the legal engine. Please try again." },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, state.language.code]
  );

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop — dims and blurs background */}
          <motion.div
            className="fixed inset-0 z-[55]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(2px)" }}
          />

          {/* Slide-over panel from right */}
          <motion.div
            className="fixed top-0 right-0 bottom-0 z-[60] flex flex-col w-full md:w-[480px] md:max-w-[90vw]"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            style={{
              background: "var(--color-bg)",
              borderLeft: "1px solid var(--color-border-bright)",
              boxShadow: "-10px 0 40px rgba(0,0,0,0.3)",
            }}
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-5 py-4 border-b shrink-0"
              style={{ borderColor: "var(--color-border)" }}
            >
              <div className="flex items-center gap-2">
                <Logo size={24} />
                <h2 className="font-semibold text-sm" style={{ color: "var(--color-text)" }}>
                  Lexaro
                  <span className="gradient-text-violet text-xs font-normal ml-0.5">.AI</span>
                </h2>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm transition-colors"
                  style={{ color: "var(--color-text-muted)", background: "var(--color-surface)" }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3 min-h-0">
              {messages.length === 0 && (
                <div className="text-center py-6">
                  <p className="text-sm font-medium mb-1" style={{ color: "var(--color-text-muted)" }}>
                    Ask any legal question
                  </p>
                  <p className="text-xs" style={{ color: "var(--color-text-faint)" }}>
                    Classification-first AI — no hallucinations, curated legal guidance
                  </p>
                </div>
              )}
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`max-w-[90%] ${m.role === "user" ? "self-end" : "self-start"}`}
                >
                  {m.role === "user" ? (
                    <div
                      className="rounded-2xl rounded-br-sm px-4 py-2.5 text-sm"
                      style={{ background: "var(--color-accent-dim)", color: "var(--color-accent)" }}
                    >
                      {m.text}
                    </div>
                  ) : m.smartData?.scenario === "unknown" || (m.smartData && !m.smartData.guidance) ? (
                    <CategoryPicker onSelect={send} disabled={isLoading} />
                  ) : m.smartData ? (
                    <ResponseCard data={m.smartData} />
                  ) : (
                    <div
                      className="rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm whitespace-pre-line border-l-2"
                      style={{
                        background: "var(--color-surface)",
                        borderColor: "var(--color-primary)",
                        color: "var(--color-text)",
                      }}
                    >
                      {m.text}
                    </div>
                  )}
                </div>
              ))}

              {/* Loading indicator */}
              {isLoading && (
                <div className="self-start flex items-center gap-2 px-4 py-3">
                  {[0, 1, 2].map((i) => (
                    <motion.span
                      key={i}
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ background: "var(--color-primary)" }}
                      animate={{ y: [0, -4, 0] }}
                      transition={{ repeat: Infinity, duration: 0.7, delay: i * 0.15 }}
                    />
                  ))}
                  <span className="text-xs ml-1" style={{ color: "var(--color-text-faint)" }}>
                    Classifying legal issue...
                  </span>
                </div>
              )}
              <div ref={endRef} />
            </div>

            {/* Quick chips */}
            <div className="flex gap-2 px-4 pb-2 overflow-x-auto shrink-0">
              {QUICK_CHIPS.map((c) => (
                <button key={c} onClick={() => send(c)} disabled={isLoading} className="chip shrink-0">
                  {c}
                </button>
              ))}
            </div>

            {/* Input */}
            <div className="flex gap-2 px-4 py-3 border-t shrink-0" style={{ borderColor: "var(--color-border)" }}>
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send(input)}
                placeholder="Describe your legal problem..."
                disabled={isLoading}
                className="flex-1 bg-transparent text-sm outline-none disabled:opacity-50"
                style={{ color: "var(--color-text)" }}
              />
              <button
                onClick={() => send(input)}
                disabled={!input.trim() || isLoading}
                className="px-4 py-2 rounded-full text-xs font-semibold disabled:opacity-40"
                style={{
                  background: "var(--color-primary-dim)",
                  color: "var(--color-primary)",
                  border: "1px solid var(--color-primary)",
                }}
              >
                Send
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
