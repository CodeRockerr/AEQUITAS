interface InsightStripProps {
  noticed: string;
  whyItMatters: string;
  nextAction: string;
}

/**
 * AEQUITAS — Structured agent insight summary.
 *
 * Research backing ("explainable guidance" pattern): users trust AI
 * output faster when three things are made explicit — what the
 * system noticed, why it matters, and what to do next. This sits
 * above the full prose output as a scannable summary; the full
 * narrative remains available below for anyone who wants depth.
 */
export function InsightStrip({
  noticed,
  whyItMatters,
  nextAction,
}: InsightStripProps) {
  const rows = [
    { label: "Noticed", value: noticed, icon: "◐" },
    { label: "Why it matters", value: whyItMatters, icon: "◑" },
    { label: "Next", value: nextAction, icon: "◒" },
  ];

  return (
    <div
      className="card"
      style={{
        padding: "18px 22px",
        marginBottom: "20px",
        background: "var(--bg-elevated)",
      }}
    >
      {rows.map((row, i) => (
        <div
          key={row.label}
          style={{
            display: "grid",
            gridTemplateColumns: "120px 1fr",
            gap: "12px",
            alignItems: "start",
            padding: "8px 0",
            borderBottom:
              i < rows.length - 1 ? "1px solid var(--border-subtle)" : "none",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              letterSpacing: "0.06em",
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
            }}
          >
            <span aria-hidden="true">{row.icon}</span>
            {row.label}
          </div>
          <div
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "13px",
              color: "var(--text-primary)",
              lineHeight: "1.6",
            }}
          >
            {row.value}
          </div>
        </div>
      ))}
    </div>
  );
}
