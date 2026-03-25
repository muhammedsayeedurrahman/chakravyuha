"use client";

import { Suspense, lazy, useState, useCallback, useRef } from "react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Header } from "@/components/Header";
import { HeroSection } from "@/components/HeroSection";
import { StatsBar } from "@/components/StatsBar";
import { FeatureGrid } from "@/components/FeatureGrid";
import { DemoShowcase } from "@/components/DemoShowcase";
import { GuidedStepsCard } from "@/components/GuidedStepsCard";
import { BottomTabNav } from "@/components/BottomTabNav";
import { ChatModal } from "@/components/ChatModal";
import { Card } from "@/components/Card";
import { ComplaintDraftCard } from "@/components/ComplaintDraftCard";
import { Preloader } from "@/components/Preloader";
import { ParticleBackground } from "@/components/ParticleBackground";
import { CurtainTransition } from "@/components/CurtainTransition";

const VoiceCard = lazy(() =>
  import("@/components/VoiceCard").then((m) => ({ default: m.VoiceCard }))
);

export default function HomeContent() {
  const [activeTab, setActiveTab] = useState("home");
  const [chatOpen, setChatOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [showCurtain, setShowCurtain] = useState(false);
  const prevTabRef = useRef("home");

  const handleTabChange = useCallback((tab: string) => {
    if (tab === prevTabRef.current) return;

    // Trigger curtain for non-chat tab switches
    if (tab !== "chat") {
      setShowCurtain(true);
      setTimeout(() => {
        setActiveTab(tab);
        prevTabRef.current = tab;
        setShowCurtain(false);
      }, 400);
    } else {
      setActiveTab(tab);
      prevTabRef.current = tab;
    }

    if (tab === "chat") setChatOpen(true);
  }, []);

  const handleStartChat = useCallback(() => {
    setChatOpen(true);
    setActiveTab("chat");
    prevTabRef.current = "chat";
  }, []);

  if (!loaded) {
    return <Preloader onComplete={() => setLoaded(true)} />;
  }

  return (
    <div className="min-h-screen flex flex-col pb-20 bg-grid relative" style={{ backgroundColor: "var(--color-bg)" }}>
      {/* Floating particles */}
      <ParticleBackground />

      {/* Curtain transition overlay */}
      <CurtainTransition show={showCurtain} />

      <Header />

      <main className="flex-1 max-w-3xl mx-auto w-full flex flex-col gap-8 py-6 relative z-10">
        {activeTab === "draft" ? (
          /* ── Draft Tab ──────────────────────────────────────────── */
          <ErrorBoundary>
            <ComplaintDraftCard />
          </ErrorBoundary>
        ) : (
          /* ── Home Tab (default) ─────────────────────────────────── */
          <>
            <HeroSection onStartChat={handleStartChat} />
            <StatsBar />
            <DemoShowcase />
            <FeatureGrid />

            {/* Guided Steps */}
            <ErrorBoundary>
              <div className="px-4">
                <Card>
                  <Card.Body>
                    <GuidedStepsCard />
                  </Card.Body>
                </Card>
              </div>
            </ErrorBoundary>

            {/* Voice Card */}
            <ErrorBoundary>
              <div className="px-4">
                <Card>
                  <Card.Header>
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">🎤</span>
                      <div>
                        <h2 className="font-bold text-sm" style={{ color: "var(--color-text)" }}>Speak your legal concern</h2>
                        <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Voice AI in 22 Indian languages</p>
                      </div>
                    </div>
                  </Card.Header>
                  <Card.Body>
                    <Suspense
                      fallback={<div className="flex items-center justify-center py-12 text-sm" style={{ color: "var(--color-text-faint)" }}>Loading voice assistant...</div>}
                    >
                      <VoiceCard />
                    </Suspense>
                  </Card.Body>
                </Card>
              </div>
            </ErrorBoundary>
          </>
        )}

        {/* Disclaimer */}
        <p className="text-xs text-center px-4" style={{ color: "var(--color-text-faint)" }}>
          This is not legal advice. Please consult a qualified lawyer.
        </p>
      </main>

      <BottomTabNav activeTab={activeTab} onTabChange={handleTabChange} />
      <ChatModal open={chatOpen} onClose={() => { setChatOpen(false); setActiveTab("home"); prevTabRef.current = "home"; }} />
    </div>
  );
}
