"use client";

import { useMemo } from "react";

/** Seed-based pseudo-random for deterministic particle placement */
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9301 + 49297) * 49297;
  return x - Math.floor(x);
}

interface Particle {
  left: string;
  top: string;
  delay: string;
  className: string;
}

export function ParticleBackground() {
  const particles = useMemo<Particle[]>(() => {
    const result: Particle[] = [];
    // Small particles
    for (let i = 0; i < 20; i++) {
      result.push({
        left: `${seededRandom(i) * 100}%`,
        top: `${seededRandom(i + 100) * 100}%`,
        delay: `${seededRandom(i + 200) * 80}s`,
        className: "particle-small",
      });
    }
    // Medium particles (violet-tinted)
    for (let i = 0; i < 12; i++) {
      result.push({
        left: `${seededRandom(i + 300) * 100}%`,
        top: `${seededRandom(i + 400) * 100}%`,
        delay: `${seededRandom(i + 500) * 100}s`,
        className: "particle-medium",
      });
    }
    // Large particles (rose-tinted, blurred)
    for (let i = 0; i < 8; i++) {
      result.push({
        left: `${seededRandom(i + 600) * 100}%`,
        top: `${seededRandom(i + 700) * 100}%`,
        delay: `${seededRandom(i + 800) * 120}s`,
        className: "particle-large",
      });
    }
    return result;
  }, []);

  return (
    <div className="particle-layer" aria-hidden>
      {particles.map((p, i) => (
        <div
          key={i}
          className={p.className}
          style={{
            left: p.left,
            top: p.top,
            animationDelay: p.delay,
          }}
        />
      ))}
    </div>
  );
}
