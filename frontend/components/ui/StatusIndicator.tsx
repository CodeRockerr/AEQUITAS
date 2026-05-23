/**
 * AEQUITAS — StatusIndicator component
 *
 * Shows a coloured dot + label indicating service health.
 * If an apiUrl is provided it pings the backend and updates live.
 *
 * This is our first React component. Note:
 *  - "use client" tells Next.js this component runs in the browser
 *    (needed because we use useState and useEffect hooks)
 *  - Components without "use client" run on the server (faster,
 *    no JS sent to browser) — we'll use server components for
 *    data-heavy pages in Week 7
 */
"use client";

import { useEffect, useState } from "react";

type Status = "online" | "offline" | "checking" | "degraded";

interface StatusIndicatorProps {
  label: string;
  status: Status;
  apiUrl?: string;   // if provided, we'll ping this URL to get live status
}

const statusConfig: Record<Status, { color: string; text: string; dot: string }> = {
  online:   { color: "border-emerald-800/50 bg-emerald-900/20", text: "text-emerald-400", dot: "bg-emerald-400" },
  offline:  { color: "border-red-800/50 bg-red-900/20",         text: "text-red-400",     dot: "bg-red-400" },
  degraded: { color: "border-amber-800/50 bg-amber-900/20",     text: "text-amber-400",   dot: "bg-amber-400 animate-pulse" },
  checking: { color: "border-gray-800 bg-gray-900/20",          text: "text-gray-500",    dot: "bg-gray-500 animate-pulse" },
};

export function StatusIndicator({ label, status: initialStatus, apiUrl }: StatusIndicatorProps) {
  const [status, setStatus] = useState<Status>(initialStatus);

  useEffect(() => {
    // If no API URL given, keep the initial status
    if (!apiUrl) return;

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    async function checkStatus() {
      try {
        const res = await fetch(`${apiBase}${apiUrl}`, { cache: "no-store" });
        const data = await res.json();

        if (!res.ok) {
          setStatus("offline");
        } else if (data.status === "degraded") {
          setStatus("degraded");
        } else {
          setStatus("online");
        }
      } catch {
        // fetch throws if the server is unreachable
        setStatus("offline");
      }
    }

    checkStatus();
    // Re-check every 30 seconds
    const interval = setInterval(checkStatus, 30_000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  const cfg = statusConfig[status];

  return (
    <div className={`flex items-center gap-2 px-4 py-3 rounded-lg border ${cfg.color}`}>
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className={`text-sm font-medium capitalize ${cfg.text}`}>{status}</p>
      </div>
    </div>
  );
}
