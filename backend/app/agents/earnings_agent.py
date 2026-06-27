"""
AEQUITAS — Earnings analysis agent.

Real earnings call transcripts require paid data providers ($50+/month
for most APIs). Instead, this agent synthesizes an earnings analysis
from: (1) Finnhub's earnings calendar (actual vs estimated EPS/revenue,
beat/miss history), (2) recent earnings-related news coverage, and
(3) basic company fundamentals — giving a genuinely useful "earnings
analysis" without needing a transcript API subscription.

Standalone agent, same composable pattern as the news sentiment agent.
"""

from dataclasses import dataclass, field

import structlog

from app.services.finnhub_client import (
    get_basic_financials,
    get_company_news,
    get_earnings_calendar,
)

log = structlog.get_logger()


@dataclass
class EarningsHistoryEntry:
    date: str
    quarter: str
    eps_actual: float | None
    eps_estimate: float | None
    eps_surprise_pct: float | None
    revenue_actual: float | None
    revenue_estimate: float | None


@dataclass
class EarningsAnalysisResult:
    ticker: str
    next_earnings_date: str | None
    last_earnings_beat: bool | None
    last_eps_surprise_pct: float | None
    guidance_sentiment: str  # "positive" | "negative" | "mixed" | "unknown"
    analysis: str  # LLM-written narrative
    key_metrics: dict
    earnings_history: list[EarningsHistoryEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _safe_surprise_pct(actual: float | None, estimate: float | None) -> float | None:
    if actual is None or estimate is None or estimate == 0:
        return None
    return round(((actual - estimate) / abs(estimate)) * 100, 2)


async def run_earnings_agent(ticker: str, llm_call) -> EarningsAnalysisResult:
    """
    Run the earnings analysis agent for a ticker.

    Args:
        ticker: stock symbol
        llm_call: async function (system: str, user: str, max_tokens: int) -> str
    """
    ticker = ticker.upper()
    errors: list[str] = []

    calendar = await get_earnings_calendar(ticker)
    financials = await get_basic_financials(ticker)
    news = await get_company_news(ticker, days_back=21)

    if not calendar:
        errors.append(f"No earnings calendar data found for {ticker}.")

    # Sort by date, separate past (with actuals) from future
    past_entries = [e for e in calendar if e.get("epsActual") is not None]
    future_entries = [e for e in calendar if e.get("epsActual") is None]

    past_entries.sort(key=lambda e: e.get("date", ""), reverse=True)
    future_entries.sort(key=lambda e: e.get("date", ""))

    next_date = future_entries[0].get("date") if future_entries else None
    last_entry = past_entries[0] if past_entries else None

    last_surprise_pct = None
    last_beat = None
    if last_entry:
        last_surprise_pct = _safe_surprise_pct(
            last_entry.get("epsActual"), last_entry.get("epsEstimate")
        )
        if last_surprise_pct is not None:
            last_beat = last_surprise_pct > 0

    history = [
        EarningsHistoryEntry(
            date=e.get("date", ""),
            quarter=f"Q{e.get('quarter', '?')} {e.get('year', '?')}",
            eps_actual=e.get("epsActual"),
            eps_estimate=e.get("epsEstimate"),
            eps_surprise_pct=_safe_surprise_pct(
                e.get("epsActual"), e.get("epsEstimate")
            ),
            revenue_actual=e.get("revenueActual"),
            revenue_estimate=e.get("revenueEstimate"),
        )
        for e in past_entries[:4]
    ]

    # Filter news for earnings-related keywords to find guidance commentary
    earnings_keywords = ("earnings", "guidance", "quarter", "eps", "revenue", "outlook")
    earnings_news = [
        n
        for n in news
        if any(kw in n.get("headline", "").lower() for kw in earnings_keywords)
    ][:10]

    news_summary = (
        "\n".join(
            f"- [{n.get('source', 'Unknown')}] {n.get('headline', '')}"
            for n in earnings_news
        )
        if earnings_news
        else "No recent earnings-related news coverage found."
    )

    history_summary = (
        "\n".join(
            f"- {h.quarter}: EPS {h.eps_actual} vs est. {h.eps_estimate} "
            f"({'+' if (h.eps_surprise_pct or 0) >= 0 else ''}{h.eps_surprise_pct}% surprise)"
            for h in history
        )
        if history
        else "No historical earnings data available."
    )

    key_metrics: dict = {}
    if financials:
        metrics = financials.get("metric", {})
        key_metrics = {
            "pe_ratio": metrics.get("peNormalizedAnnual"),
            "revenue_growth_yoy": metrics.get("revenueGrowthTTMYoy"),
            "eps_growth_yoy": metrics.get("epsGrowthTTMYoy"),
            "gross_margin": metrics.get("grossMarginTTM"),
            "net_margin": metrics.get("netProfitMarginTTM"),
        }

    metrics_summary = (
        "\n".join(
            f"- {k.replace('_', ' ').title()}: {v}"
            for k, v in key_metrics.items()
            if v is not None
        )
        if key_metrics
        else "No fundamental metrics available."
    )

    response_text = await llm_call(
        system=(
            "You are an equity research analyst specialising in earnings analysis. "
            "Given a company's earnings history, recent earnings-related news, and "
            "key fundamentals, write a concise earnings analysis covering: "
            "recent performance trend, guidance sentiment, and what to watch for "
            "next quarter. "
            "End your response with exactly one line: "
            "GUIDANCE: positive|negative|mixed|unknown"
        ),
        user=(
            f"Ticker: {ticker}\n\n"
            f"=== EARNINGS HISTORY (last 4 quarters) ===\n{history_summary}\n\n"
            f"=== RECENT EARNINGS-RELATED NEWS ===\n{news_summary}\n\n"
            f"=== KEY FUNDAMENTALS ===\n{metrics_summary}\n\n"
            "Write a 250-350 word earnings analysis."
        ),
        max_tokens=600,
    )

    guidance_sentiment = "unknown"
    analysis = response_text.strip()
    for line in response_text.splitlines():
        if line.upper().strip().startswith("GUIDANCE:"):
            val = line.split(":", 1)[1].strip().lower()
            if val in ("positive", "negative", "mixed", "unknown"):
                guidance_sentiment = val
            analysis = response_text.replace(line, "").strip()

    return EarningsAnalysisResult(
        ticker=ticker,
        next_earnings_date=next_date,
        last_earnings_beat=last_beat,
        last_eps_surprise_pct=last_surprise_pct,
        guidance_sentiment=guidance_sentiment,
        analysis=analysis,
        key_metrics=key_metrics,
        earnings_history=history,
        errors=errors,
    )
