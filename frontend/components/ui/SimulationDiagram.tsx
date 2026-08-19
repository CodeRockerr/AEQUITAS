"use client";

/**
 * Animated diagram of the live-decision pipeline: a tick arrives, then
 * pandas and C++ race to turn it into a signal. Runs on its own ambient
 * loop (not synced frame-for-frame to real tick timing, since that would
 * be fragile) - the real numbers underneath come from the live stat cards
 * and ticker table, not from this animation's timing.
 */

interface SimulationDiagramProps {
  pandasLabel: string;
  cppLabel: string;
}

export function SimulationDiagram({ pandasLabel, cppLabel }: SimulationDiagramProps) {
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
        How every tick becomes a decision
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "auto 1fr auto",
          alignItems: "center",
          gap: "clamp(12px, 3vw, 32px)",
        }}
      >
        <div className="sim-node">
          <div className="sim-node-dot sim-node-dot-tick" />
          <div className="sim-node-label">New tick</div>
        </div>

        <div style={{ display: "grid", gap: 28 }}>
          <div>
            <div className="sim-track">
              <div className="sim-packet sim-packet-pandas" />
            </div>
            <div className="sim-lane-label" style={{ color: "var(--accent-blue)" }}>
              pandas - {pandasLabel}
            </div>
          </div>
          <div>
            <div className="sim-track">
              <div className="sim-packet sim-packet-cpp" />
            </div>
            <div className="sim-lane-label" style={{ color: "var(--accent-green)" }}>
              C++ - {cppLabel}
            </div>
          </div>
        </div>

        <div className="sim-node">
          <div className="sim-node-dot sim-node-dot-decision" />
          <div className="sim-node-label">Decision</div>
        </div>
      </div>

      <style>{`
        .sim-node {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          width: 72px;
        }
        .sim-node-dot {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: var(--text-tertiary);
        }
        .sim-node-dot-tick {
          background: var(--text-secondary);
          animation: sim-pulse 1.3s ease-in-out infinite;
        }
        .sim-node-dot-decision {
          background: var(--accent-green);
          animation: sim-pulse 1.3s ease-in-out infinite 0.4s;
        }
        .sim-node-label {
          font-family: var(--font-mono);
          font-size: 10px;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          color: var(--text-tertiary);
          text-align: center;
        }
        .sim-track {
          position: relative;
          height: 4px;
          border-radius: 2px;
          background: var(--border-subtle);
        }
        .sim-packet {
          position: absolute;
          top: 50%;
          left: 0;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          transform: translate(-50%, -50%);
          box-shadow: 0 0 0 4px var(--bg-surface);
        }
        .sim-packet-pandas {
          background: var(--accent-blue);
          animation: sim-race 2.4s linear infinite;
        }
        .sim-packet-cpp {
          background: var(--accent-green);
          animation: sim-race 0.5s linear infinite;
        }
        .sim-lane-label {
          font-family: var(--font-mono);
          font-size: 11px;
          margin-top: 8px;
        }
        @keyframes sim-race {
          0%   { left: 0%; opacity: 0; }
          6%   { opacity: 1; }
          94%  { opacity: 1; }
          100% { left: 100%; opacity: 0; }
        }
        @keyframes sim-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%      { opacity: 0.4; transform: scale(0.8); }
        }
      `}</style>
    </div>
  );
}
