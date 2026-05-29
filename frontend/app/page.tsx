/**
 * AEQUITAS — Landing page (/)
 *
 * This is the home page. In Week 7 we'll replace the body with
 * the real dashboard. For now it's a clean status page that
 * confirms the frontend is running and can reach the backend.
 */
import Link from "next/link";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      {/* Logo + name */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-emerald-900/30 border border-emerald-800/50 mb-6">
          <span className="text-2xl font-bold text-emerald-400">Æ</span>
        </div>
        <h1 className="text-4xl font-bold text-white tracking-tight">
          AEQUITAS
        </h1>
        <p className="mt-2 text-gray-400 text-sm max-w-md">
          Agentic Equity &amp; Quantitative Intelligence Trading Analysis System
        </p>
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-xl mb-12">
        <StatusIndicator label="Frontend" status="online" />
        <StatusIndicator
          label="Backend API"
          status="checking"
          apiUrl="/health"
        />
        <StatusIndicator
          label="Database"
          status="checking"
          apiUrl="/health/ready"
        />
      </div>

      {/* Nav links — we'll fill these in Week 7 */}
      <nav className="flex gap-4 flex-wrap justify-center">
        {[
          { href: "/dashboard", label: "Dashboard" },
          { href: "/backtests", label: "Backtests" },
          { href: "/theses", label: "Trade Theses" },
          { href: "/risk", label: "Risk" },
        ].map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className="px-4 py-2 rounded-lg border border-gray-800
                       text-gray-400 text-sm hover:border-emerald-800
                       hover:text-emerald-400 transition-colors"
          >
            {label}
          </Link>
        ))}
      </nav>

      {/* Version footer */}
      <p className="mt-16 text-xs text-gray-600">v0.1.0 · Week 1 skeleton</p>
    </main>
  );
}
