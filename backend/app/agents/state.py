"""
AEQUITAS — LangGraph agent state definition.

The state is the shared memory that flows between all nodes
in the graph. Every node can read and update it.

Using TypedDict ensures every field is explicitly typed —
no surprise keys, no silent overwrites.
"""

from typing import TypedDict


class ResearchState(TypedDict, total=False):
    """
    Shared state for the AEQUITAS research agent graph.

    total=False means all fields are optional — nodes only
    update the fields they're responsible for.
    """

    # ── Input ─────────────────────────────────────────────────
    ticker: str  # e.g. "AAPL"
    research_depth: str  # "quick" | "deep"

    # ── Research node output ──────────────────────────────────
    company_summary: str  # brief company description
    recent_filings: list[dict]  # retrieved SEC filing chunks
    filing_citations: list[str]  # source references

    # ── Quant node output ─────────────────────────────────────
    current_regime: str  # Bull / Bear / High Volatility
    regime_confidence: float
    signal_score: float  # combined momentum signal [-1, +1]
    signal_direction: str  # bullish / bearish / neutral
    var_95: float  # 95% VaR in dollars (per $100k)
    predicted_return_pct: str  # XGBoost forecast
    top_shap_drivers: list[dict]  # top 5 SHAP features

    # ── Thesis node output ────────────────────────────────────
    thesis: str  # full trade thesis text
    thesis_sentiment: str  # bullish / bearish / neutral
    confidence_score: float  # 0-1 overall confidence

    # ── Critic node output ────────────────────────────────────
    critique: str  # what's weak about the thesis
    revision_needed: bool  # should we loop back?
    revision_count: int  # how many times we've revised
    final_thesis: str  # approved thesis text

    # ── Metadata ──────────────────────────────────────────────
    errors: list[str]  # any non-fatal errors encountered
