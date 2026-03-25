"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { smartQuery, type SmartResponse } from "@/services/api";

// ── Demo card configuration ────────────────────────────────────────────────

interface DemoConfig {
  id: string;
  icon: string;
  title: string;
  subtitle: string;
  query: string;
  lang: string;
  accent: "violet" | "indigo" | "red";
  responseLangLabel: string;
}

const DEMOS: readonly DemoConfig[] = [
  {
    id: "tamil",
    icon: "\uD83C\uDDEE\uD83C\uDDF3",
    title: "\u0BA4\u0BAE\u0BBF\u0BB4\u0BBF\u0BB2\u0BCD \u0B95\u0BC7\u0BB3\u0BC1\u0B99\u0BCD\u0B95\u0BB3\u0BCD",
    subtitle: "Ask in Tamil",
    query: "\u0B8E\u0BA9\u0BCD \u0B89\u0BB0\u0BBF\u0BAE\u0BAE\u0BCD \u0BA4\u0BCA\u0BB2\u0BC8\u0BA8\u0BCD\u0BA4\u0BC1 \u0BB5\u0BBF\u0B9F\u0BCD\u0B9F\u0BA4\u0BC1",
    lang: "ta-IN",
    accent: "violet",
    responseLangLabel: "\u0BA4\u0BAE\u0BBF\u0BB4\u0BCD",
  },
  {
    id: "hindi",
    icon: "\uD83C\uDDEE\uD83C\uDDF3",
    title: "\u0939\u093F\u0928\u094D\u0926\u0940 \u092E\u0947\u0902 \u092A\u0942\u0926\u0947\u0902",
    subtitle: "Ask in Hindi",
    query: "\u092E\u0947\u0930\u093E \u0932\u093E\u0907\u0938\u0947\u0902\u0938 \u0916\u094B \u0917\u092F\u093E \u0939\u0948",
    lang: "hi-IN",
    accent: "indigo",
    responseLangLabel: "\u0939\u093F\u0928\u094D\u0926\u0940",
  },
  {
    id: "sos",
    icon: "\uD83D\uDEA8",
    title: "Emergency SOS",
    subtitle: "Instant escalation",
    query: "I am facing domestic violence",
    lang: "en-IN",
    accent: "red",
    responseLangLabel: "English",
  },
] as const;

const ACCENT_MAP = {
  violet: {
    bg: "var(--color-primary-dim)",
    border: "rgba(167, 139, 250, 0.25)",
    color: "var(--color-primary)",
    glow: "0 0 30px rgba(167, 139, 250, 0.2)",
    btnBg: "rgba(167, 139, 250, 0.15)",
    btnBorder: "rgba(167, 139, 250, 0.4)",
  },
  indigo: {
    bg: "var(--color-accent-dim)",
    border: "rgba(129, 140, 248, 0.25)",
    color: "var(--color-accent)",
    glow: "0 0 30px rgba(129, 140, 248, 0.2)",
    btnBg: "rgba(129, 140, 248, 0.15)",
    btnBorder: "rgba(129, 140, 248, 0.4)",
  },
  red: {
    bg: "rgba(239, 68, 68, 0.12)",
    border: "rgba(239, 68, 68, 0.25)",
    color: "#ef4444",
    glow: "0 0 30px rgba(239, 68, 68, 0.2)",
    btnBg: "rgba(239, 68, 68, 0.15)",
    btnBorder: "rgba(239, 68, 68, 0.4)",
  },
} as const;

// ── Typewriter hook ─────────────────────────────────────────────────────────

function useTypewriter(text: string, active: boolean, speed = 30): string {
  const [displayed, setDisplayed] = useState("");

  useEffect(() => {
    if (!active || !text) {
      if (!active) setDisplayed("");
      return;
    }

    setDisplayed("");
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(timer);
    }, speed);

    return () => clearInterval(timer);
  }, [text, active, speed]);

  return displayed;
}

// ── DemoCard ────────────────────────────────────────────────────────────────

type CardState = "idle" | "loading" | "result" | "error";

function DemoCard({ config, index }: { config: DemoConfig; index: number }) {
  const [state, setState] = useState<CardState>("idle");
  const [response, setResponse] = useState<SmartResponse | null>(null);
  const [error, setError] = useState<string>("");
  const accent = ACCENT_MAP[config.accent];

  const guidanceText = response?.guidance ?? "";
  const typedGuidance = useTypewriter(guidanceText, state === "result");

  const handleClick = useCallback(async () => {
    if (state === "loading") return;
    setState("loading");
    setResponse(null);
    setError("");

    try {
      const res = await smartQuery(config.query, config.lang);
      setResponse(res);
      setState("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setState("error");
    }
  }, [config.query, config.lang, state]);

  const handleReset = useCallback(() => {
    setState("idle");
    setResponse(null);
    setError("");
  }, []);

  const isEmergency = config.id === "sos";

  return (
    <motion.div
      className="glass rounded-2xl overflow-hidden relative"
      style={{
        borderColor: accent.border,
        ...(isEmergency && state !== "idle"
          ? { animation: "sos-pulse 2s ease-in-out infinite" }
          : {}),
      }}
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 + index * 0.1, duration: 0.5, ease: "easeOut" }}
      whileHover={state === "idle" ? { scale: 1.01, boxShadow: accent.glow } : {}}
    >
      {/* Shimmer overlay during loading */}
      <AnimatePresence>
        {state === "loading" && (
          <motion.div
            className="absolute inset-0 z-10 pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              background:
                "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.06) 50%, transparent 100%)",
              backgroundSize: "200% 100%",
              animation: "shimmer 1.5s linear infinite",
            }}
          />
        )}
      </AnimatePresence>

      {/* Success border burst */}
      <AnimatePresence>
        {state === "result" && (
          <motion.div
            className="absolute inset-0 rounded-2xl pointer-events-none z-0"
            initial={{ boxShadow: `0 0 0px ${accent.color}`, opacity: 1 }}
            animate={{ boxShadow: `0 0 60px ${accent.color}`, opacity: 0 }}
            transition={{ duration: 0.8 }}
          />
        )}
      </AnimatePresence>

      <div className="relative z-[1] p-5">
        {/* Header row */}
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-11 h-11 rounded-full flex items-center justify-center text-xl shrink-0"
            style={{ background: accent.bg, border: `1px solid ${accent.border}` }}
          >
            {config.icon}
          </div>
          <div className="min-w-0">
            <h3 className="font-bold text-sm truncate" style={{ color: "var(--color-text)" }}>
              {config.title}
            </h3>
            <p className="text-[11px]" style={{ color: "var(--color-text-muted)" }}>
              {config.subtitle}
            </p>
          </div>
        </div>

        {/* Query preview */}
        <p
          className="text-xs mb-4 leading-relaxed"
          style={{ color: "var(--color-text-muted)", fontStyle: "italic" }}
        >
          &ldquo;{config.query}&rdquo;
        </p>

        {/* ── Idle state ─────────────────────────────────────────── */}
        {state === "idle" && (
          <motion.button
            onClick={handleClick}
            className="w-full py-2.5 rounded-xl text-xs font-semibold tracking-wide uppercase cursor-pointer transition-colors"
            style={{
              background: accent.btnBg,
              border: `1px solid ${accent.btnBorder}`,
              color: accent.color,
            }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Try Demo
          </motion.button>
        )}

        {/* ── Loading state ──────────────────────────────────────── */}
        {state === "loading" && (
          <div className="flex items-center gap-3 py-2">
            <motion.div
              className="w-5 h-5 rounded-full border-2 border-t-transparent"
              style={{ borderColor: accent.color, borderTopColor: "transparent" }}
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 0.8, ease: "linear" }}
            />
            <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
              Analyzing...
            </span>
          </div>
        )}

        {/* ── Error state ────────────────────────────────────────── */}
        {state === "error" && (
          <div className="space-y-2">
            <p className="text-xs text-red-400">{error}</p>
            <button
              onClick={handleReset}
              className="text-xs underline cursor-pointer"
              style={{ color: "var(--color-text-muted)" }}
            >
              Try again
            </button>
          </div>
        )}

        {/* ── Result state ───────────────────────────────────────── */}
        {state === "result" && response && (
          <motion.div
            className="space-y-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {/* Typewriter guidance */}
            <p className="text-xs leading-relaxed" style={{ color: "var(--color-text)" }}>
              {typedGuidance}
              {typedGuidance.length < guidanceText.length && (
                <span
                  className="inline-block w-[2px] h-3 ml-0.5 align-middle"
                  style={{
                    background: accent.color,
                    animation: "typewriter-cursor 0.6s step-end infinite",
                  }}
                />
              )}
            </p>

            {/* Section chips */}
            {response.sections.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {response.sections.slice(0, 3).map((s) => (
                  <span
                    key={s}
                    className="chip text-[10px]"
                    style={{ borderColor: accent.border, color: accent.color }}
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}

            {/* Language badge */}
            <motion.div
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-medium"
              style={{
                background: accent.bg,
                border: `1px solid ${accent.border}`,
                color: accent.color,
              }}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 400, damping: 15, delay: 0.2 }}
            >
              Responded in {config.responseLangLabel}
            </motion.div>

            {/* SOS call button */}
            {isEmergency && (
              <motion.a
                href="tel:1091"
                className="flex items-center justify-center gap-2 w-full py-3 rounded-xl text-sm font-bold tracking-wide uppercase no-underline"
                style={{
                  background: "rgba(239, 68, 68, 0.2)",
                  border: "1px solid rgba(239, 68, 68, 0.5)",
                  color: "#ef4444",
                  animation: "sos-pulse 1.5s ease-in-out infinite",
                }}
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ type: "spring", stiffness: 300, damping: 20, delay: 0.3 }}
              >
                <span className="text-lg">📞</span>
                CALL 1091
              </motion.a>
            )}

            {/* Reset */}
            <button
              onClick={handleReset}
              className="text-[10px] underline cursor-pointer opacity-50 hover:opacity-80 transition-opacity"
              style={{ color: "var(--color-text-muted)" }}
            >
              Reset demo
            </button>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

// ── DemoShowcase section ────────────────────────────────────────────────────

export function DemoShowcase() {
  return (
    <section className="px-4 space-y-4">
      {/* Section header */}
      <motion.div
        className="text-center"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h2 className="text-lg font-bold gradient-text-hero">See It In Action</h2>
        <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
          One-click demos — Tamil, Hindi, and Emergency SOS
        </p>
      </motion.div>

      {/* Demo cards */}
      <div className="grid gap-3 sm:grid-cols-3">
        {DEMOS.map((demo, i) => (
          <DemoCard key={demo.id} config={demo} index={i} />
        ))}
      </div>
    </section>
  );
}
