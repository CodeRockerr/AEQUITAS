"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useTheme } from "./ThemeProvider";
import { SITE_STATS } from "@/lib/site-stats";

// Grouped nav reduces top-level cognitive load: research backing
// shows that reducing stimuli and clarifying intent improves trust and
// usability in data-dense interfaces. 9 flat items -> 2 ungrouped + 3 groups.
const NAV_TOP = [
  { href: "/", label: "Overview", icon: "○" },
  { href: "/dashboard", label: "Dashboard", icon: "◈" },
  { href: "/how-it-works", label: "How It Works", icon: "◍" },
];

const NAV_GROUPS = [
  {
    label: "Research",
    items: [
      { href: "/theses", label: "Theses", icon: "◧" },
      { href: "/agents", label: "Agents", icon: "◓" },
    ],
  },
  {
    label: "Quant Tools",
    items: [
      { href: "/backtests", label: "Backtests", icon: "◫" },
      { href: "/risk", label: "Risk", icon: "◬" },
      { href: "/factors", label: "Factors", icon: "◇" },
    ],
  },
  {
    label: "Python vs C++",
    items: [
      { href: "/performance", label: "Benchmarks", icon: "◭" },
      { href: "/trading-simulation", label: "Trading simulation", icon: "◔" },
    ],
  },
];

const NAV_BOTTOM = [{ href: "/about", label: "About", icon: "◉" }];

const VERSION = SITE_STATS.version;

function NavLink({
  href,
  label,
  icon,
  active,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: string;
  active: boolean;
  onNavigate?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      className={`nav-link${active ? " nav-link-active" : ""}`}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "10px",
        padding: "10px 12px",
        borderRadius: "var(--radius-md)",
        marginBottom: "2px",
        textDecoration: "none",
        transition: "all var(--duration-fast)",
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "14px",
          color: active ? "var(--text-primary)" : "var(--text-tertiary)",
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
          color: active ? "var(--text-primary)" : "var(--text-secondary)",
        }}
      >
        {label}
      </span>
    </Link>
  );
}

function NavList({
  path,
  onNavigate,
}: {
  path: string | null;
  onNavigate?: () => void;
}) {
  return (
    <nav style={{ padding: "12px 8px", flex: 1, overflowY: "auto" }}>
      {NAV_TOP.map((item) => (
        <NavLink
          key={item.href}
          {...item}
          active={path === item.href}
          onNavigate={onNavigate}
        />
      ))}

      {NAV_GROUPS.map((group) => (
        <div key={group.label} style={{ marginTop: "16px" }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "9px",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
              padding: "0 12px",
              marginBottom: "6px",
            }}
          >
            {group.label}
          </div>
          {group.items.map((item) => (
            <NavLink
              key={item.href}
              {...item}
              active={path === item.href}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      ))}

      <div
        style={{
          marginTop: "16px",
          paddingTop: "12px",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        {NAV_BOTTOM.map((item) => (
          <NavLink
            key={item.href}
            {...item}
            active={path === item.href}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </nav>
  );
}

function SidebarFooter({
  theme,
  toggle,
}: {
  theme: string;
  toggle: () => void;
}) {
  return (
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
          padding: "10px 8px",
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
  );
}

function Wordmark() {
  return (
    <div>
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
  );
}

export function Sidebar() {
  const path = usePathname();
  const { theme, toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [drawerEntered, setDrawerEntered] = useState(false);

  // Close the drawer whenever the route changes (a nav tap navigated away).
  useEffect(() => {
    setMobileOpen(false);
  }, [path]);

  // Close automatically if the viewport is resized up to desktop width
  // (Tailwind's md breakpoint), so a drawer left open pre-resize can't get
  // stuck showing behind the now-visible static sidebar.
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    const onChange = () => {
      if (mq.matches) setMobileOpen(false);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!mobileOpen) {
      setDrawerEntered(false);
      return;
    }
    const raf = requestAnimationFrame(() => setDrawerEntered(true));

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", onKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [mobileOpen]);

  return (
    <>
      {/* ── Mobile top bar (hidden md and up) ───────────────────── */}
      <div
        className="flex md:hidden"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 40,
          alignItems: "center",
          justifyContent: "space-between",
          background: "var(--bg-surface)",
          borderBottom: "1px solid var(--border-subtle)",
          padding:
            "max(10px, env(safe-area-inset-top)) 12px 10px max(12px, env(safe-area-inset-left))",
        }}
      >
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          aria-expanded={mobileOpen}
          style={{
            width: "44px",
            height: "44px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "none",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-md)",
            color: "var(--text-primary)",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path
              d="M2 4.5h14M2 9h14M2 13.5h14"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
          </svg>
        </button>

        <div
          style={{
            fontFamily: "var(--font-serif)",
            fontSize: "16px",
            color: "var(--text-primary)",
            letterSpacing: "-0.02em",
          }}
        >
          Æquitas
        </div>

        <span className="live-dot" style={{ marginRight: "8px" }} />
      </div>

      {/* ── Mobile drawer + backdrop ─────────────────────────────── */}
      {mobileOpen && (
        <div className="md:hidden">
          <div
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 49,
              background: "rgba(0, 0, 0, 0.4)",
              opacity: drawerEntered ? 1 : 0,
              transition: "opacity var(--duration-base) var(--ease-out)",
            }}
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              bottom: 0,
              zIndex: 50,
              width: "min(280px, 84vw)",
              background: "var(--bg-surface)",
              borderRight: "1px solid var(--border-subtle)",
              display: "flex",
              flexDirection: "column",
              transform: drawerEntered ? "translateX(0)" : "translateX(-100%)",
              transition: "transform var(--duration-base) var(--ease-out)",
              paddingTop: "env(safe-area-inset-top)",
              paddingBottom: "env(safe-area-inset-bottom)",
              paddingLeft: "env(safe-area-inset-left)",
            }}
          >
            <div
              style={{
                padding: "20px 20px 20px",
                borderBottom: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
              }}
            >
              <Wordmark />
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation menu"
                style={{
                  width: "36px",
                  height: "36px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "none",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              >
                ✕
              </button>
            </div>

            <NavList path={path} onNavigate={() => setMobileOpen(false)} />
            <SidebarFooter theme={theme} toggle={toggle} />
          </aside>
        </div>
      )}

      {/* ── Desktop sidebar (hidden below md) ───────────────────── */}
      <aside
        className="hidden md:flex"
        style={{
          width: "208px",
          height: "100vh",
          background: "var(--bg-surface)",
          borderRight: "1px solid var(--border-subtle)",
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
          <Wordmark />
        </div>

        <NavList path={path} />
        <SidebarFooter theme={theme} toggle={toggle} />
      </aside>
    </>
  );
}
