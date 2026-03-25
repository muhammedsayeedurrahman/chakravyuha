"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useApp } from "@/context/AppContext";
import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";

export function Header() {
  const { state, setLanguage, supportedLanguages } = useApp();
  const [langOpen, setLangOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setLangOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") setLangOpen(false);
  };

  return (
    <header
      className="sticky top-0 z-50 flex items-center justify-between px-5 py-3.5"
      style={{
        background: "rgba(10, 10, 26, 0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--color-border)",
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5">
        <div className="relative">
          <div
            className="absolute inset-[-2px] rounded-full animate-spin-slow opacity-60"
            style={{
              background: "conic-gradient(from 0deg, #a78bfa, #e8b4b8, #818cf8, #a78bfa)",
            }}
          />
          <div
            className="relative rounded-full flex items-center justify-center"
            style={{ background: "var(--color-bg-2)" }}
          >
            <Logo size={38} />
          </div>
        </div>

        <div>
          <h1
            className="text-base font-bold leading-tight tracking-tight"
            style={{ color: "var(--color-text)", fontFamily: "var(--font-playfair)" }}
          >
            CHAKRAVYUHA
            <span className="gradient-text-violet text-xs font-normal ml-0.5">.AI</span>
          </h1>
          <p className="text-[9px] leading-none tracking-wider uppercase" style={{ color: "var(--color-text-faint)" }}>
            Indian Law | Artificial Intelligence
          </p>
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Theme Toggle */}
        <ThemeToggle />

        {/* Language Picker */}
        <div ref={dropdownRef} className="relative" onKeyDown={handleKeyDown}>
          <button
            onClick={() => setLangOpen((v) => !v)}
            aria-haspopup="listbox"
            aria-expanded={langOpen}
            className="flex items-center gap-1.5 text-xs rounded-full px-3 py-1.5 transition-all focus:outline-none"
            style={{
              border: "1px solid var(--color-border)",
              color: "var(--color-text-muted)",
              background: "var(--color-surface)",
            }}
          >
            <span style={{ color: "var(--color-text)" }}>{state.language.label}</span>
            <span style={{ color: "var(--color-text-faint)" }}>{langOpen ? "\u25B2" : "\u25BC"}</span>
          </button>

          <AnimatePresence>
            {langOpen && (
              <motion.ul
                role="listbox"
                aria-label="Select language"
                initial={{ opacity: 0, y: -8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.96 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-10 rounded-xl shadow-2xl py-1.5 min-w-[160px] z-50"
                style={{ background: "var(--color-bg-2)", border: "1px solid var(--color-border-bright)" }}
              >
                {supportedLanguages.map((lang) => (
                  <li
                    key={lang.code}
                    role="option"
                    aria-selected={state.language.code === lang.code}
                    tabIndex={0}
                    className="px-4 py-2 text-sm cursor-pointer transition-colors focus:outline-none"
                    style={{
                      color: state.language.code === lang.code ? "var(--color-primary)" : "var(--color-text-muted)",
                      background: state.language.code === lang.code ? "var(--color-primary-dim)" : "transparent",
                    }}
                    onClick={() => {
                      setLanguage(lang);
                      setLangOpen(false);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        setLanguage(lang);
                        setLangOpen(false);
                      }
                    }}
                  >
                    {lang.label}
                  </li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>

        {/* Animated LIVE Demo badge */}
        <span
          className="hidden sm:flex items-center gap-1.5 text-xs rounded-full px-3 py-1.5"
          style={{
            background: "var(--color-primary-dim)",
            border: "1px solid rgba(167, 139, 250, 0.3)",
            color: "var(--color-primary)",
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: "var(--color-primary)", animation: "pulse 1.5s ease-in-out infinite" }}
          />
          LIVE DEMO
        </span>
      </div>
    </header>
  );
}
