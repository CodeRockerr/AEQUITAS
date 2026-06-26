"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { CandlestickChart } from "@/components/charts/CandlestickChart";
import {
  signalsApi,
  mlApi,
  historyApi,
  type SignalResponse,
  type RegimeResponse,
  type ForecastResponse,
  type HistoryResponse,
} from "@/lib/api";

const TICKERS = ["AAPL", "MSFT", "SPY", "NVDA", "TSLA"];
const RANGES = [
  { id: "1mo", label: "1M" },
  { id: "6mo", label: "6M" },
  { id: "1y", label: "1Y" },
  { id: "5y", label: "5Y" },
  { id: "max", label: "All" },
] as const;

export default function DashboardPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [searchInput, setSearchInput] = useState("");
  const [range, setRange] = useState<(typeof RANGES)[number]["id"]>("1y");

  const [signals, setSignals] = useState<SignalResponse | null>(null);
  const [regime, setRegime] = useState<RegimeResponse | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chartError, setChartError] = useState<string | null>(null);

  async function load(t: string) {
    setLoading(true);
    setError(null);
    try {
      const [sig, reg, fore] = await Promise.all([
        signalsApi.get(t),
        mlApi.regime(t),
        mlApi.forecast(t),
      ]);
      setSignals(sig);
      setRegime(reg);
      setForecast(fore);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  async function loadHistory(t: string, r: typeof range) {
    setChartLoading(true);
    setChartError(null);
    try {
      const h = await historyApi.get(t, r);
      setHistory(h);
    } catch (e) {
      setChartError(
        e instanceof Error ? e.message : "Failed to load price history",
      );
      setHistory(null);
    } finally {
      setChartLoading(false);
    }
  }

  useEffect(() => {
    void load(ticker);
    void loadHistory(ticker, range);
  }, [ticker]);
  useEffect(() => {
    void loadHistory(ticker, range);
  }, [range]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const t = searchInput.trim().toUpperCase();
    if (t) {
      setTicker(t);
      setSearchInput("");
    }
  }

  const signalVariant = (v: number): "green" | "red" | "amber" | "neutral" =>
    v > 0.3 ? "green" : v < -0.3 ? "red" : v !== 0 ? "amber" : "neutral";

  const regimeVariant = (r: string): "green" | "red" | "amber" | "neutral" =>
    r === "Bull"
      ? "green"
      : r === "Bear"
        ? "red"
        : r === "High Volatility"
          ? "amber"
          : "neutral";

  return (
    <div style={{ minHeight: "100vh" }}>
      <PageHeader title="Dashboard" subtitle="LIVE QUANTITATIVE SIGNALS">
        <form onSubmit={handleSearch} style={{ display: "flex", gap: "6px" }}>
          <input
            className="input"
            placeholder="Search any ticker..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            style={{ width: "160px" }}
          />
          <button
            type="submit"
            className="btn btn-primary"
            style={{ fontSize: "11px" }}
          >
            Search →
          </button>
        </form>
      </PageHeader>

      <div style={{ padding: "32px 40px" }}>
        {/* Quick ticker buttons */}
        <div style={{ display: "flex", gap: "6px", marginBottom: "24px" }}>
          {TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => setTicker(t)}
              className="btn"
              style={{
                background:
                  t === ticker ? "var(--text-primary)" : "transparent",
                color:
                  t === ticker
                    ? "var(--text-inverse)"
                    : "var(--text-secondary)",
                borderColor:
                  t === ticker
                    ? "var(--text-primary)"
                    : "var(--border-default)",
                padding: "6px 12px",
                fontSize: "11px",
              }}
            >
              {t}
            </button>
          ))}
          {!TICKERS.includes(ticker) && <Badge variant="blue">{ticker}</Badge>}
        </div>

        {/* Price History Chart */}
        <div
          className="card animate-fade-up"
          style={{ padding: "24px", marginBottom: "24px" }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "16px",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "10px",
                  letterSpacing: "0.1em",
                  color: "var(--text-tertiary)",
                  textTransform: "uppercase",
                  marginBottom: "4px",
                }}
              >
                Price History · {ticker}
              </div>
              {history && (
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--text-tertiary)",
                  }}
                >
                  {history.first_date?.slice(0, 10)} →{" "}
                  {history.last_date?.slice(0, 10)} · {history.n_candles}{" "}
                  candles
                </div>
              )}
            </div>
            <div style={{ display: "flex", gap: "4px" }}>
              {RANGES.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setRange(r.id)}
                  className="btn"
                  style={{
                    background:
                      r.id === range ? "var(--text-primary)" : "transparent",
                    color:
                      r.id === range
                        ? "var(--text-inverse)"
                        : "var(--text-secondary)",
                    borderColor:
                      r.id === range
                        ? "var(--text-primary)"
                        : "var(--border-default)",
                    padding: "5px 12px",
                    fontSize: "11px",
                  }}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          {chartError && (
            <div
              style={{
                background: "var(--accent-red-bg)",
                border:
                  "1px solid color-mix(in srgb, var(--accent-red) 30%, transparent)",
                borderRadius: "var(--radius-md)",
                padding: "12px 16px",
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--accent-red)",
              }}
            >
              {chartError}
            </div>
          )}

          {chartLoading ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "60px 0",
                justifyContent: "center",
              }}
            >
              <Spinner size={20} />
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "12px",
                  color: "var(--text-tertiary)",
                }}
              >
                Loading {ticker} history...
              </span>
            </div>
          ) : history && history.candles.length > 0 ? (
            <CandlestickChart candles={history.candles} height={420} />
          ) : null}
        </div>

        {error && (
          <div
            style={{
              background: "var(--accent-red-bg)",
              border:
                "1px solid color-mix(in srgb, var(--accent-red) 30%, transparent)",
              borderRadius: "var(--radius-md)",
              padding: "12px 16px",
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              color: "var(--accent-red)",
              marginBottom: "24px",
            }}
          >
            {error} — Make sure {ticker} is a valid ticker symbol.
          </div>
        )}

        {loading ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "40px 0",
            }}
          >
            <Spinner size={20} />
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                color: "var(--text-tertiary)",
              }}
            >
              Loading {ticker} signals...
            </span>
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                gap: "12px",
                marginBottom: "32px",
              }}
            >
              <StatCard
                label="Regime"
                value={regime?.current_regime ?? "—"}
                sub={
                  regime
                    ? `${(regime.current_regime_prob * 100).toFixed(0)}% confidence`
                    : undefined
                }
                accent={
                  regime ? regimeVariant(regime.current_regime) : "neutral"
                }
                delay={0}
              />
              <StatCard
                label="Signal"
                value={signals ? signals.direction.toUpperCase() : "—"}
                sub={
                  signals
                    ? `Score: ${signals.combined_signal.toFixed(3)}`
                    : undefined
                }
                accent={
                  signals ? signalVariant(signals.combined_signal) : "neutral"
                }
                delay={60}
              />
              <StatCard
                label="ML Forecast"
                value={forecast?.predicted_return_pct ?? "—"}
                sub={
                  forecast
                    ? `${forecast.direction} · ${(forecast.confidence * 100).toFixed(0)}% conf`
                    : undefined
                }
                accent={
                  forecast
                    ? forecast.direction === "up"
                      ? "green"
                      : "red"
                    : "neutral"
                }
                delay={120}
              />
              <StatCard
                label="Dir. Accuracy"
                value={forecast?.model_metrics.directional_accuracy ?? "—"}
                sub="XGBoost model"
                delay={180}
              />
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
                marginBottom: "16px",
              }}
            >
              {signals && (
                <div
                  className="card animate-fade-up"
                  style={{ padding: "24px" }}
                >
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      letterSpacing: "0.1em",
                      color: "var(--text-tertiary)",
                      textTransform: "uppercase",
                      marginBottom: "16px",
                    }}
                  >
                    Signal Breakdown · {ticker}
                  </div>

                  {[
                    { name: "RSI", signal: signals.signals.rsi },
                    { name: "MACD", signal: signals.signals.macd },
                    { name: "Bollinger", signal: signals.signals.bollinger },
                  ].map(({ name, signal }) => (
                    <div
                      key={name}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "10px 0",
                        borderBottom: "1px solid var(--border-subtle)",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "12px",
                            color: "var(--text-primary)",
                            marginBottom: "2px",
                          }}
                        >
                          {name}
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10px",
                            color: "var(--text-tertiary)",
                            maxWidth: "220px",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {signal.note}
                        </div>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                        }}
                      >
                        <div
                          style={{
                            width: "80px",
                            height: "4px",
                            background: "var(--border-subtle)",
                            borderRadius: "2px",
                            position: "relative",
                            overflow: "hidden",
                          }}
                        >
                          <div
                            style={{
                              position: "absolute",
                              height: "100%",
                              borderRadius: "2px",
                              background:
                                signal.value > 0
                                  ? "var(--accent-green)"
                                  : "var(--accent-red)",
                              width: `${Math.abs(signal.value) * 100}%`,
                              left:
                                signal.value >= 0
                                  ? "50%"
                                  : `${50 - Math.abs(signal.value) * 50}%`,
                            }}
                          />
                          <div
                            style={{
                              position: "absolute",
                              left: "50%",
                              top: 0,
                              bottom: 0,
                              width: "1px",
                              background: "var(--border-strong)",
                            }}
                          />
                        </div>
                        <Badge variant={signalVariant(signal.value)}>
                          {signal.value >= 0 ? "+" : ""}
                          {signal.value.toFixed(3)}
                        </Badge>
                      </div>
                    </div>
                  ))}

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      paddingTop: "12px",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        color: "var(--text-secondary)",
                        letterSpacing: "0.04em",
                      }}
                    >
                      COMBINED
                    </span>
                    <Badge variant={signalVariant(signals.combined_signal)}>
                      {signals.combined_signal >= 0 ? "+" : ""}
                      {signals.combined_signal.toFixed(4)}
                    </Badge>
                  </div>
                </div>
              )}

              {forecast && forecast.top_drivers.length > 0 && (
                <div
                  className="card animate-fade-up anim-delay-2"
                  style={{ padding: "24px" }}
                >
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      letterSpacing: "0.1em",
                      color: "var(--text-tertiary)",
                      textTransform: "uppercase",
                      marginBottom: "16px",
                    }}
                  >
                    SHAP Drivers · Top 5
                  </div>

                  {forecast.top_drivers.map((d, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "8px 0",
                        borderBottom:
                          i < forecast.top_drivers.length - 1
                            ? "1px solid var(--border-subtle)"
                            : "none",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "12px",
                            color: "var(--text-primary)",
                          }}
                        >
                          {d.feature}
                        </div>
                        <div
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "10px",
                            color: d.direction.includes("bullish")
                              ? "var(--accent-green)"
                              : "var(--accent-red)",
                            marginTop: "1px",
                          }}
                        >
                          {d.direction}
                        </div>
                      </div>
                      <div
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "12px",
                          color:
                            d.shap_value >= 0
                              ? "var(--accent-green)"
                              : "var(--accent-red)",
                        }}
                      >
                        {d.shap_value >= 0 ? "+" : ""}
                        {d.shap_value.toFixed(4)}
                      </div>
                    </div>
                  ))}

                  <div
                    style={{
                      marginTop: "16px",
                      padding: "10px 12px",
                      background: "var(--bg-elevated)",
                      borderRadius: "var(--radius-md)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      color: "var(--text-tertiary)",
                      lineHeight: "1.6",
                    }}
                  >
                    MAE: {forecast.model_metrics.mae.toFixed(4)} · RMSE:{" "}
                    {forecast.model_metrics.rmse.toFixed(4)} · Dir:{" "}
                    {forecast.model_metrics.directional_accuracy}
                  </div>
                </div>
              )}
            </div>

            {regime && (
              <div
                className="card animate-fade-up anim-delay-3"
                style={{ padding: "24px" }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "16px",
                  }}
                >
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      letterSpacing: "0.1em",
                      color: "var(--text-tertiary)",
                      textTransform: "uppercase",
                    }}
                  >
                    Regime Sequence · Last 60 Days
                  </div>
                  <Badge variant={regimeVariant(regime.current_regime)}>
                    Current: {regime.current_regime}
                  </Badge>
                </div>

                <div style={{ display: "flex", gap: "2px", flexWrap: "wrap" }}>
                  {regime.regime_sequence.map((r, i) => (
                    <div
                      key={i}
                      title={r}
                      style={{
                        width: "12px",
                        height: "24px",
                        borderRadius: "2px",
                        background:
                          r === "Bull"
                            ? "var(--accent-green)"
                            : r === "Bear"
                              ? "var(--accent-red)"
                              : "var(--accent-amber)",
                        opacity: 0.7,
                        flexShrink: 0,
                      }}
                    />
                  ))}
                </div>

                <div
                  style={{ display: "flex", gap: "16px", marginTop: "12px" }}
                >
                  {[
                    { label: "Bull", color: "var(--accent-green)" },
                    { label: "Bear", color: "var(--accent-red)" },
                    { label: "High Vol", color: "var(--accent-amber)" },
                  ].map(({ label, color }) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <div
                        style={{
                          width: "8px",
                          height: "8px",
                          borderRadius: "2px",
                          background: color,
                          opacity: 0.7,
                        }}
                      />
                      <span
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "10px",
                          color: "var(--text-tertiary)",
                        }}
                      >
                        {label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
