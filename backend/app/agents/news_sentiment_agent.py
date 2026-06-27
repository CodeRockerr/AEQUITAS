"""
AEQUITAS — News sentiment agent.

Pulls recent news for a ticker from Finnhub, scores sentiment using
an LLM (since Finnhub's pre-computed sentiment endpoint requires a
paid plan), and detects whether sentiment is improving, worsening,
or stable compared to the prior period.

This is a standalone agent — not part of the LangGraph research
graph — but its output is structured to be easily fed into the
research agent's thesis generation as supplementary context.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

from app.services.finnhub_client import get_company_news, get_news_sentiment

log = structlog.get_logger()

MAX_HEADLINES_FOR_LLM = 15


@dataclass
class NewsArticleSummary:
    headline: str
    source: str
    url: str
    published: str  # ISO date string


@dataclass
class NewsSentimentResult:
    ticker: str
    sentiment: str  # "bullish" | "bearish" | "neutral"
    sentiment_score: float  # -1.0 to +1.0
    trend: str  # "improving" | "worsening" | "stable"
    confidence: float
    summary: str  # LLM-written narrative summary
    key_themes: list[str]
    recent_articles: list[NewsArticleSummary] = field(default_factory=list)
    finnhub_sentiment_available: bool = False
    errors: list[str] = field(default_factory=list)


def _format_headlines_for_prompt(articles: list[dict]) -> str:
    lines = []
    for a in articles[:MAX_HEADLINES_FOR_LLM]:
        headline = a.get("headline", "").strip()
        source = a.get("source", "Unknown")
        if headline:
            lines.append(f"- [{source}] {headline}")
    return "\n".join(lines) if lines else "No recent headlines available."


async def run_news_sentiment_agent(ticker: str, llm_call) -> NewsSentimentResult:
    """
    Run the news sentiment agent for a ticker.

    Args:
        ticker: stock symbol
        llm_call: async function (system: str, user: str, max_tokens: int) -> str
                  — injected so this module doesn't depend on a specific
                  LLM provider implementation (Groq, in our case)
    """
    ticker = ticker.upper()
    errors: list[str] = []

    articles = await get_company_news(ticker, days_back=14)
    older_articles = await get_company_news(ticker, days_back=30)
    # Articles from 14-30 days ago, for trend comparison
    older_only = [a for a in older_articles if a not in articles][
        :MAX_HEADLINES_FOR_LLM
    ]

    if not articles:
        errors.append(f"No recent news found for {ticker} via Finnhub.")

    finnhub_sentiment = await get_news_sentiment(ticker)
    finnhub_available = finnhub_sentiment is not None

    recent_summary = _format_headlines_for_prompt(articles)
    older_summary = (
        _format_headlines_for_prompt(older_only)
        if older_only
        else "No older headlines available for comparison."
    )

    finnhub_context = ""
    if finnhub_sentiment:
        bullish_pct = finnhub_sentiment.get("sentiment", {}).get(
            "bullishPercent", "N/A"
        )
        bearish_pct = finnhub_sentiment.get("sentiment", {}).get(
            "bearishPercent", "N/A"
        )
        finnhub_context = (
            f"\n\nFinnhub pre-computed sentiment: "
            f"{bullish_pct}% bullish, {bearish_pct}% bearish.\n"
        )

    response_text = await llm_call(
        system=(
            "You are a financial news analyst. Given recent headlines about a company, "
            "assess overall sentiment and identify key themes. "
            "Respond ONLY in this exact format, nothing else:\n"
            "SENTIMENT: bullish|bearish|neutral\n"
            "SCORE: <number between -1.0 and 1.0>\n"
            "TREND: improving|worsening|stable\n"
            "CONFIDENCE: <number between 0.0 and 1.0>\n"
            "THEMES: theme1, theme2, theme3\n"
            "SUMMARY: <2-3 sentence narrative summary>"
        ),
        user=(
            f"Ticker: {ticker}\n\n"
            f"=== RECENT HEADLINES (last 14 days) ===\n{recent_summary}\n\n"
            f"=== OLDER HEADLINES (14-30 days ago, for trend comparison) ===\n{older_summary}"
            f"{finnhub_context}"
        ),
        max_tokens=400,
    )

    sentiment, score, trend, confidence, themes, summary = _parse_llm_response(
        response_text
    )

    article_summaries = [
        NewsArticleSummary(
            headline=a.get("headline", ""),
            source=a.get("source", "Unknown"),
            url=a.get("url", ""),
            published=datetime.fromtimestamp(a.get("datetime", 0), tz=UTC).isoformat()
            if a.get("datetime")
            else "",
        )
        for a in articles[:10]
    ]

    return NewsSentimentResult(
        ticker=ticker,
        sentiment=sentiment,
        sentiment_score=score,
        trend=trend,
        confidence=confidence,
        summary=summary,
        key_themes=themes,
        recent_articles=article_summaries,
        finnhub_sentiment_available=finnhub_available,
        errors=errors,
    )


def _parse_llm_response(text: str) -> tuple[str, float, str, float, list[str], str]:
    """
    Parse the structured LLM response into typed fields.

    Falls back to safe defaults if any field is malformed —
    LLMs occasionally deviate from the requested format.
    """
    sentiment = "neutral"
    score = 0.0
    trend = "stable"
    confidence = 0.5
    themes: list[str] = []
    summary = text.strip()

    for line in text.splitlines():
        line = line.strip()
        try:
            if line.upper().startswith("SENTIMENT:"):
                val = line.split(":", 1)[1].strip().lower()
                if val in ("bullish", "bearish", "neutral"):
                    sentiment = val
            elif line.upper().startswith("SCORE:"):
                score = max(-1.0, min(1.0, float(line.split(":", 1)[1].strip())))
            elif line.upper().startswith("TREND:"):
                val = line.split(":", 1)[1].strip().lower()
                if val in ("improving", "worsening", "stable"):
                    trend = val
            elif line.upper().startswith("CONFIDENCE:"):
                confidence = max(0.0, min(1.0, float(line.split(":", 1)[1].strip())))
            elif line.upper().startswith("THEMES:"):
                themes = [
                    t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()
                ]
            elif line.upper().startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()
        except (ValueError, IndexError):
            continue

    return sentiment, score, trend, confidence, themes, summary
