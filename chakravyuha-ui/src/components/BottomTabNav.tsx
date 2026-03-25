"use client";

import { useState } from "react";

interface BottomTabNavProps {
  onTabChange: (tab: string) => void;
  activeTab: string;
}

const TABS = [
  { id: "home", icon: "\uD83C\uDFE0", label: "Home" },
  { id: "chat", icon: "\u2696\uFE0F", label: "Consult" },
  { id: "draft", icon: "\uD83D\uDCDD", label: "Draft" },
  { id: "voice", icon: "\uD83C\uDFA4", label: "Voice" },
  { id: "info", icon: "\uD83D\uDCDC", label: "Laws" },
];

export function BottomTabNav({ onTabChange, activeTab }: BottomTabNavProps) {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 glass-bright flex justify-around py-2 px-2 safe-area-pb" suppressHydrationWarning>
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={`bottom-nav-tab ${activeTab === tab.id ? "active" : ""}`}
          suppressHydrationWarning
        >
          <span className="text-lg">{tab.icon}</span>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
