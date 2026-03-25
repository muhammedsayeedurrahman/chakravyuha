"use client";

import { motion, AnimatePresence } from "framer-motion";

interface CurtainTransitionProps {
  show: boolean;
}

export function CurtainTransition({ show }: CurtainTransitionProps) {
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="fixed inset-0 z-[100] pointer-events-none"
          style={{
            background: "linear-gradient(135deg, var(--color-bg) 0%, var(--color-bg-2) 100%)",
          }}
          initial={{ y: "100%" }}
          animate={{ y: "0%" }}
          exit={{ y: "-100%" }}
          transition={{
            duration: 0.6,
            ease: [0.65, 0, 0.35, 1],
          }}
        />
      )}
    </AnimatePresence>
  );
}
