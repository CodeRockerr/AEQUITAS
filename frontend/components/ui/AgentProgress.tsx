"use client";

import { useEffect, useState } from "react";

interface AgentProgressProps {
  steps: string[];
  /** Approximate ms per step — used to advance the visual indicator
   * even though we can't get real progress events from a single
   * synchronous POST request. This is an honest approximation, not
   * a fake progress bar — steps stay lit once "reached" and the
   * final step pulses until the real response arrives. */
  msPerStep?: number;
}

/**
 * AEQUITAS — Agent pipeline progress indicator.
 *
 * Shows which stage of a multi-step agent pipeline is likely running,
 * instead of a bare spinner. Research backing: silence during a long
 * wait erodes trust fastest — showing *what's happening* even
 * approximately is far better than a generic loading state.
 */
export function AgentProgress({ steps, msPerStep = 4000 }: AgentProgressProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setActiveIndex(0);
    const timers = steps.map((_, i) =>
      setTimeout(() => setActiveIndex(i), i * msPerStep),
    );
    return () => timers.forEach(clearTimeout);
  }, [steps, msPerStep]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        padding: "8px 0",
      }}
    >
      {steps.map((step, i) => {
        const reached = i <= activeIndex;
        const isCurrent = i === activeIndex;
        return (
          <div
            key={step}
            className="animate-fade-up"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              animationDelay: `${i * 40}ms`,
            }}
          >
            <span
              style={{
                width: "14px",
                height: "14px",
                borderRadius: "50%",
                border: `1.5px solid ${reached ? "var(--accent-green)" : "var(--border-default)"}`,
                background:
                  reached && !isCurrent ? "var(--accent-green)" : "transparent",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                transition: "all 300ms var(--ease-out)",
              }}
            >
              {isCurrent && (
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: "var(--accent-green)",
                    animation: "pulse-dot 1.2s ease-in-out infinite",
                  }}
                />
              )}
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: reached ? "var(--text-primary)" : "var(--text-tertiary)",
                transition: "color 300ms var(--ease-out)",
              }}
            >
              {step}
            </span>
          </div>
        );
      })}
    </div>
  );
}
