"""
AEQUITAS — Finnhub API client.

Finnhub provides free-tier access (60 calls/min, no credit card) to:
  - Company news
  - News sentiment scores
  - Earnings calendar
  - Basic company fundamentals

Used by the news sentiment agent and earnings call agent.
Docs: https://finnhub.io/docs/api
"""

from datetime import UTC, datetime, timedelta
from typing import cast

import httpx
import structlog

from app.config import settings

log = structlog.get_logger()

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


async def _finnhub_get(endpoint: str, params: dict) -> dict | list:
    """
    Make a GET request to Finnhub's API.

    Raises httpx.HTTPStatusError on non-2xx responses, which callers
    should catch to handle rate limits / invalid tickers gracefully.
    """
    params["token"] = settings.finnhub_api_key
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(f"{FINNHUB_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()
        return cast(dict | list, response.json())


async def get_company_news(
    ticker: str,
    days_back: int = 14,
) -> list[dict]:
    """
    Fetch recent news articles for a ticker.

    Returns a list of dicts with: headline, summary, source, url,
    datetime (unix timestamp), category.

    Finnhub's free tier covers the last ~1 year of news.
    """
    to_date = datetime.now(UTC).date()
    from_date = to_date - timedelta(days=days_back)

    try:
        result = await _finnhub_get(
            "/company-news",
            {
                "symbol": ticker.upper(),
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
            },
        )
        return result if isinstance(result, list) else []
    except httpx.HTTPStatusError as e:
        log.warning("finnhub_news_failed", ticker=ticker, status=e.response.status_code)
        return []
    except Exception as e:
        log.warning("finnhub_news_error", ticker=ticker, error=str(e))
        return []


async def get_news_sentiment(ticker: str) -> dict | None:
    """
    Fetch Finnhub's pre-computed news sentiment score for a ticker.

    Returns a dict with companyNewsScore, sectorAverageNewsScore,
    sentiment.bearishPercent, sentiment.bullishPercent, buzz metrics.

    Note: this endpoint is on Finnhub's premium tier as of certain
    plan changes — if it 403s, we fall back to computing our own
    sentiment from headlines via the LLM instead.
    """
    try:
        result = await _finnhub_get("/news-sentiment", {"symbol": ticker.upper()})
        return result if isinstance(result, dict) else None
    except httpx.HTTPStatusError as e:
        log.info(
            "finnhub_sentiment_unavailable",
            ticker=ticker,
            status=e.response.status_code,
            note="falling back to LLM-computed sentiment",
        )
        return None
    except Exception as e:
        log.warning("finnhub_sentiment_error", ticker=ticker, error=str(e))
        return None


async def get_earnings_calendar(ticker: str) -> list[dict]:
    """
    Fetch upcoming and recent earnings dates + estimates for a ticker.

    Returns a list of dicts with: date, epsActual, epsEstimate,
    revenueActual, revenueEstimate, quarter, year.
    """
    to_date = datetime.now(UTC).date() + timedelta(days=90)
    from_date = datetime.now(UTC).date() - timedelta(days=180)

    try:
        result = await _finnhub_get(
            "/calendar/earnings",
            {
                "symbol": ticker.upper(),
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
            },
        )
        if isinstance(result, dict):
            return cast(list[dict], result.get("earningsCalendar", []))
        return []
    except httpx.HTTPStatusError as e:
        log.warning(
            "finnhub_earnings_failed", ticker=ticker, status=e.response.status_code
        )
        return []
    except Exception as e:
        log.warning("finnhub_earnings_error", ticker=ticker, error=str(e))
        return []


async def get_basic_financials(ticker: str) -> dict | None:
    """
    Fetch basic company fundamentals (P/E, margins, growth rates).

    Useful supplementary context for the earnings agent.
    """
    try:
        result = await _finnhub_get(
            "/stock/metric",
            {
                "symbol": ticker.upper(),
                "metric": "all",
            },
        )
        return result if isinstance(result, dict) else None
    except Exception as e:
        log.warning("finnhub_financials_error", ticker=ticker, error=str(e))
        return None
