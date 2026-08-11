"use client";

/**
 * AEQUITAS — AI Chat Widget
 *
 * Floating chat button on every page. Powered by Groq (free tier)
 * with tool use — calls your real AEQUITAS endpoints to answer
 * questions with actual data, not hallucinated numbers.
 */

import { useState, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  loading?: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SUGGESTIONS = [
  "Is AAPL worth buying right now?",
  "Compare NVDA and AMD risk profiles",
  "What's the market regime for SPY?",
  "Build a portfolio with AAPL, MSFT, NVDA",
  "Run RSI backtest on TSLA",
  "Analyse MSFT earnings",
];

const TOOL_LABELS: Record<string, string> = {
  get_signals: "◈ Signals",
  get_regime: "◐ Regime",
  get_forecast: "◑ ML Forecast",
  compute_var: "◬ Risk/VaR",
  run_thesis: "◧ Research Agent",
  get_news_sentiment: "◓ News Sentiment",
  get_earnings: "◑ Earnings",
  build_portfolio: "◒ Portfolio",
  run_backtest: "◫ Backtest",
  get_factor_model: "◇ Factor Model",
};

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi — I'm the AEQUITAS AI analyst. Ask me anything about a stock, portfolio, or market. I'll call the real algorithms to answer with actual data.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [showGreeting, setShowGreeting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const showTimer = setTimeout(() => setShowGreeting(true), 1500);
    const hideTimer = setTimeout(() => setShowGreeting(false), 12000);
    return () => {
      clearTimeout(showTimer);
      clearTimeout(hideTimer);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (showSuggestions) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [showSuggestions]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  async function send(text?: string) {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    setInput("");
    setShowSuggestions(false);
    const userMessage: Message = { role: "user", content };
    const loadingMessage: Message = {
      role: "assistant",
      content: "",
      loading: true,
    };

    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setLoading(true);

    // Build message history for the API (exclude loading placeholder)
    const history = [...messages, userMessage].map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await fetch(`${API_BASE}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();

      setMessages((prev) => [
        ...prev.slice(0, -1), // remove loading placeholder
        {
          role: "assistant",
          content: data.message,
          toolsUsed: data.tools_used,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev.slice(0, -1),
        {
          role: "assistant",
          content:
            "Sorry — something went wrong. The API might still be starting up. Try again in a moment.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  }

  return (
    <>
      {/* Proactive greeting bubble */}
      {showGreeting && !open && (
        <div
          onClick={() => {
            setOpen(true);
            setShowGreeting(false);
          }}
          style={{
            position: "fixed",
            bottom: "88px",
            right: "24px",
            width: "240px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "14px",
            padding: "14px 16px",
            boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
            zIndex: 9998,
            cursor: "pointer",
          }}
        >
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowGreeting(false);
            }}
            aria-label="Dismiss"
            style={{
              position: "absolute",
              top: "6px",
              right: "8px",
              background: "none",
              border: "none",
              color: "var(--text-tertiary)",
              cursor: "pointer",
              fontSize: "11px",
              padding: "2px",
            }}
          >
            ✕
          </button>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "9px",
              color: "var(--accent-green)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              marginBottom: "6px",
            }}
          >
            AEQUITAS AI Analyst
          </div>
          <div
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "13px",
              color: "var(--text-secondary)",
              lineHeight: 1.5,
            }}
          >
            👋 Ask me anything about a stock, portfolio, or the market — I&apos;ll
            pull real data to answer.
          </div>
        </div>
      )}

      {/* Floating button */}
      <button
        onClick={() => {
          setOpen((o) => !o);
          setShowGreeting(false);
        }}
        aria-label="Chat with the AEQUITAS AI analyst"
        title="Chat with the AEQUITAS AI analyst"
        style={{
          position: "fixed",
          bottom: "24px",
          right: "24px",
          width: "52px",
          height: "52px",
          borderRadius: "50%",
          background: open ? "var(--bg-elevated)" : "var(--text-primary)",
          border: "1px solid var(--border-subtle)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9998,
          boxShadow: "0 4px 24px rgba(0,0,0,0.3)",
          transition: "all 0.2s ease",
          color: open ? "var(--text-primary)" : "var(--text-inverse)",
        }}
      >
        {open ? (
          <span style={{ fontSize: "20px" }}>✕</span>
        ) : (
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M4 5h16a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5H9.5l-4.9 3.8a.5.5 0 0 1-.8-.4V17H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 5z"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinejoin="round"
            />
            <circle cx="8.5" cy="10.5" r="1.1" fill="currentColor" />
            <circle cx="12" cy="10.5" r="1.1" fill="currentColor" />
            <circle cx="15.5" cy="10.5" r="1.1" fill="currentColor" />
          </svg>
        )}
        {!open && (
          <span
            style={{
              position: "absolute",
              bottom: "2px",
              right: "2px",
              width: "12px",
              height: "12px",
              borderRadius: "50%",
              background: "var(--accent-green)",
              border: "2px solid var(--bg-surface)",
            }}
          />
        )}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          style={{
            position: "fixed",
            bottom: "88px",
            right: "24px",
            width: "380px",
            height: "560px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "16px",
            display: "flex",
            flexDirection: "column",
            zIndex: 9997,
            boxShadow: "0 8px 48px rgba(0,0,0,0.4)",
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid var(--border-subtle)",
              background: "var(--bg-elevated)",
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <span style={{ fontSize: "18px" }}>◈</span>
            <div>
              <div
                style={{
                  fontFamily: "var(--font-serif)",
                  fontSize: "15px",
                  color: "var(--text-primary)",
                  lineHeight: 1.2,
                }}
              >
                AEQUITAS AI
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "9px",
                  color: "var(--accent-green)",
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                Powered by Groq · Real data
              </div>
            </div>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: msg.role === "user" ? "flex-end" : "flex-start",
                  gap: "4px",
                }}
              >
                {/* Tool badges */}
                {msg.toolsUsed && msg.toolsUsed.length > 0 && (
                  <div
                    style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}
                  >
                    {msg.toolsUsed.map((t) => (
                      <span
                        key={t}
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "9px",
                          padding: "2px 7px",
                          background: "var(--bg-elevated)",
                          border: "1px solid var(--accent-green)",
                          borderRadius: "100px",
                          color: "var(--accent-green)",
                          letterSpacing: "0.04em",
                        }}
                      >
                        {TOOL_LABELS[t] ?? t}
                      </span>
                    ))}
                  </div>
                )}

                {/* Bubble */}
                <div
                  style={{
                    maxWidth: "88%",
                    padding: "10px 14px",
                    borderRadius:
                      msg.role === "user"
                        ? "12px 12px 2px 12px"
                        : "12px 12px 12px 2px",
                    background:
                      msg.role === "user"
                        ? "var(--text-primary)"
                        : "var(--bg-elevated)",
                    border:
                      msg.role === "user"
                        ? "none"
                        : "1px solid var(--border-subtle)",
                    fontFamily: "var(--font-sans)",
                    fontSize: "13px",
                    color:
                      msg.role === "user"
                        ? "var(--text-inverse)"
                        : "var(--text-secondary)",
                    lineHeight: "1.6",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {msg.loading ? (
                    <span
                      style={{
                        display: "flex",
                        gap: "3px",
                        alignItems: "center",
                      }}
                    >
                      {[0, 1, 2].map((j) => (
                        <span
                          key={j}
                          style={{
                            width: "5px",
                            height: "5px",
                            borderRadius: "50%",
                            background: "var(--text-tertiary)",
                            animation: `bounce 1.2s ease-in-out ${j * 0.2}s infinite`,
                          }}
                        />
                      ))}
                    </span>
                  ) : (
                    msg.content
                  )}
                </div>
              </div>
            ))}
            {showSuggestions && (
              <div
                style={{ display: "flex", flexDirection: "column", gap: "6px" }}
              >
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "9px",
                    color: "var(--text-tertiary)",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    marginBottom: "4px",
                  }}
                >
                  Try asking
                </div>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => void send(s)}
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--text-secondary)",
                      background: "var(--bg-elevated)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "8px",
                      padding: "7px 12px",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "border-color 0.15s",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.borderColor =
                        "var(--accent-green)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.borderColor =
                        "var(--border-subtle)")
                    }
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div
            style={{
              padding: "12px 16px",
              borderTop: "1px solid var(--border-subtle)",
              background: "var(--bg-elevated)",
              display: "flex",
              gap: "8px",
              alignItems: "flex-end",
            }}
          >
            <button
              onClick={() => setShowSuggestions((s) => !s)}
              aria-label="Toggle suggested questions"
              title="Suggested questions"
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: showSuggestions
                  ? "var(--accent-green-bg)"
                  : "var(--bg-surface)",
                border: `1px solid ${
                  showSuggestions ? "var(--accent-green)" : "var(--border-subtle)"
                }`,
                color: showSuggestions
                  ? "var(--accent-green)"
                  : "var(--text-tertiary)",
                cursor: "pointer",
                fontSize: "16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.15s",
                flexShrink: 0,
              }}
            >
              ✦
            </button>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything about any stock..."
              rows={1}
              disabled={loading}
              style={{
                flex: 1,
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--text-primary)",
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "8px",
                padding: "8px 12px",
                resize: "none",
                outline: "none",
                lineHeight: "1.5",
                maxHeight: "80px",
                overflowY: "auto",
              }}
            />
            <button
              onClick={() => void send()}
              disabled={loading || !input.trim()}
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background:
                  loading || !input.trim()
                    ? "var(--bg-surface)"
                    : "var(--text-primary)",
                border: "1px solid var(--border-subtle)",
                color:
                  loading || !input.trim()
                    ? "var(--text-tertiary)"
                    : "var(--text-inverse)",
                cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                fontSize: "16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.15s",
                flexShrink: 0,
              }}
            >
              →
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
      `}</style>
    </>
  );
}
