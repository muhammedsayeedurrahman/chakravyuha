"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/Card";
import type { CivicJourney } from "@/components/CivicAssistant";

interface LawSectionProps {
  onOpenDraft: () => void;
  onOpenFile: (portal?: string) => void;
  onOpenCivic: (journey: CivicJourney) => void;
  onAutoFlow: () => void;
}

const QUICK_ACTIONS = [
  {
    label: "Draft an RTI",
    description: "Request government records",
    icon: "📄",
    action: "civic_rti" as const,
  },
  {
    label: "Check Schemes",
    description: "Explainable eligibility",
    icon: "🏛️",
    action: "civic_schemes" as const,
  },
  {
    label: "Prepare CPGRAMS",
    description: "Draft, review, then proceed",
    icon: "📮",
    action: "civic_cpgrams" as const,
  },
  {
    label: "Rights Navigator",
    description: "Consumer, tenant, workplace",
    icon: "🧭",
    action: "civic_rights" as const,
  },
  {
    label: "Generate Complaint",
    description: "Draft FIR / legal notice",
    icon: "\uD83D\uDCDD",
    action: "draft" as const,
  },
  {
    label: "Apply Duplicate License",
    description: "Continue to assisted filing",
    icon: "\uD83D\uDE97",
    action: "file_mparivahan" as const,
  },
];

const YOUR_RIGHTS = [
  {
    title: "Legal-aid pathway",
    description: "Legal-services institutions may provide assistance subject to eligibility. Verify the current service and requirements.",
    icon: "\u2696\uFE0F",
  },
  {
    title: "Reporting an offence",
    description: "Police procedure depends on the alleged facts and whether they disclose a cognizable offence. Get case-specific help if a report is refused.",
    icon: "\uD83D\uDCCB",
  },
  {
    title: "Bail information",
    description: "The applicable process depends on the offence classification, court, and circumstances. Verify it for the specific case.",
    icon: "\uD83D\uDD13",
  },
];

export function LawSection({ onOpenDraft, onOpenFile, onOpenCivic, onAutoFlow }: LawSectionProps) {
  const handleAction = (action: string) => {
    switch (action) {
      case "draft":
        onOpenDraft();
        break;
      case "file_mparivahan":
        onOpenFile("mparivahan");
        break;
      case "civic_rti":
        onOpenCivic("rti");
        break;
      case "civic_schemes":
        onOpenCivic("schemes");
        break;
      case "civic_cpgrams":
        onOpenCivic("cpgrams");
        break;
      case "civic_rights":
        onOpenCivic("rights");
        break;
    }
  };

  return (
    <div className="flex flex-col gap-5 px-4">
      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
      >
        <h2
          className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: "var(--color-text-faint)" }}
        >
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {QUICK_ACTIONS.map((item) => (
            <button
              key={item.label}
              onClick={() => handleAction(item.action)}
              className="flex items-center gap-3 p-3.5 rounded-2xl text-left transition-all hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
              }}
            >
              <span className="text-2xl">{item.icon}</span>
              <div>
                <p className="text-sm font-semibold" style={{ color: "var(--color-text)" }}>
                  {item.label}
                </p>
                <p className="text-[10px]" style={{ color: "var(--color-text-faint)" }}>
                  {item.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Your Rights */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
      >
        <h2
          className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: "var(--color-text-faint)" }}
        >
          Common pathways — verify details
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {YOUR_RIGHTS.map((right) => (
            <div
              key={right.title}
              className="p-3.5 rounded-2xl"
              style={{
                background: "var(--color-primary-dim)",
                border: "1px solid rgba(167, 139, 250, 0.15)",
              }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span>{right.icon}</span>
                <p className="text-sm font-semibold" style={{ color: "var(--color-primary)" }}>
                  {right.title}
                </p>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
                {right.description}
              </p>
            </div>
          ))}
        </div>
      </motion.div>

      {/* Emergency orientation */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <h2
          className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: "var(--color-text-faint)" }}
        >
          Immediate safety
        </h2>
        <div className="rounded-2xl p-3.5 text-xs leading-relaxed" style={{ background: "rgba(239,68,68,0.1)", color: "var(--color-text-muted)", border: "1px solid rgba(239,68,68,0.25)" }}>
          If someone is in immediate danger, contact the official emergency service available in their location. Verify any specialist helpline through the relevant government authority before relying on it.
        </div>
      </motion.div>

      {/* Auto Legal Agent CTA */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.4 }}
      >
        <Card>
          <Card.Body>
            <button
              onClick={onAutoFlow}
              className="w-full flex flex-col items-center gap-2 py-4 rounded-2xl transition-all hover:scale-[1.01] active:scale-[0.99]"
              style={{
                background: "linear-gradient(135deg, rgba(167, 139, 250, 0.15), rgba(129, 140, 248, 0.08))",
                border: "1px solid var(--color-primary)",
              }}
            >
              <span className="text-3xl">{"\uD83E\uDD16"}</span>
              <p className="text-sm font-bold" style={{ color: "var(--color-primary)" }}>
                Auto Legal Agent
              </p>
              <p className="text-xs max-w-xs text-center" style={{ color: "var(--color-text-muted)" }}>
                Describe your issue for guided classification, source-aware guidance, and a reviewed next step
              </p>
            </button>
          </Card.Body>
        </Card>
      </motion.div>
    </div>
  );
}
