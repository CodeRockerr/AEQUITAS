"use client";

import { useEffect, useState, useCallback } from "react";
import { TRADING_FACTS } from "./facts";

interface LoadingScreenProps {
  onDismiss: () => void;
}

const TICKER_SYMBOLS = [
  "AAPL",
  "MSFT",
  "NVDA",
  "SPY",
  "TSLA",
  "AMZN",
  "META",
  "GOOGL",
  "BRK-B",
  "JPM",
  "NFLX",
  "AMD",
];
const MINI_GAME_DURATION = 20; // seconds
const FACT_ROTATE_MS = 8000; // now that the screen holds for 30-35s, cycle through several facts instead of showing one static fact the whole time
const GAME_RESTART_DELAY_MS = 4000; // pause on the score before auto-starting a new round

function useTypewriter(text: string, speed = 28) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    setDisplayed("");
    setDone(false);
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayed(text.slice(0, i + 1));
        i++;
      } else {
        setDone(true);
        clearInterval(timer);
      }
    }, speed);
    return () => clearInterval(timer);
  }, [text, speed]);

  return { displayed, done };
}

// ── Mini game: catch the rising ticker ──────────────────────────────────────
function TickerCatchGame({ onScore }: { onScore: (n: number) => void }) {
  const [score, setScore] = useState(0);
  const [tickers, setTickers] = useState<
    {
      id: number;
      symbol: string;
      x: number;
      y: number;
      speed: number;
      caught: boolean;
    }[]
  >([]);
  const [timeLeft, setTimeLeft] = useState(MINI_GAME_DURATION);
  const [over, setOver] = useState(false);
  const [highScore, setHighScore] = useState(() => {
    try {
      return parseInt(localStorage.getItem("aq_game_hi") ?? "0", 10);
    } catch {
      return 0;
    }
  });

  // Tracks "did THIS round just beat the high score" separately from a
  // score > highScore comparison, which would flicker: the game-over
  // effect below updates highScore to match score right after a new
  // best, which would immediately make that comparison false again.
  const [justBeatHighScore, setJustBeatHighScore] = useState(false);

  const restart = useCallback(() => {
    setTickers([]);
    setScore(0);
    setTimeLeft(MINI_GAME_DURATION);
    setOver(false);
    setJustBeatHighScore(false);
  }, []);

  // The loading screen now holds for 30-35s but a round only lasts
  // MINI_GAME_DURATION (20s) - auto-restart after a short pause on the
  // score instead of leaving a dead "game over" screen for the rest of
  // the wait. A visible "Play again" button lets anyone skip the pause.
  useEffect(() => {
    if (!over) return;
    const t = setTimeout(restart, GAME_RESTART_DELAY_MS);
    return () => clearTimeout(t);
  }, [over, restart]);

  useEffect(() => {
    if (over) return;
    const interval = setInterval(() => {
      setTickers((prev) => {
        const speed = 0.6 + Math.random() * 0.8;
        return [
          ...prev.filter((t) => t.y > -60),
          {
            id: Date.now(),
            symbol:
              TICKER_SYMBOLS[Math.floor(Math.random() * TICKER_SYMBOLS.length)],
            x: 8 + Math.random() * 80,
            y: 108,
            speed,
            caught: false,
          },
        ];
      });
    }, 1100);
    return () => clearInterval(interval);
  }, [over]);

  useEffect(() => {
    if (over) return;
    // `cancelled` is checked synchronously inside `tick` (unlike the `over`
    // state, which is a stale closure here and would never reflect updates
    // once this effect has run). Setting it in the cleanup guarantees the
    // recursive rAF chain actually stops on unmount or when the game ends,
    // instead of scheduling frames forever.
    let cancelled = false;
    let raf = requestAnimationFrame(function tick() {
      if (cancelled) return;
      setTickers((prev) =>
        prev.map((t) => (t.caught ? t : { ...t, y: t.y - t.speed * 0.25 })),
      );
      raf = requestAnimationFrame(tick);
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
  }, [over]);

  useEffect(() => {
    if (over) return;
    const timer = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) {
          setOver(true);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [over]);

  useEffect(() => {
    if (over) {
      onScore(score);
      try {
        // highScore is read once at mount; with auto-restart now enabled,
        // beating it in a later round needs to update the displayed value
        // too, not just localStorage.
        if (score > highScore) {
          localStorage.setItem("aq_game_hi", String(score));
          setHighScore(score);
          setJustBeatHighScore(true);
        }
      } catch {}
    }
  }, [over, score, onScore, highScore]);

  const catch_ = useCallback((id: number) => {
    setTickers((prev) =>
      prev.map((t) => (t.id === id ? { ...t, caught: true } : t)),
    );
    setScore((s) => s + 1);
  }, []);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "200px",
        background: "var(--bg-elevated)",
        borderRadius: "12px",
        border: "1px solid var(--border-subtle)",
        overflow: "hidden",
        cursor: "crosshair",
        userSelect: "none",
      }}
    >
      {/* Header */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          padding: "8px 12px",
          display: "flex",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--border-subtle)",
          background: "var(--bg-surface)",
          zIndex: 2,
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "11px",
            color: "var(--text-tertiary)",
          }}
        >
          Catch the tickers ◈
        </span>
        <div style={{ display: "flex", gap: "16px" }}>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--accent-green)",
            }}
          >
            {score} caught
          </span>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color:
                timeLeft <= 5 ? "var(--accent-red)" : "var(--text-tertiary)",
            }}
          >
            {timeLeft}s
          </span>
        </div>
      </div>

      {/* Game area */}
      <div
        style={{
          position: "absolute",
          inset: "36px 0 0 0",
          overflow: "hidden",
        }}
      >
        {!over ? (
          tickers
            .filter((t) => !t.caught && t.y > 0 && t.y < 108)
            .map((t) => (
              <button
                key={t.id}
                onClick={() => catch_(t.id)}
                style={{
                  position: "absolute",
                  left: `${t.x}%`,
                  top: `${t.y}%`,
                  transform: "translateX(-50%)",
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "3px 8px",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--accent-green)",
                  borderRadius: "4px",
                  color: "var(--accent-green)",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  transition: "opacity 0.1s",
                }}
              >
                {t.symbol}
              </button>
            ))
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              gap: "6px",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "20px",
                color: "var(--text-primary)",
              }}
            >
              {score} caught
            </div>
            {justBeatHighScore && score > 0 && (
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "11px",
                  color: "var(--accent-green)",
                }}
              >
                ▲ New high score!
              </div>
            )}
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                color: "var(--text-tertiary)",
              }}
            >
              High score: {Math.max(score, highScore)}
            </div>
            <button
              onClick={restart}
              style={{
                marginTop: "4px",
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--accent-green)",
                background: "none",
                border: "1px solid var(--accent-green)",
                borderRadius: "100px",
                padding: "4px 12px",
                cursor: "pointer",
              }}
            >
              Play again ↺
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main loading screen ──────────────────────────────────────────────────────
export function LoadingScreen({ onDismiss }: LoadingScreenProps) {
  // factIndex starts null (matches server output, avoiding a hydration
  // mismatch from Math.random() running separately on server and client)
  // and is picked once on mount. The typewriter gets "" until then, so it
  // never flashes one fact and then resets into a different one. With the
  // screen now holding for 30-35s, it then rotates to a new (never
  // immediately-repeated) fact every FACT_ROTATE_MS instead of sitting on
  // one static fact for the whole wait.
  const [factIndex, setFactIndex] = useState<number | null>(null);
  useEffect(() => {
    setFactIndex(Math.floor(Math.random() * TRADING_FACTS.length));

    const timer = setInterval(() => {
      setFactIndex((prev) => {
        if (TRADING_FACTS.length <= 1) return prev;
        let next = Math.floor(Math.random() * TRADING_FACTS.length);
        while (next === prev) {
          next = Math.floor(Math.random() * TRADING_FACTS.length);
        }
        return next;
      });
    }, FACT_ROTATE_MS);

    return () => clearInterval(timer);
  }, []);
  const fact = factIndex !== null ? TRADING_FACTS[factIndex] : null;
  const { displayed, done } = useTypewriter(fact?.fact ?? "");
  const [gameScore, setGameScore] = useState<number | null>(null);
  const [pulse, setPulse] = useState(true);
  const [dots, setDots] = useState(".");

  useEffect(() => {
    const t = setInterval(
      () => setDots((d) => (d.length >= 3 ? "." : d + ".")),
      500,
    );
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const t = setInterval(() => setPulse((p) => !p), 1200);
    return () => clearInterval(t);
  }, []);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Connecting to platform"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "var(--bg-surface)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      {/* Subtle grid background */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          backgroundImage:
            "linear-gradient(var(--border-subtle) 1px, transparent 1px), linear-gradient(90deg, var(--border-subtle) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          opacity: 0.35,
        }}
      />

      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: "520px",
          display: "flex",
          flexDirection: "column",
          gap: "20px",
        }}
      >
        {/* Wordmark + connecting status */}
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              fontFamily: "var(--font-serif)",
              fontSize: "clamp(28px, 6vw, 42px)",
              fontWeight: 400,
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
              lineHeight: 1.1,
              marginBottom: "8px",
            }}
          >
            Æquitas
          </div>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--text-tertiary)",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              marginBottom: "16px",
            }}
          >
            Quant Research Platform
          </div>
          {/* Animated connecting bar */}
          <div
            role="status"
            aria-live="polite"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              marginBottom: "4px",
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "var(--accent-green)",
                opacity: pulse ? 1 : 0.3,
                transition: "opacity 0.4s ease",
              }}
            />
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--text-tertiary)",
                letterSpacing: "0.06em",
              }}
            >
              Connecting to API{dots}
            </span>
          </div>
          <div
            style={{
              width: "200px",
              height: "2px",
              background: "var(--border-subtle)",
              borderRadius: "1px",
              margin: "8px auto 0",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: "40%",
                background: "var(--accent-green)",
                borderRadius: "1px",
                animation: "slide-progress 1.8s ease-in-out infinite",
              }}
            />
          </div>
        </div>

        {/* Why this takes a minute */}
        <p
          style={{
            textAlign: "center",
            fontFamily: "var(--font-sans)",
            fontSize: "12px",
            color: "var(--text-tertiary)",
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          I&apos;m a broke grad student, so this runs on free-tier hosting -
          the API is waking up from its nap and that takes a minute or two.
          Sorry! Play the game, read a fact, or go creep on my portfolio and
          resume below while you wait.
        </p>

        {/* Fun fact card */}
        <div
          style={{
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "12px",
            padding: "18px 20px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "10px",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "9px",
                letterSpacing: "0.1em",
                color: "var(--text-tertiary)",
                textTransform: "uppercase",
              }}
            >
              Did you know · {fact?.category ?? ""}
            </span>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                color: "var(--accent-green)",
              }}
            >
              ◈
            </span>
          </div>
          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "13px",
              color: "var(--text-secondary)",
              lineHeight: "1.7",
              margin: 0,
              minHeight: "60px",
            }}
          >
            {displayed}
            {!done && (
              <span
                style={{
                  opacity: 0.5,
                  animation: "blink 1s step-end infinite",
                }}
              >
                |
              </span>
            )}
          </p>
        </div>

        {/* Mini game */}
        <TickerCatchGame onScore={setGameScore} />
        {gameScore !== null && (
          <div
            style={{
              textAlign: "center",
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--text-tertiary)",
            }}
          >
            You caught {gameScore} tickers. The platform will be ready soon.
          </div>
        )}

        {/* Portfolio + resume links, skip */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <div
            style={{
              display: "flex",
              gap: "10px",
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            <a
              href="https://adit-2d-portfolio.vercel.app/"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--text-secondary)",
                padding: "8px 16px",
                border: "1px solid var(--border-subtle)",
                borderRadius: "100px",
                textDecoration: "none",
                background: "var(--bg-elevated)",
                transition: "border-color 0.15s, color 0.15s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor =
                  "var(--accent-green)";
                (e.currentTarget as HTMLElement).style.color =
                  "var(--accent-green)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor =
                  "var(--border-subtle)";
                (e.currentTarget as HTMLElement).style.color =
                  "var(--text-secondary)";
              }}
            >
              <span>◉</span>
              <span>Built by Adit Shah, view portfolio</span>
              <span style={{ opacity: 0.5 }}>↗</span>
            </a>

            <a
              href="https://drive.google.com/file/d/1JdZfo_4qNAXY7i3eR5bb7H5pSvyslel4/view?usp=sharing"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--text-secondary)",
                padding: "8px 16px",
                border: "1px solid var(--border-subtle)",
                borderRadius: "100px",
                textDecoration: "none",
                background: "var(--bg-elevated)",
                transition: "border-color 0.15s, color 0.15s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor =
                  "var(--accent-green)";
                (e.currentTarget as HTMLElement).style.color =
                  "var(--accent-green)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor =
                  "var(--border-subtle)";
                (e.currentTarget as HTMLElement).style.color =
                  "var(--text-secondary)";
              }}
            >
              <span>◈</span>
              <span>Hiring? View resume</span>
              <span style={{ opacity: 0.5 }}>↗</span>
            </a>
          </div>

          <button
            onClick={onDismiss}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--text-tertiary)",
              background: "none",
              border: "none",
              cursor: "pointer",
              letterSpacing: "0.04em",
              padding: "4px 8px",
              textDecoration: "underline",
              textDecorationColor: "var(--border-subtle)",
            }}
          >
            Skip → enter platform
          </button>
        </div>
      </div>

      <style>{`
        @keyframes slide-progress {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(200%); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
      `}</style>
    </div>
  );
}
