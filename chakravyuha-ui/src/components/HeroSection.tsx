"use client";

import { motion, useMotionValue, useTransform } from "framer-motion";
import { HeroLogo } from "@/components/Logo";
import { useRef, useCallback } from "react";

const CHIPS = [
  { label: "BNS 2023", icon: "\u2696\uFE0F" },
  { label: "BNSS", icon: "\uD83D\uDCDC" },
  { label: "Constitution", icon: "\uD83C\uDDEE\uD83C\uDDF3" },
  { label: "NALSA", icon: "\uD83C\uDFDB\uFE0F" },
  { label: "22 Languages", icon: "\uD83D\uDDE3\uFE0F" },
  { label: "Voice AI", icon: "\uD83C\uDFA4" },
];

interface HeroSectionProps {
  onStartChat: () => void;
}

export function HeroSection({ onStartChat }: HeroSectionProps) {
  const btnRef = useRef<HTMLButtonElement>(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const btnTranslateX = useTransform(mouseX, [-200, 200], [-4, 4]);
  const btnTranslateY = useTransform(mouseY, [-200, 200], [-4, 4]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!btnRef.current) return;
      const rect = btnRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      mouseX.set(e.clientX - centerX);
      mouseY.set(e.clientY - centerY);
    },
    [mouseX, mouseY]
  );

  const handleMouseLeave = useCallback(() => {
    mouseX.set(0);
    mouseY.set(0);
  }, [mouseX, mouseY]);

  return (
    <section className="relative flex flex-col items-center text-center gap-6 pt-10 pb-6 px-4">
      {/* Animated logo with concentric rings */}
      <motion.div
        initial={{ opacity: 0, scale: 0.7 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, ease: [0.34, 1.56, 0.64, 1] }}
      >
        <HeroLogo />
      </motion.div>

      {/* Title with shimmer */}
      <motion.div
        className="flex flex-col gap-2"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
      >
        <h1
          className="text-4xl sm:text-5xl font-bold leading-tight"
          style={{ fontFamily: "var(--font-playfair)" }}
        >
          <span
            className="animate-text-shimmer"
            style={{
              background: "linear-gradient(90deg, #ffffff 0%, #a78bfa 25%, #e8b4b8 50%, #818cf8 75%, #ffffff 100%)",
              backgroundSize: "200% auto",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            CHAKRAVYUHA
          </span>
          <span className="gradient-text-violet">.AI</span>
        </h1>
        <p
          className="text-xs tracking-[0.3em] font-medium uppercase"
          style={{ color: "var(--color-secondary)" }}
        >
          Indian Law | Artificial Intelligence
        </p>
      </motion.div>

      {/* Description */}
      <motion.p
        className="text-sm max-w-sm leading-relaxed"
        style={{ color: "var(--color-text-muted)" }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.45 }}
      >
        Navigate the Indian Constitution, Bhartiya Nyaya Sanhita, and legal procedures
        with classification-first AI guidance — no hallucinations, in{" "}
        <span style={{ color: "var(--color-primary)" }}>22 regional languages</span>.
      </motion.p>

      {/* Magnetic CTA */}
      <motion.button
        ref={btnRef}
        onClick={onStartChat}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.55 }}
        whileHover={{ scale: 1.04 }}
        whileTap={{ scale: 0.97 }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          x: btnTranslateX,
          y: btnTranslateY,
          background: "linear-gradient(135deg, rgba(167, 139, 250, 0.25), rgba(129, 140, 248, 0.1))",
          border: "1px solid var(--color-primary)",
          color: "var(--color-primary)",
          boxShadow: "0 0 20px var(--color-primary-glow)",
        }}
        className="flex items-center gap-2 px-7 py-3 rounded-full text-sm font-semibold transition-shadow"
      >
        Start Legal Consultation
        <span aria-hidden>&#8594;</span>
      </motion.button>

      {/* Powered by */}
      <motion.p
        className="text-[10px] tracking-widest uppercase"
        style={{ color: "var(--color-text-faint)" }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
      >
        Classification-First &middot; Zero Hallucinations &middot; Official Legal Frameworks
      </motion.p>

      {/* Chips */}
      <motion.div
        className="flex flex-wrap justify-center gap-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.75 }}
      >
        {CHIPS.map((chip, i) => (
          <motion.span
            key={chip.label}
            className="chip"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.75 + i * 0.07 }}
          >
            {chip.icon} {chip.label}
          </motion.span>
        ))}
      </motion.div>
    </section>
  );
}
