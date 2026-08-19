"use client";

import { useEffect, useState } from "react";
import QRCode from "qrcode";

export function QRFooter() {
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [pageUrl, setPageUrl] = useState("");

  useEffect(() => {
    const url = `${window.location.origin}${window.location.pathname}`;
    setPageUrl(url);
    QRCode.toDataURL(url, {
      width: 168,
      margin: 1,
      color: { dark: "#1a1a2e", light: "#ffffff" },
    })
      .then(setQrDataUrl)
      .catch(() => {});
  }, []);

  return (
    <div
      className="card animate-fade-up"
      style={{
        padding: 20,
        display: "flex",
        alignItems: "center",
        gap: 20,
        flexWrap: "wrap",
        marginTop: 8,
      }}
    >
      {qrDataUrl && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={qrDataUrl}
          width={96}
          height={96}
          alt="QR code linking to this page"
          style={{
            borderRadius: 8,
            border: "1px solid var(--border-subtle)",
            flexShrink: 0,
          }}
        />
      )}
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
          Scan to open this demo on your phone
        </div>
        <div
          style={{
            fontSize: 12,
            color: "var(--text-secondary)",
            fontFamily: "var(--font-mono)",
            marginTop: 4,
            wordBreak: "break-all",
          }}
        >
          {pageUrl}
        </div>
      </div>
    </div>
  );
}
