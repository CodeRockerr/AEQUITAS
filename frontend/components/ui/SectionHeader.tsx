import type { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  subtitle: string;
  badge?: ReactNode;
  /** Centers the title/badge row and subtitle - opt-in, every existing
   * usage defaults to the original left-aligned layout. */
  centered?: boolean;
}

export function SectionHeader({
  title,
  subtitle,
  badge,
  centered = false,
}: SectionHeaderProps) {
  return (
    <div style={{ marginTop: 8, textAlign: centered ? "center" : undefined }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: centered ? "center" : undefined,
          gap: 10,
          flexWrap: "wrap",
        }}
      >
        <h2
          style={{
            fontSize: 18,
            fontWeight: 600,
            color: "var(--text-primary)",
            margin: 0,
          }}
        >
          {title}
        </h2>
        {badge}
      </div>
      <p
        style={{
          fontSize: 13,
          color: "var(--text-secondary)",
          marginTop: 4,
          maxWidth: centered ? 640 : undefined,
          margin: centered ? "4px auto 0" : "4px 0 0",
        }}
      >
        {subtitle}
      </p>
    </div>
  );
}
