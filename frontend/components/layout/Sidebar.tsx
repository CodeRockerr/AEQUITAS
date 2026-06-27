"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "./ThemeProvider";

const NAV = [
  { href: "/", label: "Overview", icon: "○" },
  { href: "/dashboard", label: "Dashboard", icon: "◈" },
  { href: "/backtests", label: "Backtests", icon: "◫" },
  { href: "/theses", label: "Theses", icon: "◧" },
  { href: "/risk", label: "Risk", icon: "◬" },
  { href: "/factors", label: "Factors", icon: "◇" },
  { href: "/agents", label: "Agents", icon: "◓" },
  { href: "/about", label: "About", icon: "◉" },
];

const VERSION = "v0.10.0";

export function Sidebar() {
  const path = usePathname();
  const { theme, toggle } = useTheme();

  return (
    <aside
      style={{
        width: "200px",
        minHeight: "100vh",
        background: "var(--bg-surface)",
        borderRight: "1px solid var(--border-subtle)",
        display: "flex",
        flexDirection: "column",
        padding: "0",
        position: "sticky",
        top: 0,
        flexShrink: 0,
      }}
    >
      <div
        style={{
          padding: "24px 20px 20px",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "18px",
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
            lineHeight: 1,
          }}
        >
          Æquitas
        </div>
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "9px",
            color: "var(--text-tertiary)",
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            marginTop: "4px",
          }}
        >
          Quant Research
        </div>
      </div>

      <nav style={{ padding: "12px 8px", flex: 1 }}>
        {NAV.map(({ href, label, icon }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "8px 12px",
                borderRadius: "var(--radius-md)",
                marginBottom: "2px",
                textDecoration: "none",
                background: active ? "var(--bg-elevated)" : "transparent",
                transition: "all var(--duration-fast)",
              }}
              onMouseEnter={(e) => {
                if (!active)
                  (e.currentTarget as HTMLElement).style.background =
                    "var(--bg-elevated)";
              }}
              onMouseLeave={(e) => {
                if (!active)
                  (e.currentTarget as HTMLElement).style.background =
                    "transparent";
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "14px",
                  color: active
                    ? "var(--text-primary)"
                    : "var(--text-tertiary)",
                  lineHeight: 1,
                }}
              >
                {icon}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-sans)",
                  fontSize: "13px",
                  fontWeight: active ? "500" : "400",
                  color: active
                    ? "var(--text-primary)"
                    : "var(--text-secondary)",
                }}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </nav>

      <div
        style={{
          padding: "16px",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "6px 8px",
          }}
        >
          <span className="live-dot" />
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "10px",
              color: "var(--accent-green)",
              letterSpacing: "0.06em",
            }}
          >
            LIVE
          </span>
        </div>

        <button
          onClick={toggle}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "6px 8px",
            background: "none",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            cursor: "pointer",
            color: "var(--text-secondary)",
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            letterSpacing: "0.04em",
            transition: "all var(--duration-fast)",
            width: "100%",
          }}
        >
          <span>{theme === "dark" ? "◐" : "◑"}</span>
          <span>{theme === "dark" ? "Light" : "Dark"}</span>
        </button>

        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "10px",
            color: "var(--text-tertiary)",
            padding: "0 8px",
            letterSpacing: "0.04em",
          }}
        >
          {VERSION}
        </div>
      </div>
    </aside>
  );
}
