"use client";

/**
 * Animated end-to-end data-flow diagram for the How It Works page: a
 * packet races through every stage of the platform, node dots pulse as
 * it arrives. Purely a CSS keyframe loop (matches SimulationDiagram's
 * approach) - not synced to anything real, just a visual summary of the
 * pipeline shape before the accordion below explains each stage.
 */

import { Fragment, useEffect, useState } from "react";

const STAGES = [
  { icon: "◎", label: "Market Data" },
  { icon: "◈", label: "Signals & Risk" },
  { icon: "◑", label: "ML Models" },
  { icon: "◧", label: "AI Agents" },
  { icon: "✦", label: "Your Thesis" },
];

export function PipelineFlowDiagram() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 640px)");
    setIsMobile(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return (
    <div className="card animate-fade-up" style={{ padding: "28px clamp(20px, 5vw, 40px)" }}>
      <div
        style={{
          fontSize: 12,
          color: "var(--text-tertiary)",
          textAlign: "center",
          marginBottom: 24,
          fontFamily: "var(--font-mono)",
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}
      >
        A price, on its way to becoming a decision
      </div>

      <div className={isMobile ? "pipeline-flow pipeline-flow-v" : "pipeline-flow"}>
        {STAGES.map((stage, i) => (
          <Fragment key={stage.label}>
            <div className="pipeline-node">
              <div
                className="pipeline-node-dot"
                style={{ animationDelay: `${i * 0.4}s` }}
              >
                {stage.icon}
              </div>
              <div className="pipeline-node-label">{stage.label}</div>
            </div>
            {i < STAGES.length - 1 && (
              <div className={isMobile ? "pipeline-track pipeline-track-v" : "pipeline-track"}>
                <div
                  className={
                    isMobile ? "pipeline-packet pipeline-packet-v" : "pipeline-packet"
                  }
                  style={{ animationDelay: `${i * 0.5}s` }}
                />
              </div>
            )}
          </Fragment>
        ))}
      </div>

      <style>{`
        .pipeline-flow {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: clamp(2px, 1.5vw, 10px);
        }
        .pipeline-flow-v {
          flex-direction: column;
          align-items: center;
          gap: 0;
        }
        .pipeline-node {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          width: 78px;
          flex-shrink: 0;
        }
        .pipeline-node-dot {
          width: 34px;
          height: 34px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 15px;
          background: var(--bg-elevated);
          border: 1px solid var(--border-default);
          color: var(--accent-green);
          animation: pipeline-pulse 2.4s ease-in-out infinite;
        }
        .pipeline-node-label {
          font-family: var(--font-mono);
          font-size: 10px;
          letter-spacing: 0.02em;
          color: var(--text-tertiary);
          text-align: center;
          line-height: 1.3;
        }
        .pipeline-track {
          position: relative;
          flex: 1;
          min-width: 24px;
          height: 3px;
          border-radius: 2px;
          background: var(--border-subtle);
          margin-bottom: 22px;
        }
        .pipeline-track-v {
          flex: none;
          width: 3px;
          height: 28px;
          min-width: 0;
          margin: 0;
        }
        .pipeline-packet {
          position: absolute;
          top: 50%;
          left: 0;
          width: 9px;
          height: 9px;
          border-radius: 50%;
          background: var(--accent-green);
          transform: translate(-50%, -50%);
          box-shadow: 0 0 0 3px var(--bg-surface);
          animation: pipeline-race-h 2s linear infinite;
        }
        .pipeline-packet-v {
          top: 0;
          left: 50%;
          animation: pipeline-race-v 2s linear infinite;
        }
        @keyframes pipeline-race-h {
          0%   { left: 0%; opacity: 0; }
          8%   { opacity: 1; }
          92%  { opacity: 1; }
          100% { left: 100%; opacity: 0; }
        }
        @keyframes pipeline-race-v {
          0%   { top: 0%; opacity: 0; }
          8%   { opacity: 1; }
          92%  { opacity: 1; }
          100% { top: 100%; opacity: 0; }
        }
        @keyframes pipeline-pulse {
          0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 color-mix(in srgb, var(--accent-green) 30%, transparent); }
          50%      { transform: scale(1.12); box-shadow: 0 0 0 6px color-mix(in srgb, var(--accent-green) 12%, transparent); }
        }
        @media (prefers-reduced-motion: reduce) {
          .pipeline-node-dot, .pipeline-packet {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}
