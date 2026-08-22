"use client";

/**
 * AEQUITAS: AI Chat Widget
 *
 * Floating chat button, fixed to the bottom-right corner on every
 * page. Powered by Groq (free tier) with tool use, calling your real
 * AEQUITAS endpoints to answer questions with actual data, not
 * hallucinated numbers.
 */

import { useState, useRef, useEffect } from "react";
import { Markdown } from "@/components/ui/Markdown";

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

// Fixed to the bottom-right corner everywhere - not draggable. The panel
// opens upward from the button, anchored to the same corner.
const BUTTON_SIZE = 52;
const PANEL_W = 380;
const PANEL_H = 560;
const WIDGET_MARGIN = 24;
const PANEL_GAP = 12;

// How long the proactive greeting stays up to establish, up front, that
// this is an AI-powered assistant (not a static help widget) before it
// fades away - long enough to actually be read, short enough not to
// linger as clutter on every fresh page load.
const GREETING_SHOW_DELAY_MS = 1500;
const GREETING_VISIBLE_MS = 15000;

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi, I'm the AEQUITAS AI analyst. Ask me anything about a stock, portfolio, or market. I'll call the real algorithms to answer with actual data.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [showGreeting, setShowGreeting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Below this width the floating 380px panel wouldn't fit (or would fit
  // with almost no margin) - phones get a full-width bottom sheet instead
  // of a corner-anchored floating panel.
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 640px)");
    setIsMobile(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    const showTimer = setTimeout(
      () => setShowGreeting(true),
      GREETING_SHOW_DELAY_MS,
    );
    const hideTimer = setTimeout(
      () => setShowGreeting(false),
      GREETING_SHOW_DELAY_MS + GREETING_VISIBLE_MS,
    );
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
            "Sorry, something went wrong. The API might still be starting up. Try again in a moment.",
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
      {/* Proactive greeting bubble - establishes up front that this is an
          AI-powered assistant, not a static help widget. */}
      {showGreeting && !open && (
        <div
          onClick={() => {
            setOpen(true);
            setShowGreeting(false);
          }}
          style={{
            position: "fixed",
            bottom: `${WIDGET_MARGIN + BUTTON_SIZE + PANEL_GAP}px`,
            right: `${WIDGET_MARGIN}px`,
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
            👋 I&apos;m an AI-powered assistant. Ask me anything about a
            stock, portfolio, or the market - I&apos;ll pull real data to
            answer.
          </div>
        </div>
      )}

      {/* Floating button - fixed to the bottom-right corner. Hidden while
          the mobile bottom sheet covers most of the screen - it has its
          own close button, and the corner button would otherwise float
          on top of the sheet's content. */}
      {!(isMobile && open) && (
        <button
          onClick={() => {
            setOpen((o) => !o);
            setShowGreeting(false);
          }}
          aria-label="Chat with the AEQUITAS AI analyst"
          title="Chat with the AEQUITAS AI analyst"
          style={{
            position: "fixed",
            bottom: `${WIDGET_MARGIN}px`,
            right: `${WIDGET_MARGIN}px`,
            width: `${BUTTON_SIZE}px`,
            height: `${BUTTON_SIZE}px`,
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
      )}

      {/* Chat panel - a full-width bottom sheet on phones (a 380px fixed
          panel doesn't fit, and doesn't feel native, on a 360-430px
          screen); anchored above the button, bottom-right, everywhere
          else. */}
      {open && (
        <div
          style={
            isMobile
              ? {
                  position: "fixed",
                  left: 0,
                  right: 0,
                  bottom: 0,
                  top: "12dvh",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "16px 16px 0 0",
                  display: "flex",
                  flexDirection: "column",
                  zIndex: 9997,
                  boxShadow: "0 -8px 48px rgba(0,0,0,0.4)",
                  overflow: "hidden",
                  paddingBottom: "env(safe-area-inset-bottom)",
                }
              : {
                  position: "fixed",
                  bottom: `${WIDGET_MARGIN + BUTTON_SIZE + PANEL_GAP}px`,
                  right: `${WIDGET_MARGIN}px`,
                  width: `${PANEL_W}px`,
                  height: `${PANEL_H}px`,
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "16px",
                  display: "flex",
                  flexDirection: "column",
                  zIndex: 9997,
                  boxShadow: "0 8px 48px rgba(0,0,0,0.4)",
                  overflow: "hidden",
                }
          }
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
                AI-powered · Groq · Real data
              </div>
            </div>
            {isMobile && (
              <button
                onClick={() => setOpen(false)}
                aria-label="Close chat"
                style={{
                  marginLeft: "auto",
                  width: "32px",
                  height: "32px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "none",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                  fontSize: "16px",
                  flexShrink: 0,
                }}
              >
                ✕
              </button>
            )}
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
                    whiteSpace: msg.role === "user" ? "pre-wrap" : "normal",
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
                  ) : msg.role === "user" ? (
                    msg.content
                  ) : (
                    <Markdown fontSize="13px">{msg.content}</Markdown>
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
