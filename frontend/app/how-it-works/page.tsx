"use client";

import { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";

interface Topic {
  id: string;
  icon: string;
  title: string;
  hook: string;
  explanation: string;
  href: string;
  linkLabel: string;
}

const TOPICS: Topic[] = [
  {
    id: "signals",
    icon: "◈",
    title: "Momentum Signals",
    hook: "Is this stock hot or cold right now?",
    explanation:
      "RSI is a speedometer for buying pressure - it says whether a stock has been bought up too fast (\"overbought\") or beaten down too hard (\"oversold\"). MACD checks whether the fast-moving average and the slow-moving average agree on direction. Bollinger Bands watch whether the price has stretched outside its normal comfort zone. Combine all three into one score from -1 (bearish) to +1 (bullish) and you get a quick read on the crowd's mood.",
    href: "/dashboard",
    linkLabel: "See live signals on the Dashboard",
  },
  {
    id: "regime",
    icon: "◐",
    title: "Market Regime Detection",
    hook: "Is the market in a good mood or a bad one?",
    explanation:
      "A Hidden Markov Model (HMM) is a way of guessing an invisible state from the clues it leaves behind - here, whether the market is quietly Bullish, nervously Bearish, or just plain chaotic (High-Volatility), inferred purely from the pattern of recent returns. Think of it as a mood ring for the whole market: you can't see the mood directly, but you can read it from how the price has been behaving.",
    href: "/dashboard",
    linkLabel: "Check today's regime on the Dashboard",
  },
  {
    id: "forecast",
    icon: "◑",
    title: "ML Forecast, With Receipts",
    hook: "A machine's best guess at tomorrow, and its reasoning.",
    explanation:
      "An XGBoost model looks at 19 engineered features (momentum, volatility, volume patterns, and more) and predicts which way the price is likely to move next. The model is tested the honest way (TimeSeriesSplit) so it's never accidentally allowed to peek at the future while training. SHAP then opens the black box and shows exactly which features pushed the prediction up or down - the difference between a doctor just saying \"you'll be fine\" and a doctor showing you the actual chart.",
    href: "/dashboard",
    linkLabel: "See a live forecast + SHAP breakdown",
  },
  {
    id: "risk",
    icon: "◬",
    title: "Risk & Options Pricing",
    hook: "How much could you actually lose - and what's that option really worth?",
    explanation:
      "Value at Risk (VaR) answers \"on a bad-but-not-catastrophic day, about how much might I lose?\" - computed three different ways (historical, parametric, Monte Carlo) so you can sanity-check one against another. Black-Scholes is the classic formula options traders use to price a bet on where a stock will be by a certain date, plus the Greeks - Delta, Gamma, Vega, Theta, Rho - which are just dials showing how that price reacts if the stock moves, time passes, or volatility shifts.",
    href: "/risk",
    linkLabel: "Compute VaR and price an option",
  },
  {
    id: "portfolio",
    icon: "◒",
    title: "Portfolio Construction",
    hook: "How do you not put all your eggs in one basket - mathematically?",
    explanation:
      "Mean-variance optimisation searches for the mix of stocks that gets you the best return for the least amount of bumpiness (volatility), tracing out an \"efficient frontier\" of good trade-offs. Cointegration testing hunts for pairs of stocks that tend to move together like dance partners, so that when they drift apart further than usual, a pairs trade bets on them snapping back.",
    href: "/agents",
    linkLabel: "Build a portfolio on the Agents page",
  },
  {
    id: "agents",
    icon: "◧",
    title: "The AI Research Team",
    hook: "Four AI \"employees,\" each with one job, handing off to the next.",
    explanation:
      "A LangGraph pipeline runs a company through an assembly line: Research reads real SEC filings and news, Quant crunches the regime/signal/forecast numbers, Thesis writes up a structured investment case citing both, and Critic tries to poke holes in it - unsupported claims, missing risks, contradictions - and sends it back for a rewrite if it's not convincing. Only an approved thesis reaches you.",
    href: "/theses",
    linkLabel: "Generate a thesis and watch the pipeline run",
  },
  {
    id: "backtesting",
    icon: "◫",
    title: "Backtesting",
    hook: "Time travel for trading strategies.",
    explanation:
      "Rewind to the past, pretend you traded a strategy (RSI mean-reversion, MACD crossover, Bollinger bands) every single day using only the information that would have actually been available at the time, and see the full tearsheet: total return, Sharpe ratio, max drawdown, win rate - the honest answer to \"would this have actually worked?\"",
    href: "/backtests",
    linkLabel: "Run a backtest",
  },
  {
    id: "cpp",
    icon: "◭",
    title: "The C++ Speed Boost",
    hook: "Same math, a much faster engine underneath.",
    explanation:
      "Python is friendly to write but slow at raw number-crunching. The busiest calculations - rolling averages, RSI, ATR - got reimplemented in C++20 and wired back into Python via pybind11, with zero-copy access to the same NumPy arrays. The app still feels like Python; the hot loops underneath just run 1.3x-40x faster, verified to agree with the original pandas output to within a tiny rounding error.",
    href: "/performance",
    linkLabel: "Watch pandas race C++ live",
  },
  {
    id: "streaming",
    icon: "◎",
    title: "Real-Time Price Streaming",
    hook: "Prices that update while you watch, not just when you refresh.",
    explanation:
      "A WebSocket connection pushes new prices to your browser as they arrive, like a live scoreboard instead of a printed program you have to go fetch again. Search a ticker nobody's looked at before and the platform quietly fetches and stores its history in the background - no manual setup step required.",
    href: "/dashboard",
    linkLabel: "Watch prices update live",
  },
];

const GLOSSARY: { term: string; def: string }[] = [
  { term: "RSI", def: "Relative Strength Index - momentum speedometer, 0-100." },
  { term: "MACD", def: "Moving Average Convergence/Divergence - trend-following momentum." },
  { term: "VaR", def: "Value at Risk - your likely worst-case loss on a normal bad day." },
  { term: "Sharpe ratio", def: "Return per unit of bumpiness - higher is smoother sailing." },
  { term: "SHAP", def: "Explains which input features drove a model's prediction, and by how much." },
  { term: "HMM", def: "Hidden Markov Model - infers an unseen state from observable clues." },
  { term: "GIL", def: "Python's Global Interpreter Lock - normally lets only one thread run Python at a time; C++ code can release it." },
  { term: "TWAP / VWAP", def: "Ways to split a big order into smaller pieces over time so you don't move the price against yourself." },
];

export default function HowItWorksPage() {
  const [expanded, setExpanded] = useState<string | null>(TOPICS[0].id);

  return (
    <div>
      <PageHeader
        title="How It Works"
        subtitle="THE MODELS, ALGORITHMS & TRICKS BEHIND AEQUITAS, IN PLAIN ENGLISH"
        serif
      />

      <div
        style={{
          padding: "32px clamp(16px, 5vw, 40px)",
          display: "grid",
          gap: 24,
          maxWidth: 880,
        }}
      >
        <p
          style={{
            fontFamily: "var(--font-sans)",
            fontSize: 14,
            color: "var(--text-secondary)",
            lineHeight: 1.7,
          }}
        >
          Every number on this site comes from a real algorithm, not a
          hardcoded placeholder. Here&apos;s what&apos;s actually running
          under the hood - tap a card to open it up.
        </p>

        <div style={{ display: "grid", gap: 12 }}>
          {TOPICS.map((topic) => {
            const isOpen = expanded === topic.id;
            return (
              <div
                key={topic.id}
                className="card animate-fade-up"
                style={{ overflow: "hidden" }}
              >
                <button
                  onClick={() => setExpanded(isOpen ? null : topic.id)}
                  aria-expanded={isOpen}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                    padding: "16px 20px",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    textAlign: "left",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 20,
                      color: "var(--accent-green)",
                      flexShrink: 0,
                      width: 24,
                    }}
                  >
                    {topic.icon}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: 15,
                        fontWeight: 600,
                        color: "var(--text-primary)",
                      }}
                    >
                      {topic.title}
                    </div>
                    <div
                      style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: 13,
                        color: "var(--text-secondary)",
                        marginTop: 2,
                      }}
                    >
                      {topic.hook}
                    </div>
                  </div>
                  <span
                    aria-hidden="true"
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 13,
                      color: "var(--text-tertiary)",
                      transform: isOpen ? "rotate(180deg)" : "none",
                      transition: "transform var(--duration-fast)",
                      flexShrink: 0,
                    }}
                  >
                    ▾
                  </span>
                </button>

                {isOpen && (
                  <div
                    className="animate-fade-in"
                    style={{
                      padding: "0 20px 20px 58px",
                      display: "grid",
                      gap: 12,
                    }}
                  >
                    <p
                      style={{
                        fontFamily: "var(--font-sans)",
                        fontSize: 13,
                        color: "var(--text-secondary)",
                        lineHeight: 1.7,
                        margin: 0,
                      }}
                    >
                      {topic.explanation}
                    </p>
                    <Link
                      href={topic.href}
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 12,
                        color: "var(--accent-green)",
                        textDecoration: "none",
                        letterSpacing: "0.02em",
                      }}
                    >
                      {topic.linkLabel} →
                    </Link>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <div style={{ marginTop: 8 }}>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              letterSpacing: "0.1em",
              color: "var(--text-tertiary)",
              textTransform: "uppercase",
              marginBottom: 12,
            }}
          >
            Quick Glossary
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
              gap: 10,
            }}
          >
            {GLOSSARY.map((g) => (
              <div
                key={g.term}
                className="card"
                style={{ padding: "12px 14px" }}
              >
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 12,
                    fontWeight: 600,
                    color: "var(--accent-blue)",
                    marginBottom: 3,
                  }}
                >
                  {g.term}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-sans)",
                    fontSize: 12,
                    color: "var(--text-secondary)",
                    lineHeight: 1.5,
                  }}
                >
                  {g.def}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
