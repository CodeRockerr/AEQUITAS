import type { CSSProperties } from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "green" | "red" | "amber" | "blue" | "neutral";
  delay?: number;
  style?: CSSProperties;
}

/**
 * Directional glyph paired with each accent color. Never rely on
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
  style,
}: StatCardProps) {
  const accentColors: Record<string, string> = {
    green: "var(--accent-green)",
    red: "var(--accent-red)",
    amber: "var(--accent-amber)",
    blue: "var(--accent-blue)",
    neutral: "var(--text-primary)",
  };

  const glyph = ACCENT_GLYPH[accent];
  // Long category strings (e.g. "High Volatility") don't fit a 150px-wide
  // card at the default 22px mono size without hyphen-less mid-word
  // breaks; step the size down rather than let a single word overflow.
  const valueFontSize =
    typeof value === "string" && value.length > 10 ? "16px" : undefined;

  return (
    <div
      className="card animate-fade-up"
      style={{
        padding: "20px 24px",
        animationDelay: `${delay}ms`,
        ...style,
      }}
    >
      <div className="stat-label">{label}</div>
      <div
        className="stat-value"
        style={{
          color: accentColors[accent],
          marginTop: "6px",
          display: "flex",
          alignItems: "flex-start",
          gap: "6px",
          minWidth: 0,
          fontSize: valueFontSize,
        }}
      >
        {glyph && (
          <span
            style={{ fontSize: "11px", opacity: 0.85, flexShrink: 0 }}
            aria-hidden="true"
          >
            {glyph}
          </span>
        )}
        <span style={{ minWidth: 0, overflowWrap: "break-word" }}>
          {value}
        </span>
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
