interface BadgeProps {
  children: React.ReactNode;
  variant?: "green" | "red" | "amber" | "blue" | "neutral";
  /** Show a directional glyph alongside color — set false only for
   * badges where the text itself is already unambiguous without color
   * (e.g. a ticker symbol badge). Defaults to true for semantic badges. */
  showGlyph?: boolean;
}

const VARIANT_GLYPH: Record<string, string> = {
  green: "▲",
  red: "▼",
  amber: "●",
  blue: "■",
  neutral: "",
};

export function Badge({
  children,
  variant = "neutral",
  showGlyph = true,
}: BadgeProps) {
  const glyph = showGlyph ? VARIANT_GLYPH[variant] : "";
  return (
    <span
      className={`badge badge-${variant}`}
      style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}
    >
      {glyph && (
        <span aria-hidden="true" style={{ fontSize: "9px" }}>
          {glyph}
        </span>
      )}
      {children}
    </span>
  );
}
