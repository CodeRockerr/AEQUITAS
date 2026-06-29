interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "green" | "red" | "amber" | "blue" | "neutral";
  delay?: number;
}

/**
 * Directional glyph paired with each accent color — never rely on
 * color alone to convey meaning (accessibility: color-blind users
 * can't reliably distinguish red/green hue differences).
 */
const ACCENT_GLYPH: Record<string, string> = {
  green: "▲",
  red: "▼",
  amber: "●",
  blue: "■",
  neutral: "",
};

export function StatCard({
  label,
  value,
  sub,
  accent = "neutral",
  delay = 0,
}: StatCardProps) {
  const accentColors: Record<string, string> = {
    green: "var(--accent-green)",
    red: "var(--accent-red)",
    amber: "var(--accent-amber)",
    blue: "var(--accent-blue)",
    neutral: "var(--text-primary)",
  };

  const glyph = ACCENT_GLYPH[accent];

  return (
    <div
      className="card animate-fade-up"
      style={{
        padding: "20px 24px",
        animationDelay: `${delay}ms`,
      }}
    >
      <div className="stat-label">{label}</div>
      <div
        className="stat-value"
        style={{
          color: accentColors[accent],
          marginTop: "6px",
          display: "flex",
          alignItems: "baseline",
          gap: "6px",
        }}
      >
        {glyph && (
          <span style={{ fontSize: "11px", opacity: 0.85 }} aria-hidden="true">
            {glyph}
          </span>
        )}
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            color: "var(--text-tertiary)",
            marginTop: "4px",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}
