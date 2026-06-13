interface PageHeaderProps {
  title: string;
  subtitle?: string;
  serif?: boolean;
  children?: React.ReactNode;
}

export function PageHeader({
  title,
  subtitle,
  serif = false,
  children,
}: PageHeaderProps) {
  return (
    <div
      style={{
        padding: "32px 40px 24px",
        borderBottom: "1px solid var(--border-subtle)",
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "space-between",
        gap: "16px",
      }}
    >
      <div>
        <h1
          style={{
            fontFamily: serif ? "var(--font-serif)" : "var(--font-sans)",
            fontSize: serif ? "32px" : "22px",
            fontWeight: serif ? "400" : "500",
            color: "var(--text-primary)",
            letterSpacing: serif ? "-0.02em" : "-0.01em",
            lineHeight: 1.1,
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--text-tertiary)",
              letterSpacing: "0.04em",
              marginTop: "6px",
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {children && <div style={{ flexShrink: 0 }}>{children}</div>}
    </div>
  );
}
