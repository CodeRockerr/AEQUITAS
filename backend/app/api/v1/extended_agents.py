"""
AEQUITAS — Extended agentic features API endpoints.

POST /api/v1/agents/news-sentiment/{ticker}      news sentiment agent
POST /api/v1/agents/earnings/{ticker}             earnings analysis agent
POST /api/v1/agents/portfolio                     portfolio construction agent
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.earnings_agent import run_earnings_agent
from app.agents.news_sentiment_agent import run_news_sentiment_agent
from app.agents.nodes import _llm
from app.agents.portfolio_agent import run_portfolio_agent
from app.db import get_db

router = APIRouter(prefix="/api/v1/agents")


# ── Response schemas ──────────────────────────────────────────


class NewsArticleOut(BaseModel):
    headline: str
    source: str
    url: str
    published: str


class NewsSentimentOut(BaseModel):
    ticker: str
    sentiment: str
    sentiment_score: float
    trend: str
    confidence: float
    summary: str
    key_themes: list[str]
    recent_articles: list[NewsArticleOut]
    finnhub_sentiment_available: bool
    errors: list[str]


class EarningsHistoryOut(BaseModel):
    date: str
    quarter: str
    eps_actual: float | None
    eps_estimate: float | None
    eps_surprise_pct: float | None
    revenue_actual: float | None
    revenue_estimate: float | None


class EarningsAnalysisOut(BaseModel):
    ticker: str
    next_earnings_date: str | None
    last_earnings_beat: bool | None
    last_eps_surprise_pct: float | None
    guidance_sentiment: str
    analysis: str
    key_metrics: dict
    earnings_history: list[EarningsHistoryOut]
    history_available: bool
    errors: list[str]


class PortfolioRequest(BaseModel):
    tickers: list[str]


class PortfolioAllocationOut(BaseModel):
    ticker: str
    max_sharpe_weight: float
    min_variance_weight: float


class PairCointegrationOut(BaseModel):
    ticker_a: str
    ticker_b: str
    is_cointegrated: bool
    p_value: float
    half_life: float


class PortfolioConstructionOut(BaseModel):
    tickers: list[str]
    allocations: list[PortfolioAllocationOut]
    max_sharpe_return: float
    max_sharpe_vol: float
    max_sharpe_ratio: float
    min_variance_vol: float
    cointegrated_pairs: list[PairCointegrationOut]
    thesis: str
    errors: list[str]


# ── Endpoints ─────────────────────────────────────────────────


@router.post("/news-sentiment/{ticker}", response_model=NewsSentimentOut)
async def news_sentiment(ticker: str) -> NewsSentimentOut:
    """
    Run the news sentiment agent for a ticker.

    Pulls recent news from Finnhub, scores sentiment via LLM,
    and compares against the prior period to detect trend direction.
    """
    try:
        result = await run_news_sentiment_agent(ticker, _llm)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"News sentiment agent failed: {e}"
        ) from e

    return NewsSentimentOut(
        ticker=result.ticker,
        sentiment=result.sentiment,
        sentiment_score=result.sentiment_score,
        trend=result.trend,
        confidence=result.confidence,
        summary=result.summary,
        key_themes=result.key_themes,
        recent_articles=[NewsArticleOut(**a.__dict__) for a in result.recent_articles],
        finnhub_sentiment_available=result.finnhub_sentiment_available,
        errors=result.errors,
    )


@router.post("/earnings/{ticker}", response_model=EarningsAnalysisOut)
async def earnings_analysis(ticker: str) -> EarningsAnalysisOut:
    """
    Run the earnings analysis agent for a ticker.

    Synthesizes earnings history, recent earnings-related news,
    and key fundamentals into a structured analysis with guidance
    sentiment classification.

    history_available=false means Finnhub's free-tier earnings
    calendar had no data for this ticker — the analysis still runs,
    grounded in news + fundamentals instead.
    """
    try:
        result = await run_earnings_agent(ticker, _llm)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Earnings agent failed: {e}"
        ) from e

    return EarningsAnalysisOut(
        ticker=result.ticker,
        next_earnings_date=result.next_earnings_date,
        last_earnings_beat=result.last_earnings_beat,
        last_eps_surprise_pct=result.last_eps_surprise_pct,
        guidance_sentiment=result.guidance_sentiment,
        analysis=result.analysis,
        key_metrics=result.key_metrics,
        earnings_history=[
            EarningsHistoryOut(**h.__dict__) for h in result.earnings_history
        ],
        history_available=result.history_available,
        errors=result.errors,
    )


@router.post("/portfolio", response_model=PortfolioConstructionOut)
async def portfolio_construction(
    req: PortfolioRequest,
    db: AsyncSession = Depends(get_db),
) -> PortfolioConstructionOut:
    """
    Run the portfolio construction agent across a list of tickers.

    Runs mean-variance optimisation (max-Sharpe and min-variance),
    tests all pairs for cointegration, and asks the LLM to synthesise
    a portfolio-level thesis.

    Recommended: 2-10 tickers, each with 60+ days of ingested history.
    """
    if len(req.tickers) < 2:
        raise HTTPException(status_code=422, detail="Need at least 2 tickers")
    if len(req.tickers) > 10:
        raise HTTPException(status_code=422, detail="Maximum 10 tickers per request")

    try:
        result = await run_portfolio_agent(req.tickers, db, _llm)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Portfolio agent failed: {e}"
        ) from e

    return PortfolioConstructionOut(
        tickers=result.tickers,
        allocations=[PortfolioAllocationOut(**a.__dict__) for a in result.allocations],
        max_sharpe_return=result.max_sharpe_return,
        max_sharpe_vol=result.max_sharpe_vol,
        max_sharpe_ratio=result.max_sharpe_ratio,
        min_variance_vol=result.min_variance_vol,
        cointegrated_pairs=[
            PairCointegrationOut(**p.__dict__) for p in result.cointegrated_pairs
        ],
        thesis=result.thesis,
        errors=result.errors,
    )
