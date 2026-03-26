"use client";

import { motion } from "framer-motion";
import { Card } from "@/components/Card";

interface LawSectionProps {
  onOpenDraft: () => void;
  onOpenFile: (portal?: string) => void;
  onAutoFlow: () => void;
}

const QUICK_ACTIONS = [
  {
    label: "Generate Complaint",
    description: "Draft FIR / legal notice",
    icon: "\uD83D\uDCDD",
    action: "draft" as const,
  },
  {
    label: "Apply Duplicate License",
    description: "mParivahan portal",
    icon: "\uD83D\uDE97",
    action: "file_mparivahan" as const,
  },
  {
    label: "File Consumer Complaint",
    description: "Consumer Helpline",
    icon: "\uD83D\uDED2",
    action: "file_consumer" as const,
  },
];

const YOUR_RIGHTS = [
  {
    title: "Right to Legal Aid",
    description: "Free lawyer via NALSA. Call 15100.",
    icon: "\u2696\uFE0F",
  },
  {
    title: "Right to FIR",
    description: "Police MUST register your FIR under law.",
    icon: "\uD83D\uDCCB",
  },
  {
    title: "Right to Bail",
    description: "Bailable offenses allow immediate bail.",
    icon: "\uD83D\uDD13",
  },
];

const EMERGENCY_NUMBERS = [
  { label: "112 Emergency", number: "112", color: "#ef4444" },
  { label: "1091 Women Helpline", number: "1091", color: "#f59e0b" },
];

export function LawSection({ onOpenDraft, onOpenFile, onAutoFlow }: LawSectionProps) {
  const handleAction = (action: string) => {
    switch (action) {
      case "draft":
        onOpenDraft();
        break;
      case "file_mparivahan":
        onOpenFile("mparivahan");
        break;
      case "file_consumer":
        onOpenFile("consumer_helpline");
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
          Your Rights
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

      {/* Emergency */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
      >
        <h2
          className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: "var(--color-text-faint)" }}
        >
          Emergency
        </h2>
        <div className="flex gap-3">
          {EMERGENCY_NUMBERS.map((em) => (
            <a
              key={em.number}
              href={`tel:${em.number}`}
              className="flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-bold tracking-wide transition-all hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: `${em.color}20`,
                color: em.color,
                border: `1px solid ${em.color}40`,
              }}
            >
              {"📞"} {em.label}
            </a>
          ))}
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
                Describe your issue — AI handles the rest
              </p>
            </button>
          </Card.Body>
        </Card>
      </motion.div>
    </div>
  );
}
