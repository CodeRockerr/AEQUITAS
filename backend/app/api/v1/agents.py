"""
AEQUITAS — Agentic research API endpoints.

POST /api/v1/agents/research/{ticker}    run full research agent
POST /api/v1/agents/ingest-filing/{ticker}  store a filing document
GET  /api/v1/agents/thesis/{ticker}      get latest thesis
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_research_agent
from app.data.vector.store import chunk_text, store_document_chunks
from app.db import get_db

router = APIRouter(prefix="/api/v1/agents")


# ── Response schemas ──────────────────────────────────────────


class ShapDriverOut(BaseModel):
    feature: str
    shap_value: float
    direction: str
    magnitude: float


class ResearchResponse(BaseModel):
    ticker: str
    # Fundamental
    company_summary: str
    filing_citations: list[str]
    # Quantitative
    current_regime: str
    regime_confidence: float
    signal_direction: str
    signal_score: float
    predicted_return_pct: str
    var_95: float
    top_shap_drivers: list[ShapDriverOut]
    # Thesis
    final_thesis: str
    thesis_sentiment: str
    confidence_score: float
    # Meta
    critique: str
    revision_count: int
    errors: list[str]


class IngestFilingRequest(BaseModel):
    content: str
    source: str  # e.g. "10-K 2024 Q4", "Earnings Call 2024-Q3"


# ── Endpoints ─────────────────────────────────────────────────


@router.post("/research/{ticker}", response_model=ResearchResponse)
async def run_research(
    ticker: str,
    research_depth: str = "quick",
    db: AsyncSession = Depends(get_db),
) -> ResearchResponse:
    """
    Run the full AEQUITAS research agent for a ticker.

    Pipeline:
      1. Research node — retrieves company info + SEC filing chunks
      2. Quant node    — computes regime, signals, forecast, VaR
      3. Thesis node   — Claude synthesises investment thesis
      4. Critic node   — Claude evaluates, optionally requests revision

    Takes 15-30 seconds depending on Claude API response time.
    Requires the ticker to be ingested first via the market data endpoint.

    research_depth: "quick" (1 revision max) | "deep" (2 revisions max)
    """
    ticker = ticker.upper()

    try:
        state = await run_research_agent(ticker, db, research_depth)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent pipeline failed: {e}",
        ) from e

    final_thesis = state.get("final_thesis") or state.get("thesis", "")
    if not final_thesis:
        raise HTTPException(
            status_code=500,
            detail="Agent completed but produced no thesis.",
        )

    drivers = state.get("top_shap_drivers", [])

    return ResearchResponse(
        ticker=ticker,
        company_summary=state.get("company_summary", ""),
        filing_citations=state.get("filing_citations", []),
        current_regime=state.get("current_regime", "Unknown"),
        regime_confidence=state.get("regime_confidence", 0.0),
        signal_direction=state.get("signal_direction", "neutral"),
        signal_score=state.get("signal_score", 0.0),
        predicted_return_pct=state.get("predicted_return_pct", "N/A"),
        var_95=state.get("var_95", 0.0),
        top_shap_drivers=[ShapDriverOut(**d) for d in drivers],
        final_thesis=final_thesis,
        thesis_sentiment=state.get("thesis_sentiment", "neutral"),
        confidence_score=state.get("confidence_score", 0.0),
        critique=state.get("critique", ""),
        revision_count=state.get("revision_count", 0),
        errors=state.get("errors", []),
    )


@router.post("/ingest-filing/{ticker}")
async def ingest_filing(
    ticker: str,
    req: IngestFilingRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Store a financial document for RAG retrieval.

    The document is chunked into ~500-word pieces and stored
    in the document_chunks table for semantic search.

    Use this to feed SEC filings, earnings call transcripts,
    analyst reports, or any text-based financial document.

    Example sources: "10-K 2024", "10-Q 2024-Q3", "Earnings Call 2024-Q4"
    """
    if len(req.content.strip()) < 100:
        raise HTTPException(
            status_code=422,
            detail="Content too short — minimum 100 characters",
        )

    chunks = chunk_text(req.content, chunk_size=500, overlap=50)
    stored = await store_document_chunks(
        db,
        ticker=ticker.upper(),
        source=req.source,
        chunks=chunks,
    )
    await db.commit()

    return {
        "ticker": ticker.upper(),
        "source": req.source,
        "chunks_stored": stored,
        "total_chunks": len(chunks),
        "message": (
            f"Stored {stored} new chunks from '{req.source}'. "
            f"Run POST /api/v1/agents/research/{ticker} to generate a thesis."
        ),
    }
