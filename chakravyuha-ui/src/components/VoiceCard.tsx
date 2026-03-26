"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useApp } from "@/context/AppContext";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useState, useRef, useEffect, useCallback } from "react";
import { smartQuery, smartVoice, type SmartResponse } from "@/services/api";

// ── Severity badge ──────────────────────────────────────────────────────────
function SeverityBadge({ severity }: { severity: string }) {
  const config: Record<string, { bg: string; text: string; label: string }> = {
    critical: { bg: "rgba(239,68,68,0.2)", text: "#ef4444", label: "CRITICAL" },
    high: { bg: "rgba(249,115,22,0.2)", text: "#f97316", label: "HIGH" },
    medium: { bg: "rgba(232,180,184,0.2)", text: "#e8b4b8", label: "MEDIUM" },
    low: { bg: "rgba(167,139,250,0.2)", text: "#a78bfa", label: "LOW" },
  };
  const c = config[severity] || config.medium;
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wider uppercase"
      style={{ background: c.bg, color: c.text }}
    >
      {c.label}
    </span>
  );
}

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

// ── UI i18n labels per language ───────────────────────────────────────────────
type UILabels = {
  likelyOutcome: string;
  relevantSections: string;
  viewComplaint: string;
  hideComplaint: string;
  call: string;
  source: string;
  verifiedDb: string;
  keywordSearch: string;
  respondedIn: string;
  tapMic: string;
  recording: string;
  processing: string;
  typeQuestion: string;
  send: string;
  disclaimer: string;
  youSaid: string;
  categoryPrompt: string;
  nalsaHint: string;
  helplines: string;
};

const UI_LABELS: Record<string, UILabels> = {
  "en-IN": {
    likelyOutcome: "Likely Outcome",
    relevantSections: "Relevant Sections",
    viewComplaint: "View Complaint Draft",
    hideComplaint: "Hide Complaint Draft",
    call: "Call",
    source: "Source",
    verifiedDb: "Verified Legal Database",
    keywordSearch: "Keyword Search",
    respondedIn: "Responded in",
    tapMic: "Tap microphone to speak",
    recording: "Recording... tap to stop",
    processing: "Processing...",
    typeQuestion: "Or type your legal question...",
    send: "Send",
    disclaimer: "This is not legal advice. Contact a lawyer for case-specific guidance.",
    youSaid: "You said",
    categoryPrompt: "I couldn\u2019t classify this issue. Please choose a category:",
    nalsaHint: "Or call NALSA at 15100 for free legal aid",
    helplines: "Helplines",
  },
  "ta-IN": {
    likelyOutcome: "\u0B89\u0BA4\u0BCD\u0BA4\u0BC7\u0B9A \u0BAE\u0BC1\u0B9F\u0BBF\u0BB5\u0BC1",
    relevantSections: "\u0BA4\u0BCA\u0B9F\u0BB0\u0BCD\u0BAA\u0BC1\u0B9F\u0BC8\u0BAF \u0BAA\u0BBF\u0BB0\u0BBF\u0BB5\u0BC1\u0B95\u0BB3\u0BCD",
    viewComplaint: "\u0BAE\u0BC1\u0B95\u0BCD\u0B95\u0BBF\u0BAF \u0BB5\u0BB0\u0BC8\u0BB5\u0BC1 \u0B95\u0BBE\u0BA3\u0BCD\u0B95",
    hideComplaint: "\u0BAE\u0BC1\u0B95\u0BCD\u0B95\u0BBF\u0BAF \u0BB5\u0BB0\u0BC8\u0BB5\u0BC1 \u0BAE\u0BB1\u0BC8",
    call: "\u0B85\u0BB4\u0BC8",
    source: "\u0BAE\u0BC2\u0BB2\u0BAE\u0BCD",
    verifiedDb: "\u0B9A\u0BB0\u0BBF\u0BAA\u0BBE\u0BB0\u0BCD\u0B95\u0BCD\u0B95\u0BAA\u0BCD\u0BAA\u0B9F\u0BCD\u0B9F \u0B9A\u0B9F\u0BCD\u0B9F \u0BA4\u0BB0\u0BB5\u0BC1\u0BA4\u0BCD\u0BA4\u0BB3\u0BAE\u0BCD",
    keywordSearch: "\u0B9A\u0BCA\u0BB2\u0BCD \u0BA4\u0BC7\u0B9F\u0BB2\u0BCD",
    respondedIn: "\u0BAA\u0BA4\u0BBF\u0BB2\u0BCD \u0BAE\u0BCA\u0BB4\u0BBF",
    tapMic: "\u0BAA\u0BC7\u0B9A \u0BAE\u0BC8\u0B95\u0BCD\u0B95\u0BC8 \u0BA4\u0BCA\u0B9F\u0BB5\u0BC1\u0BAE\u0BCD",
    recording: "\u0BAA\u0BA4\u0BBF\u0BB5\u0BC1 \u0B9A\u0BC6\u0BAF\u0BCD\u0BAF\u0BAA\u0BCD\u0BAA\u0B9F\u0BC1\u0B95\u0BBF\u0BB1\u0BA4\u0BC1... \u0BA8\u0BBF\u0BB1\u0BC1\u0BA4\u0BCD\u0BA4 \u0BA4\u0BCA\u0B9F\u0BB5\u0BC1\u0BAE\u0BCD",
    processing: "\u0B9A\u0BC6\u0BAF\u0BB2\u0BCD\u0BAA\u0B9F\u0BC1\u0BA4\u0BCD\u0BA4\u0BAA\u0BCD\u0BAA\u0B9F\u0BC1\u0B95\u0BBF\u0BB1\u0BA4\u0BC1...",
    typeQuestion: "\u0B89\u0B99\u0BCD\u0B95\u0BB3\u0BCD \u0B9A\u0B9F\u0BCD\u0B9F \u0B95\u0BC7\u0BB3\u0BCD\u0BB5\u0BBF\u0BAF\u0BC8 \u0BA4\u0B9F\u0BCD\u0B9F\u0B9A\u0BCD\u0B9A\u0BC1 \u0B9A\u0BC6\u0BAF\u0BCD\u0BAF\u0BB5\u0BC1\u0BAE\u0BCD...",
    send: "\u0B85\u0BA9\u0BC1\u0BAA\u0BCD\u0BAA\u0BC1",
    disclaimer: "\u0B87\u0BA4\u0BC1 \u0B9A\u0B9F\u0BCD\u0B9F \u0B86\u0BB2\u0BCB\u0B9A\u0BA9\u0BC8 \u0B85\u0BB2\u0BCD\u0BB2. \u0B95\u0BC1\u0BB1\u0BBF\u0BAA\u0BCD\u0BAA\u0BBF\u0B9F\u0BCD\u0B9F \u0BB5\u0BB4\u0BBF\u0B95\u0BBE\u0B9F\u0BCD\u0B9F\u0BC1 \u0BA8\u0BBE\u0B9F\u0BC1\u0B99\u0BCD\u0B95\u0BB3\u0BCD.",
    youSaid: "\u0BA8\u0BC0\u0B99\u0BCD\u0B95\u0BB3\u0BCD \u0B9A\u0BCA\u0BA9\u0BCD\u0BA9\u0BA4\u0BC1",
    categoryPrompt: "\u0B87\u0BA8\u0BCD\u0BA4 \u0BAA\u0BBF\u0BB0\u0B9A\u0BCD\u0B9A\u0BBF\u0BA9\u0BC8\u0BAF\u0BC8 \u0BB5\u0B95\u0BC8\u0BAA\u0BCD\u0BAA\u0B9F\u0BC1\u0BA4\u0BCD\u0BA4 \u0BAE\u0BC1\u0B9F\u0BBF\u0BAF\u0BB5\u0BBF\u0BB2\u0BCD\u0BB2\u0BC8. \u0B92\u0BB0\u0BC1 \u0BB5\u0B95\u0BC8\u0BAF\u0BC8 \u0BA4\u0BC7\u0BB0\u0BCD\u0BA8\u0BCD\u0BA4\u0BC6\u0B9F\u0BC1\u0B95\u0BCD\u0B95\u0BB5\u0BC1\u0BAE\u0BCD:",
    nalsaHint: "\u0B89\u0BA4\u0BB5\u0BBF\u0B95\u0BCD\u0B95\u0BC1 NALSA 15100 \u0B85\u0BB4\u0BC8\u0B95\u0BCD\u0B95\u0BB5\u0BC1\u0BAE\u0BCD",
    helplines: "\u0B89\u0BA4\u0BB5\u0BBF \u0B8E\u0BA3\u0BCD\u0B95\u0BB3\u0BCD",
  },
  "hi-IN": {
    likelyOutcome: "\u0938\u0902\u092D\u093E\u0935\u093F\u0924 \u092A\u0930\u093F\u0923\u093E\u092E",
    relevantSections: "\u0938\u0902\u092C\u0902\u0927\u093F\u0924 \u0927\u093E\u0930\u093E\u090F\u0901",
    viewComplaint: "\u0936\u093F\u0915\u093E\u092F\u0924 \u0921\u094D\u0930\u093E\u092B\u094D\u091F \u0926\u0947\u0916\u0947\u0902",
    hideComplaint: "\u0936\u093F\u0915\u093E\u092F\u0924 \u0921\u094D\u0930\u093E\u092B\u094D\u091F \u091B\u0941\u092A\u093E\u090F\u0901",
    call: "\u0915\u0949\u0932 \u0915\u0930\u0947\u0902",
    source: "\u0938\u094D\u0930\u094B\u0924",
    verifiedDb: "\u0938\u0924\u094D\u092F\u093E\u092A\u093F\u0924 \u0915\u093E\u0928\u0942\u0928\u0940 \u0921\u0947\u091F\u093E\u092C\u0947\u0938",
    keywordSearch: "\u0915\u0940\u0935\u0930\u094D\u0921 \u0916\u094B\u091C",
    respondedIn: "\u091C\u0935\u093E\u092C \u092D\u093E\u0937\u093E",
    tapMic: "\u092C\u094B\u0932\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F \u092E\u093E\u0907\u0915 \u0926\u092C\u093E\u090F\u0902",
    recording: "\u0930\u093F\u0915\u0949\u0930\u094D\u0921\u093F\u0902\u0917... \u0930\u094B\u0915\u0928\u0947 \u0915\u0947 \u0932\u093F\u090F \u0926\u092C\u093E\u090F\u0902",
    processing: "\u092A\u094D\u0930\u094B\u0938\u0947\u0938 \u0939\u094B \u0930\u0939\u093E \u0939\u0948...",
    typeQuestion: "\u0905\u092A\u0928\u093E \u0915\u093E\u0928\u0942\u0928\u0940 \u0938\u0935\u093E\u0932 \u091F\u093E\u0907\u092A \u0915\u0930\u0947\u0902...",
    send: "\u092D\u0947\u091C\u0947\u0902",
    disclaimer: "\u092F\u0939 \u0915\u093E\u0928\u0942\u0928\u0940 \u0938\u0932\u093E\u0939 \u0928\u0939\u0940\u0902 \u0939\u0948\u0964 \u0935\u0915\u0940\u0932 \u0938\u0947 \u0938\u0902\u092A\u0930\u094D\u0915 \u0915\u0930\u0947\u0902\u0964",
    youSaid: "\u0906\u092A\u0928\u0947 \u0915\u0939\u093E",
    categoryPrompt: "\u0907\u0938 \u092E\u0941\u0926\u094D\u0926\u0947 \u0915\u094B \u0935\u0930\u094D\u0917\u0940\u0915\u0943\u0924 \u0928\u0939\u0940\u0902 \u0915\u093F\u092F\u093E \u091C\u093E \u0938\u0915\u093E\u0964 \u090F\u0915 \u0936\u094D\u0930\u0947\u0923\u0940 \u091A\u0941\u0928\u0947\u0902:",
    nalsaHint: "\u092E\u0926\u0926 \u0915\u0947 \u0932\u093F\u090F NALSA 15100 \u092A\u0930 \u0915\u0949\u0932 \u0915\u0930\u0947\u0902",
    helplines: "\u0939\u0947\u0932\u094D\u092A\u0932\u093E\u0907\u0928",
  },
};

const DEFAULT_LABELS = UI_LABELS["en-IN"];

function getLabels(langCode: string): UILabels {
  return UI_LABELS[langCode] || DEFAULT_LABELS;
}

/** Extract phone number from helpline string like "1091 (Women helpline)" */
function parseHelplineNumber(h: string): string | null {
  const m = h.match(/\d{3,5}/);
  return m ? m[0] : null;
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

// ── Format a SmartResponse into chat messages ───────────────────────────────
function formatSmartResponse(r: SmartResponse, langCode: string): string {
  const l = getLabels(langCode);
  const parts: string[] = [];

  parts.push(`${r.title}`);

  if (r.guidance) {
    parts.push(r.guidance);
  }

  if (r.sections.length > 0) {
    parts.push(`${l.relevantSections}:\n` + r.sections.map((s) => `  - ${s}`).join("\n"));
  }

  if (r.outcome) {
    parts.push(`${l.likelyOutcome}: ${r.outcome}`);
  }

  if (r.helplines.length > 0) {
    parts.push(`${l.helplines}:\n` + r.helplines.map((h) => `  ${h}`).join("\n"));
  }

  return parts.join("\n\n");
}

// ── Category picker for unknown scenarios ────────────────────────────────────
function CategoryPicker({ onSelect, disabled, labels }: { onSelect: (query: string) => void; disabled?: boolean; labels: UILabels }) {
  return (
    <div
      className="rounded-2xl p-3.5 flex flex-col gap-2.5 text-xs"
      style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
    >
      <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
        {labels.categoryPrompt}
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
        {labels.nalsaHint}
      </p>
    </div>
  );
}

export function VoiceCard() {
  const { state, addMessage, toggleRecording } = useApp();
  const { recorderState, audioBlob, startRecording, stopRecording, clearRecording, error } =
    useAudioRecorder();
  const [textInput, setTextInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [lastResponse, setLastResponse] = useState<SmartResponse | null>(null);
  const [lastTranscript, setLastTranscript] = useState<string>("");
  const [showComplaint, setShowComplaint] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const isRecording = recorderState === "recording";
  const labels = getLabels(state.language.code);

  // Auto-scroll chat
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.chatHistory]);

  // Process audio blob when recording stops
  useEffect(() => {
    if (!audioBlob || audioBlob.size === 0) return;

    const sendAudio = async () => {
      setIsProcessing(true);
      setStatusText("Transcribing voice...");
      addMessage("user", "Processing voice...");

      try {
        const res = await smartVoice(audioBlob, state.language.code);

        if (res.error || !res.transcript) {
          setLastTranscript("");
          addMessage(
            "assistant",
            res.error || "I couldn't understand the audio. Please try again or type your question."
          );
          return;
        }

        setLastTranscript(res.transcript);
        addMessage("user", `"${res.transcript}"`);

        if (res.response) {
          setLastResponse(res.response);
          setShowComplaint(false);
          addMessage("assistant", formatSmartResponse(res.response, state.language.code));
        } else {
          addMessage("assistant", "I couldn't classify your legal issue. Please try again with more details.");
        }

        if (res.audio) {
          try {
            const audioBytes = Uint8Array.from(atob(res.audio), (c) => c.charCodeAt(0));
            const blob = new Blob([audioBytes], { type: "audio/wav" });
            const url = URL.createObjectURL(blob);
            if (audioRef.current) {
              audioRef.current.src = url;
              audioRef.current.play().catch(() => {});
            }
          } catch {
            // TTS playback failed silently
          }
        }
      } catch (err) {
        console.error("Voice processing error:", err);
        addMessage(
          "assistant",
          "Voice processing failed. Please check your connection or type your question below."
        );
      } finally {
        setIsProcessing(false);
        setStatusText("");
        clearRecording();
      }
    };

    sendAudio();
  }, [audioBlob]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleMicClick = async () => {
    if (isRecording) {
      stopRecording();
      if (state.isRecording) toggleRecording();
    } else {
      await startRecording();
      if (!state.isRecording) toggleRecording();
    }
  };

  const sendQuery = useCallback(async (text: string) => {
    if (!text.trim() || isProcessing) return;

    addMessage("user", text);
    setIsProcessing(true);
    setStatusText("Classifying your legal issue...");

    try {
      const res = await smartQuery(text, state.language.code);
      setLastResponse(res);
      setLastTranscript("");
      setShowComplaint(false);
      addMessage("assistant", formatSmartResponse(res, state.language.code));
    } catch (err) {
      console.error("Query error:", err);
      addMessage("assistant", "Could not reach the legal engine. Please try again.");
    } finally {
      setIsProcessing(false);
      setStatusText("");
    }
  }, [isProcessing, state.language.code, addMessage]);

  const handleSend = useCallback(async () => {
    const text = textInput.trim();
    if (!text) return;
    setTextInput("");
    await sendQuery(text);
  }, [textInput, sendQuery]);

  return (
    <div className="flex flex-col gap-4">
      {/* Hidden audio element for TTS playback */}
      <audio ref={audioRef} className="hidden" />

      {/* Chat history */}
      <div
        className="rounded-2xl min-h-[200px] max-h-[360px] overflow-y-auto p-4 flex flex-col gap-3"
        style={{ background: "var(--color-surface)" }}
      >
        {state.chatHistory.length === 0 && (
          <p className="text-sm text-center mt-8" style={{ color: "var(--color-text-faint)" }}>
            Tap the microphone or type your legal question below.
          </p>
        )}
        <AnimatePresence initial={false}>
          {state.chatHistory.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-line ${
                  msg.role === "user" ? "rounded-br-sm" : "rounded-bl-sm border-l-2"
                }`}
                style={
                  msg.role === "user"
                    ? { background: "var(--color-accent-dim)", color: "var(--color-accent)" }
                    : {
                        background: "var(--color-surface)",
                        borderColor: "var(--color-primary)",
                        color: "var(--color-text)",
                        border: "1px solid var(--color-border)",
                        borderLeft: "3px solid var(--color-primary)",
                      }
                }
              >
                {msg.text}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing indicator */}
        {isProcessing && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
            <div
              className="rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2"
              style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
            >
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ background: "var(--color-primary)" }}
                  animate={{ y: [0, -4, 0] }}
                  transition={{ repeat: Infinity, duration: 0.7, delay: i * 0.15 }}
                />
              ))}
              {statusText && (
                <span className="text-xs ml-2" style={{ color: "var(--color-text-faint)" }}>
                  {statusText}
                </span>
              )}
            </div>
          </motion.div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Transcript display */}
      {lastTranscript && (
        <div
          className="rounded-xl px-3 py-2 text-xs"
          style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
        >
          <span style={{ color: "var(--color-text-faint)" }}>{labels.youSaid}: </span>
          <span style={{ color: "var(--color-text)" }}>&ldquo;{lastTranscript}&rdquo;</span>
        </div>
      )}

      {/* Category picker for unknown scenarios or empty guidance */}
      {lastResponse && (lastResponse.scenario === "unknown" || !lastResponse.guidance) && (
        <CategoryPicker onSelect={sendQuery} disabled={isProcessing} labels={labels} />
      )}

      {/* Structured Response Card (below chat, above mic) */}
      {lastResponse && lastResponse.scenario !== "empty" && lastResponse.scenario !== "unknown" && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl p-4 flex flex-col gap-3"
          style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
        >
          {/* Title + Severity */}
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm" style={{ color: "var(--color-primary)" }}>
              {lastResponse.title}
            </h3>
            <SeverityBadge severity={lastResponse.severity} />
          </div>

          {/* Outcome prediction */}
          {lastResponse.outcome && (
            <div
              className="rounded-xl px-3 py-2 text-xs"
              style={{ background: "var(--color-primary-dim)", border: "1px solid rgba(167,139,250,0.2)" }}
            >
              <span className="font-semibold" style={{ color: "var(--color-primary)" }}>
                {labels.likelyOutcome}:{" "}
              </span>
              <span style={{ color: "var(--color-text)" }}>{lastResponse.outcome}</span>
            </div>
          )}

          {/* Sections chips */}
          {lastResponse.sections.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {lastResponse.sections.map((s, i) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium"
                  style={{
                    background: "var(--color-secondary-dim)",
                    color: "var(--color-secondary)",
                    border: "1px solid rgba(232,180,184,0.2)",
                  }}
                >
                  {s}
                </span>
              ))}
            </div>
          )}

          {/* Complaint draft toggle */}
          {lastResponse.complaint_draft && (
            <div>
              <button
                onClick={() => setShowComplaint((prev) => !prev)}
                className="text-xs font-medium px-3 py-1.5 rounded-full transition-colors"
                style={{
                  background: "var(--color-accent-dim)",
                  color: "var(--color-accent)",
                  border: "1px solid rgba(129,140,248,0.25)",
                }}
              >
                {showComplaint ? labels.hideComplaint : labels.viewComplaint}
              </button>
              <AnimatePresence>
                {showComplaint && (
                  <motion.pre
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="mt-2 text-xs leading-relaxed whitespace-pre-wrap rounded-xl p-3 overflow-hidden"
                    style={{
                      background: "rgba(0,0,0,0.3)",
                      color: "var(--color-text)",
                      border: "1px solid var(--color-border)",
                    }}
                  >
                    {lastResponse.complaint_draft}
                  </motion.pre>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Emergency call button for critical/high severity */}
          {(lastResponse.severity === "critical" || lastResponse.severity === "high") && lastResponse.helplines.length > 0 && (() => {
            const num = parseHelplineNumber(lastResponse.helplines[0]);
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
                <span className="text-lg">📞</span> {labels.call} {lastResponse.helplines[0]}
              </a>
            ) : null;
          })()}

          {/* Helplines */}
          {lastResponse.helplines.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {lastResponse.helplines.map((h, i) => {
                const num = parseHelplineNumber(h);
                return num ? (
                  <a
                    key={i}
                    href={`tel:${num}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wide"
                    style={{
                      background: "rgba(239,68,68,0.15)",
                      color: "#ef4444",
                      border: "1px solid rgba(239,68,68,0.25)",
                    }}
                  >
                    📞 {h}
                  </a>
                ) : (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wide"
                    style={{
                      background: "rgba(239,68,68,0.15)",
                      color: "#ef4444",
                      border: "1px solid rgba(239,68,68,0.25)",
                    }}
                  >
                    {h}
                  </span>
                );
              })}
            </div>
          )}

          {/* Language badge + Source label */}
          <div className="flex items-center justify-between">
            {lastResponse.response_language && lastResponse.response_language !== "en-IN" ? (
              <span
                className="px-2 py-0.5 rounded-full text-[9px] font-semibold"
                style={{ background: "var(--color-primary-dim)", color: "var(--color-primary)", border: "1px solid rgba(167,139,250,0.2)" }}
              >
                {labels.respondedIn} {LANG_LABELS[lastResponse.response_language] || lastResponse.response_language}
              </span>
            ) : <span />}
            <span className="text-[10px] uppercase tracking-widest" style={{ color: "var(--color-text-faint)" }}>
              {labels.source}: {lastResponse.source === "classifier" ? labels.verifiedDb : labels.keywordSearch}
            </span>
          </div>
        </motion.div>
      )}

      {/* Microphone */}
      <div className="flex flex-col items-center gap-3">
        <button
          onClick={handleMicClick}
          disabled={isProcessing}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
          aria-pressed={isRecording}
          className="relative focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400 rounded-full disabled:opacity-50"
        >
          {isRecording && (
            <>
              <motion.span
                className="absolute inset-0 rounded-full opacity-25"
                style={{ background: "var(--color-accent)" }}
                animate={{ scale: [1, 1.6, 1] }}
                transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
              />
              <motion.span
                className="absolute inset-0 rounded-full opacity-15"
                style={{ background: "var(--color-accent)" }}
                animate={{ scale: [1, 2, 1] }}
                transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut", delay: 0.3 }}
              />
            </>
          )}
          <span
            className="relative flex items-center justify-center w-16 h-16 rounded-full text-3xl transition-colors duration-200"
            style={
              isRecording
                ? { background: "var(--color-accent)", boxShadow: "0 0 30px rgba(129,140,248,0.4)" }
                : { background: "var(--color-primary-dim)", border: "1px solid var(--color-primary)" }
            }
          >
            🎤
          </span>
        </button>
        <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
          {isRecording
            ? labels.recording
            : isProcessing
              ? statusText || labels.processing
              : error
                ? error
                : labels.tapMic}
        </span>

        {/* Waveform bars when recording */}
        {isRecording && (
          <div className="flex items-end gap-1 h-6">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="waveform-bar" style={{ height: "100%" }} />
            ))}
          </div>
        )}
      </div>

      {/* Text input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder={labels.typeQuestion}
          disabled={isProcessing}
          className="flex-1 px-4 py-2.5 rounded-full text-sm outline-none transition-colors disabled:opacity-50"
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            color: "var(--color-text)",
          }}
        />
        <button
          onClick={handleSend}
          disabled={!textInput.trim() || isProcessing}
          className="px-5 py-2.5 rounded-full text-sm font-medium transition-colors disabled:opacity-40"
          style={{
            background: "var(--color-primary-dim)",
            border: "1px solid var(--color-primary)",
            color: "var(--color-primary)",
          }}
        >
          {labels.send}
        </button>
      </div>

      <p className="text-xs text-center" style={{ color: "var(--color-text-faint)" }}>
        {labels.disclaimer}
      </p>
    </div>
  );
}
