"use client";

import { motion } from "framer-motion";
import { useApp } from "@/context/AppContext";

const STEPS_EN = [
  "Tell us your problem",
  "Understand the law",
  "Take action",
  "Fill forms",
  "How it works",
];

const STEPS_TA = [
  "\u0B89\u0B99\u0BCD\u0B95\u0BB3\u0BCD \u0BAA\u0BBF\u0BB0\u0B9A\u0BCD\u0B9A\u0BBF\u0BA9\u0BC8\u0B9A\u0BCD \u0B9A\u0BCA\u0BB2\u0BCD\u0BB2\u0BC1\u0B99\u0BCD\u0B95\u0BB3\u0BCD",
  "\u0B9A\u0B9F\u0BCD\u0B9F\u0BA4\u0BCD\u0BA4\u0BC8\u0BAA\u0BCD \u0BAA\u0BC1\u0BB0\u0BBF\u0BA8\u0BCD\u0BA4\u0BC1\u0B95\u0BCA\u0BB3\u0BCD\u0BB3\u0BC1\u0B99\u0BCD\u0B95\u0BB3\u0BCD",
  "\u0BA8\u0B9F\u0BB5\u0B9F\u0BBF\u0B95\u0BCD\u0B95\u0BC8 \u0B8E\u0B9F\u0BC1\u0B95\u0BCD\u0B95\u0BB5\u0BC1\u0BAE\u0BCD",
  "\u0BAA\u0B9F\u0BBF\u0BB5\u0B99\u0BCD\u0B95\u0BB3\u0BC8 \u0BA8\u0BBF\u0BB0\u0BAA\u0BCD\u0BAA\u0BB5\u0BC1\u0BAE\u0BCD",
  "\u0B87\u0BA4\u0BC1 \u0B8E\u0BB5\u0BCD\u0BB5\u0BBE\u0BB1\u0BC1 \u0B9A\u0BC6\u0BAF\u0BB2\u0BCD\u0BAA\u0B9F\u0BC1\u0B95\u0BBF\u0BB1\u0BA4\u0BC1",
];

export function GuidedStepsCard() {
  const { state, setStep } = useApp();
  const isTamil = state.language.code === "ta-IN";
  const steps = isTamil ? STEPS_TA : STEPS_EN;

  return (
    <div className="flex flex-wrap gap-3">
      {steps.map((label, idx) => {
        const stepNum = idx + 1;
        const isActive = state.currentStep === stepNum;
        const isDone = state.currentStep > stepNum;

        return (
          <button
            key={stepNum}
            onClick={() => setStep(stepNum)}
            aria-label={`Step ${stepNum}: ${label}`}
            aria-current={isActive ? "step" : undefined}
            className="flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2"
            style={{
              background: isActive
                ? "var(--color-primary-dim)"
                : isDone
                ? "rgba(34,197,94,0.1)"
                : "var(--color-surface)",
              border: `1px solid ${
                isActive
                  ? "rgba(167,139,250,0.4)"
                  : isDone
                  ? "rgba(34,197,94,0.3)"
                  : "var(--color-border)"
              }`,
              color: isActive
                ? "var(--color-primary)"
                : isDone
                ? "#22c55e"
                : "var(--color-text-muted)",
            }}
          >
            <motion.span
              layout
              className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{
                background: isActive
                  ? "var(--color-primary)"
                  : isDone
                  ? "#22c55e"
                  : "var(--color-border)",
                color: isActive || isDone ? "#ffffff" : "var(--color-text-muted)",
              }}
            >
              {isDone ? "\u2713" : stepNum}
            </motion.span>
            <span>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
