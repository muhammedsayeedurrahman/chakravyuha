"use client";

import React from "react";
import { motion } from "framer-motion";

// ── Sub-components ────────────────────────────────────────────────────────────

function CardHeader({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`px-6 pt-6 pb-3 border-b ${className}`} style={{ borderColor: "var(--color-border)" }}>
      {children}
    </div>
  );
}

function CardBody({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`px-6 py-5 ${className}`}>{children}</div>
  );
}

// ── Root Card component ────────────────────────────────────────────────────────

interface CardProps {
  children: React.ReactNode;
  className?: string;
  animate?: boolean;
}

/**
 * Card – Composable card component using Composition over Inheritance.
 * Attach sub-components as: <Card.Header> and <Card.Body>.
 */
function Card({ children, className = "", animate = true }: CardProps) {
  const Tag = animate ? motion.div : "div";
  const animProps = animate
    ? {
        initial: { opacity: 0, y: 16 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.4, ease: "easeOut" },
      }
    : {};

  return (
    <Tag
      className={`glass rounded-2xl overflow-hidden ${className}`}
      {...(animProps as object)}
    >
      {children}
    </Tag>
  );
}

Card.Header = CardHeader;
Card.Body = CardBody;

export { Card };
