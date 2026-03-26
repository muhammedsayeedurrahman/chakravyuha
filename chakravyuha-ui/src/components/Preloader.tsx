"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Logo } from "@/components/Logo";

interface PreloaderProps {
  onComplete: () => void;
}

export function Preloader({ onComplete }: PreloaderProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onComplete, 500); // wait for exit animation
    }, 2000);
    return () => clearTimeout(timer);
  }, [onComplete]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="preloader"
          exit={{ opacity: 0, scale: 1.05 }}
          transition={{ duration: 0.5, ease: "easeIn" }}
        >
          {/* Pulsing logo */}
          <motion.div
            className="preloader-logo"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: [0.34, 1.56, 0.64, 1] }}
          >
            <Logo size={80} />
          </motion.div>

          {/* Brand */}
          <motion.div
            className="text-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
          >
            <h1
              className="text-2xl font-bold gradient-text-hero"
              style={{ fontFamily: "var(--font-playfair)" }}
            >
              LEXARO.AI
            </h1>
            <p className="text-xs tracking-[0.2em] mt-1" style={{ color: "var(--color-text-faint)" }}>
              LEGAL HELP. SIMPLIFIED. LOCALIZED.
            </p>
          </motion.div>

          {/* Loading bar */}
          <div
            className="w-[200px] h-[2px] rounded-full overflow-hidden"
            style={{ background: "var(--color-border)" }}
          >
            <div className="preloader-bar" />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
