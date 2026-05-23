/**
 * AEQUITAS — StatusIndicator component
 */
"use client";

import { useEffect, useState } from "react";

type Status = "online" | "offline" | "checking" | "degraded";

interface StatusIndicatorProps {
  label: string;
  status: Status;
  apiUrl?: string;
}

const statusConfig: Record<
  Status,
  { color: string; text: string; dot: string }
> = {
  online: {
    color: "border-emerald-800/50 bg-emerald-900/20",
    text: "text-emerald-400",
    dot: "bg-emerald-400",
  },
  offline: {
    color: "border-red-800/50 bg-red-900/20",
    text: "text-red-400",
    dot: "bg-red-400",
  },
  degraded: {
    color: "border-amber-800/50 bg-amber-900/20",
    text: "text-amber-400",
    dot: "bg-amber-400 animate-pulse",
  },
  checking: {
    color: "border-gray-800 bg-gray-900/20",
    text: "text-gray-500",
    dot: "bg-gray-500 animate-pulse",
  },
};

export function StatusIndicator({
  label,
  status: initialStatus,
  apiUrl,
}: StatusIndicatorProps) {
  const [status, setStatus] = useState<Status>(initialStatus);

  useEffect(() => {
    if (!apiUrl) return;

    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    async function checkStatus() {
      try {
        const res = await fetch(`${apiBase}${apiUrl}`, {
          cache: "no-store",
        });
        const data = (await res.json()) as { status?: string };

        if (!res.ok) {
          setStatus("offline");
        } else if (data.status === "degraded") {
          setStatus("degraded");
        } else {
          setStatus("online");
        }
      } catch {
        // No variable needed — server is simply unreachable
        setStatus("offline");
      }
    }

    void checkStatus();
    const interval = setInterval(() => {
      void checkStatus();
    }, 30_000);

    return () => clearInterval(interval);
  }, [apiUrl]);

  const cfg = statusConfig[status];

  return (
    <div
      className={`flex items-center gap-2 px-4 py-3 rounded-lg border ${cfg.color}`}
    >
      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className={`text-sm font-medium capitalize ${cfg.text}`}>{status}</p>
      </div>
    </div>
  );
}
