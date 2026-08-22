"use client";

import { Suspense, lazy, useState, useCallback, useRef } from "react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Header } from "@/components/Header";
import { HeroSection } from "@/components/HeroSection";
import { StatsBar } from "@/components/StatsBar";
import { DemoShowcase } from "@/components/DemoShowcase";
import { LawSection } from "@/components/LawSection";
import { GuidedStepsCard } from "@/components/GuidedStepsCard";
import { BottomTabNav } from "@/components/BottomTabNav";
import { ChatModal } from "@/components/ChatModal";
import { Card } from "@/components/Card";
import { ComplaintDraftCard } from "@/components/ComplaintDraftCard";
import { OpenClawCard } from "@/components/OpenClawCard";
import { CivicAssistant, type CivicFilingHandoff, type CivicJourney } from "@/components/CivicAssistant";
import type { CivicWorkflowLaunch } from "@/lib/civicWorkflowHandoff";
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
  const [civicJourney, setCivicJourney] = useState<CivicJourney>("rti");
  const [civicContext, setCivicContext] = useState<CivicWorkflowLaunch | null>(null);
  const [civicLaunchVersion, setCivicLaunchVersion] = useState(0);
  const [filingHandoff, setFilingHandoff] = useState<{ portalId: string; userData: Record<string, string> } | null>(null);
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

  const handleOpenCivic = useCallback((journey: CivicJourney = "rti") => {
    setCivicJourney(journey);
    setCivicContext(null);
    setCivicLaunchVersion((version) => version + 1);
    handleTabChange("civic");
  }, [handleTabChange]);

  const handleChatCivicHandoff = useCallback((launch: CivicWorkflowLaunch) => {
    setChatOpen(false);
    setCivicJourney(launch.journey);
    setCivicContext(launch);
    setCivicLaunchVersion((version) => version + 1);
    handleTabChange("civic");
  }, [handleTabChange]);

  const handleOpenFile = useCallback((portal?: string) => {
    setFilingHandoff(portal ? { portalId: portal, userData: {} } : null);
    handleTabChange("file");
  }, [handleTabChange]);

  const handleCivicFilingHandoff = useCallback((handoff: CivicFilingHandoff) => {
    setFilingHandoff(handoff);
    handleTabChange("file");
  }, [handleTabChange]);

  const handleCivicLegalHandoff = useCallback((target: "chat" | "draft") => {
    if (target === "chat") {
      handleStartChat();
      return;
    }
    handleTabChange("draft");
  }, [handleStartChat, handleTabChange]);

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
        {activeTab === "file" ? (
          /* ── File Tab (OpenClaw) ─────────────────────────────────── */
          <ErrorBoundary>
            <OpenClawCard
              key={`${filingHandoff?.portalId ?? "none"}-${filingHandoff?.userData.description?.slice(0, 24) ?? "blank"}`}
              initialPortalId={filingHandoff?.portalId}
              initialUserData={filingHandoff?.userData}
            />
          </ErrorBoundary>
        ) : activeTab === "civic" ? (
          <ErrorBoundary>
            <CivicAssistant
              key={`${civicJourney}-${civicLaunchVersion}`}
              initialJourney={civicJourney}
              initialContext={civicContext}
              onOpenClaw={handleCivicFilingHandoff}
              onOpenLegal={handleCivicLegalHandoff}
            />
          </ErrorBoundary>
        ) : activeTab === "draft" ? (
          /* ── Draft Tab ──────────────────────────────────────────── */
          <ErrorBoundary>
            <ComplaintDraftCard />
          </ErrorBoundary>
        ) : (
          /* ── Home Tab (default) ─────────────────────────────────── */
          <>
            <HeroSection onStartChat={handleStartChat} />
            <StatsBar />
            <LawSection
              onOpenDraft={() => handleTabChange("draft")}
              onOpenFile={handleOpenFile}
              onOpenCivic={handleOpenCivic}
              onAutoFlow={handleStartChat}
            />
            <DemoShowcase />

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
                        <p className="text-xs" style={{ color: "var(--color-text-muted)" }}>Multilingual voice input and spoken responses</p>
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
      <ChatModal
        open={chatOpen}
        onClose={() => { setChatOpen(false); setActiveTab("home"); prevTabRef.current = "home"; }}
        onOpenCivic={handleChatCivicHandoff}
      />
    </div>
  );
}
