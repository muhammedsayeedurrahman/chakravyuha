"use client";

import { motion, useMotionValue, useTransform } from "framer-motion";
import { useRef, useCallback } from "react";

const FEATURES = [
  {
    icon: "\uD83C\uDFA4",
    title: "Voice AI",
    desc: "Speak your legal concern in any Indian language \u2014 instant classification",
    accent: "violet",
  },
  {
    icon: "\u2696\uFE0F",
    title: "AI Judge",
    desc: "Predict likely outcomes and severity of your legal situation",
    accent: "rose",
  },
  {
    icon: "\uD83D\uDCDD",
    title: "Draft Complaints",
    desc: "Auto-generate FIR drafts, legal notices, and consumer complaints",
    accent: "indigo",
  },
  {
    icon: "\uD83D\uDCDC",
    title: "BNS & IPC Guide",
    desc: "Navigate Bhartiya Nyaya Sanhita sections with curated guidance",
    accent: "violet",
  },
  {
    icon: "\uD83D\uDEE1\uFE0F",
    title: "Safe Responses",
    desc: "Classification-first pipeline \u2014 zero hallucinations, verified legal info",
    accent: "rose",
  },
  {
    icon: "\uD83D\uDDE3\uFE0F",
    title: "22 Languages",
    desc: "Hindi, Tamil, Bengali, Telugu, Marathi, Gujarati, and more",
    accent: "indigo",
  },
];

const ACCENT_STYLES: Record<string, { bg: string; border: string; hover: string }> = {
  violet: {
    bg: "var(--color-primary-dim)",
    border: "rgba(167, 139, 250, 0.25)",
    hover: "rgba(167, 139, 250, 0.5)",
  },
  rose: {
    bg: "var(--color-secondary-dim)",
    border: "rgba(232, 180, 184, 0.25)",
    hover: "rgba(232, 180, 184, 0.5)",
  },
  indigo: {
    bg: "var(--color-accent-dim)",
    border: "rgba(129, 140, 248, 0.25)",
    hover: "rgba(129, 140, 248, 0.5)",
  },
};

/** 3D tilt card wrapper */
function TiltCard({
  children,
  className,
  style,
  delay,
}: {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  delay: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const rotateX = useMotionValue(0);
  const rotateY = useMotionValue(0);
  const brightness = useTransform(rotateY, [-15, 15], [0.95, 1.05]);

  const handleMove = useCallback(
    (e: React.MouseEvent) => {
      if (!ref.current) return;
      const rect = ref.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      rotateY.set(((x - centerX) / centerX) * 12);
      rotateX.set(((centerY - y) / centerY) * 12);
    },
    [rotateX, rotateY]
  );

  const handleLeave = useCallback(() => {
    rotateX.set(0);
    rotateY.set(0);
  }, [rotateX, rotateY]);

  return (
    <motion.div
      ref={ref}
      className={className}
      style={{
        ...style,
        rotateX,
        rotateY,
        filter: useTransform(brightness, (v) => `brightness(${v})`),
        transformPerspective: 800,
        transformStyle: "preserve-3d",
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      whileHover={{ scale: 1.03 }}
    >
      {children}
    </motion.div>
  );
}

export function FeatureGrid() {
  return (
    <section className="grid grid-cols-2 sm:grid-cols-3 gap-3 px-4">
      {FEATURES.map((f, i) => {
        const accent = ACCENT_STYLES[f.accent];
        return (
          <TiltCard
            key={f.title}
            className="glass rounded-2xl p-4 flex flex-col items-center text-center gap-2.5 cursor-default transition-colors"
            style={{ borderColor: accent.border }}
            delay={0.2 + i * 0.08}
          >
            <div
              className="w-11 h-11 rounded-full flex items-center justify-center text-xl"
              style={{ background: accent.bg, border: `1px solid ${accent.border}` }}
            >
              {f.icon}
            </div>
            <h3 className="font-semibold text-xs" style={{ color: "var(--color-text)" }}>
              {f.title}
            </h3>
            <p className="text-[10px] leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
              {f.desc}
            </p>
          </TiltCard>
        );
      })}
    </section>
  );
}
