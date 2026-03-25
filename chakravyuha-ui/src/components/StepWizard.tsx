"use client";

import React, { createContext, useContext, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";

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
      className={`flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium transition-all duration-200
        focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400
        ${isActive
          ? "bg-orange-100 border border-orange-300 text-gray-800 shadow-sm"
          : isDone
          ? "bg-green-50 border border-green-200 text-green-700"
          : "bg-gray-50 border border-gray-200 text-gray-500 hover:bg-gray-100"
        }`}
    >
      <motion.span
        layout
        className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0
          ${isActive
            ? "bg-orange-500 text-white"
            : isDone
            ? "bg-green-500 text-white"
            : "bg-gray-300 text-gray-600"
          }`}
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
