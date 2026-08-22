"use client";

import React, { createContext, useContext, useMemo } from "react";
import { motion } from "framer-motion";

// ── Compound Component Context ────────────────────────────────────────────────

interface StepWizardContextValue {
  currentStep: number;
  totalSteps: number;
  setStep: (step: number) => void;
}

const StepWizardContext = createContext<StepWizardContextValue | null>(null);

function useStepWizardContext() {
  const ctx = useContext(StepWizardContext);
  if (!ctx) throw new Error("StepWizard sub-components must be inside <StepWizard>");
  return ctx;
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface StepProps {
  stepNumber: number;
  label: string;
}

function Step({ stepNumber, label }: StepProps) {
  const { currentStep, setStep } = useStepWizardContext();
  const isActive = currentStep === stepNumber;
  const isDone = currentStep > stepNumber;

  return (
    <button
      onClick={() => setStep(stepNumber)}
      aria-label={`Step ${stepNumber}: ${label}`}
      aria-current={isActive ? "step" : undefined}
      className="flex items-center gap-2 rounded-2xl px-3 py-2.5 text-xs font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
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
        className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold"
        style={{
          background: isActive ? "var(--color-primary)" : isDone ? "#22c55e" : "var(--color-border)",
          color: isActive || isDone ? "#fff" : "var(--color-text-muted)",
        }}
      >
        {isDone ? "✓" : stepNumber}
      </motion.span>
      <span>{label}</span>
    </button>
  );
}

// ── Root StepWizard component ─────────────────────────────────────────────────

interface StepWizardProps {
  currentStep: number;
  totalSteps: number;
  setStep: (step: number) => void;
  children: React.ReactNode;
}

/**
 * StepWizard – Compound component pattern where all children share wizard state
 * through context. Child <StepWizard.Step> components auto-connect to the context.
 */
function StepWizard({ currentStep, totalSteps, setStep, children }: StepWizardProps) {
  const value = useMemo(
    () => ({ currentStep, totalSteps, setStep }),
    [currentStep, totalSteps, setStep]
  );

  return (
    <StepWizardContext.Provider value={value}>
      <div className="flex flex-wrap gap-3" role="list" aria-label="Step progress">
        {children}
      </div>
    </StepWizardContext.Provider>
  );
}

StepWizard.Step = Step;

export { StepWizard };
export type { StepProps };
