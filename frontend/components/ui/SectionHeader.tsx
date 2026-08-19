import type { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  subtitle: string;
  badge?: ReactNode;
}

export function SectionHeader({ title, subtitle, badge }: SectionHeaderProps) {
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
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
      <p style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>{subtitle}</p>
    </div>
  );
}
