"""
AEQUITAS — LangGraph agent node functions.

Each node is a pure async function that receives the current
state, does work, and returns a dict of state updates.

Uses Groq API (free tier) for LLM calls — llama-3.3-70b-versatile.
Groq is ~10x faster than OpenAI and has a generous free tier.
"""

import structlog
from groq import AsyncGroq  # type: ignore[import-untyped]

from app.config import settings

log = structlog.get_logger()

MAX_REVISIONS = 2


def _get_groq_client() -> AsyncGroq:
    """Return a Groq async client using the configured API key."""
    return AsyncGroq(api_key=settings.groq_api_key)


async def _llm(
    system: str,
    user: str,
    max_tokens: int = 1024,
) -> str:
    """
    Call Groq API and return the text response.

    Model: llama-3.3-70b-versatile
      - Free tier: 6,000 requests/day, 500,000 tokens/minute
      - Speed: ~700 tokens/second (much faster than OpenAI)
      - Quality: comparable to GPT-4o for structured financial text

    The system/user message format is identical to OpenAI and
    Anthropic — easy to swap providers later.
    """
    client = _get_groq_client()

    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.3,  # lower = more focused, less creative
    )

    return str(response.choices[0].message.content)


async def research_node(state: dict, db) -> dict:  # type: ignore[type-arg]
    """
    Research node — gathers company context from stored documents.

    Retrieves relevant SEC filing chunks for the ticker using
    full-text search, then asks the LLM to summarise the company.
    """
    ticker = state.get("ticker", "")
    errors: list[str] = list(state.get("errors", []))

    log.info("research_node_start", ticker=ticker)

    from sqlalchemy import select

    from app.data.vector.store import (
        get_all_chunks_for_ticker,
        retrieve_relevant_chunks,
    )
    from app.models.market_data import CompanyInfo

    query = f"{ticker} business revenue growth risk factors earnings"
    chunks = await retrieve_relevant_chunks(db, ticker, query, n_chunks=5)

    if not chunks:
        chunks = await get_all_chunks_for_ticker(db, ticker, limit=5)

    citations = [f"{c['source']} (relevance: {c['relevance']})" for c in chunks]

    result = await db.execute(
        select(CompanyInfo).where(CompanyInfo.ticker == ticker.upper())
    )
    company = result.scalar_one_or_none()

    company_context = ""
    if company:
        company_context = (
            f"Company: {company.name}\n"
            f"Sector: {company.sector}\n"
            f"Industry: {company.industry}\n"
            f"Market Cap: ${company.market_cap:,}\n"
            f"Description: {company.description or 'N/A'}\n"
        )

    filing_context = (
        "\n\n".join([f"[{c['source']}]: {c['content'][:500]}..." for c in chunks])
        if chunks
        else "No filing documents available."
    )

    if company_context or filing_context != "No filing documents available.":
        summary = await _llm(
            system=(
                "You are a financial research analyst. Given company information "
                "and SEC filing excerpts, write a concise 2-3 paragraph company "
                "summary covering: business model, competitive position, and "
                "key financial characteristics. Be factual and cite sources."
            ),
            user=(
                f"Ticker: {ticker}\n\n"
                f"Company Info:\n{company_context}\n\n"
                f"Filing Excerpts:\n{filing_context}"
            ),
            max_tokens=512,
        )
    else:
        summary = f"{ticker} — no company information available in the database."
        errors.append("No company data found — run /ingest and /info endpoints first")

    log.info("research_node_complete", ticker=ticker, n_chunks=len(chunks))

    return {
        "company_summary": summary,
        "recent_filings": chunks,
        "filing_citations": citations,
        "errors": errors,
    }


async def quant_node(state: dict, db) -> dict:  # type: ignore[type-arg]
    """
    Quant node — pulls live quantitative signals for the ticker.

    Calls our own algorithm layer:
      - HMM regime detection
      - Combined momentum signal (RSI, MACD, Bollinger)
      - XGBoost return forecast + SHAP
      - Historical VaR
    """
    ticker = state.get("ticker", "")
    errors: list[str] = list(state.get("errors", []))

    log.info("quant_node_start", ticker=ticker)

    import numpy as np
    import pandas as pd
    from sqlalchemy import select

    from app.algorithms.ml.forecaster import forecast_next_day, train_forecaster
    from app.algorithms.ml.regime_detector import detect_regimes, fit_regime_model
    from app.algorithms.risk.var_cvar import historical_var
    from app.algorithms.signals.momentum import combined_signal
    from app.models.market_data import OHLCVBar

    result = await db.execute(
        select(OHLCVBar.time, OHLCVBar.close)
        .where(OHLCVBar.ticker == ticker.upper(), OHLCVBar.interval == "1d")
        .order_by(OHLCVBar.time.asc())
    )
    rows = result.all()

    if len(rows) < 60:
        errors.append(f"Insufficient price data for {ticker} — need 60+ bars")
        return {
            "current_regime": "Unknown",
            "regime_confidence": 0.0,
            "signal_score": 0.0,
            "signal_direction": "neutral",
            "var_95": 0.0,
            "predicted_return_pct": "N/A",
            "top_shap_drivers": [],
            "errors": errors,
        }

    times = [r.time for r in rows]
    closes = [float(r.close) for r in rows]
    close_series = pd.Series(closes, index=pd.DatetimeIndex(times))

    idx = pd.DatetimeIndex(times)
    close_arr = np.array(closes, dtype=np.float64)
    idx = pd.DatetimeIndex(times)
    df = pd.DataFrame(
        {
            "open": close_arr,
            "high": close_arr * 1.005,
            "low": close_arr * 0.995,
            "close": close_arr,
            "volume": np.full(len(closes), 1_000_000, dtype=np.float64),
        },
        index=idx,
    )

    results: dict = {}

    # Regime
    try:
        ratio1 = close_series / close_series.shift(1)
        log_ret = ratio1.apply(np.log).dropna()
        returns = log_ret.to_numpy(dtype=np.float64)
        fitted = fit_regime_model(returns)
        regime_result = detect_regimes(fitted, returns)
        results["current_regime"] = regime_result.current_regime_label
        results["regime_confidence"] = regime_result.current_regime_prob
    except Exception as e:
        errors.append(f"Regime detection failed: {e}")
        results["current_regime"] = "Unknown"
        results["regime_confidence"] = 0.0

    # Signals
    try:
        sig = combined_signal(close_series)
        results["signal_score"] = sig["combined_signal"]
        results["signal_direction"] = sig["direction"]
    except Exception as e:
        errors.append(f"Signal computation failed: {e}")
        results["signal_score"] = 0.0
        results["signal_direction"] = "neutral"

    # Forecast
    try:
        if len(rows) >= 200:
            trained = train_forecaster(df)
            forecast = forecast_next_day(trained, df)
            results["predicted_return_pct"] = forecast.predicted_return_pct
            results["top_shap_drivers"] = forecast.top_drivers
        else:
            results["predicted_return_pct"] = "N/A (need 200+ bars)"
            results["top_shap_drivers"] = []
    except Exception as e:
        errors.append(f"Forecast failed: {e}")
        results["predicted_return_pct"] = "N/A"
        results["top_shap_drivers"] = []

    # VaR
    try:
        ratio2 = close_series / close_series.shift(1)
        log_ret2 = ratio2.apply(np.log).dropna()
        returns2 = log_ret2.to_numpy(dtype=np.float64)
        var_result = historical_var(returns2, portfolio_value=100_000.0)
        results["var_95"] = var_result.var
    except Exception as e:
        errors.append(f"VaR calculation failed: {e}")
        results["var_95"] = 0.0

    results["errors"] = errors
    log.info("quant_node_complete", ticker=ticker)
    return results


async def thesis_node(state: dict) -> dict:  # type: ignore[type-arg]
    """
    Thesis node — synthesises a trade thesis using Groq LLM.

    Combines fundamental research with quantitative signals
    into a structured investment thesis.
    """
    ticker = state.get("ticker", "")
    log.info("thesis_node_start", ticker=ticker)

    company_summary = state.get("company_summary", "No company summary available.")
    regime = state.get("current_regime", "Unknown")
    regime_conf = state.get("regime_confidence", 0.0)
    signal_dir = state.get("signal_direction", "neutral")
    signal_score = state.get("signal_score", 0.0)
    predicted_return = state.get("predicted_return_pct", "N/A")
    var_95 = state.get("var_95", 0.0)
    shap_drivers = state.get("top_shap_drivers", [])
    citations = state.get("filing_citations", [])

    shap_text = (
        "\n".join(
            [
                f"  - {d['feature']}: {d['direction']} (magnitude: {d['magnitude']:.4f})"
                for d in shap_drivers[:3]
            ]
        )
        if shap_drivers
        else "  No SHAP data available"
    )

    citations_text = "\n".join([f"  [{i+1}] {c}" for i, c in enumerate(citations[:3])])

    thesis = await _llm(
        system=(
            "You are a senior quantitative research analyst at a hedge fund. "
            "Write a structured investment thesis based on fundamental research "
            "and quantitative signals. Be specific, cite sources, acknowledge risks. "
            "Format: Overview | Bull Case | Bear Case | "
            "Quantitative Evidence | Risk Factors | Verdict"
        ),
        user=(
            f"Ticker: {ticker}\n\n"
            f"=== FUNDAMENTAL RESEARCH ===\n{company_summary}\n\n"
            f"=== QUANTITATIVE SIGNALS ===\n"
            f"Market Regime: {regime} (confidence: {regime_conf:.0%})\n"
            f"Momentum Signal: {signal_dir} (score: {signal_score:+.3f})\n"
            f"ML Return Forecast: {predicted_return}\n"
            f"95% VaR (per $100k): ${var_95:,.0f}\n\n"
            f"Top Signal Drivers (SHAP):\n{shap_text}\n\n"
            f"Sources:\n"
            f"{citations_text if citations_text else '  No filing citations'}\n\n"
            "Write a thorough investment thesis (400-500 words)."
        ),
        max_tokens=1024,
    )

    if signal_score > 0.2:
        sentiment = "bullish"
        confidence = 0.6 + abs(signal_score) * 0.3
    elif signal_score < -0.2:
        sentiment = "bearish"
        confidence = 0.6 + abs(signal_score) * 0.3
    else:
        sentiment = "neutral"
        confidence = 0.4

    log.info("thesis_node_complete", ticker=ticker, sentiment=sentiment)

    return {
        "thesis": thesis,
        "thesis_sentiment": sentiment,
        "confidence_score": round(min(confidence, 0.95), 3),
    }


async def critic_node(state: dict) -> dict:  # type: ignore[type-arg]
    """
    Critic node — evaluates the thesis and decides if revision needed.
    """
    ticker = state.get("ticker", "")
    thesis = state.get("thesis", "")
    revision_count = int(state.get("revision_count", 0))

    log.info("critic_node_start", ticker=ticker, revision=revision_count)

    critique = await _llm(
        system=(
            "You are a critical risk manager reviewing an investment thesis. "
            "Find weaknesses, unsupported claims, missing risks, and inconsistencies. "
            "Be specific and constructive. "
            "End with exactly one line: VERDICT: APPROVE or VERDICT: REVISE"
        ),
        user=(
            f"Review this investment thesis for {ticker}:\n\n{thesis}\n\n"
            "Identify: (1) unsupported claims, (2) missing risk factors, "
            "(3) inconsistencies with quantitative data, "
            "(4) overconfident language."
        ),
        max_tokens=512,
    )

    needs_revision = "VERDICT: REVISE" in critique and revision_count < MAX_REVISIONS

    final_thesis = "" if needs_revision else thesis

    log.info(
        "critic_complete",
        ticker=ticker,
        approved=not needs_revision,
        revision=revision_count,
    )

    return {
        "critique": critique,
        "revision_needed": needs_revision,
        "revision_count": revision_count + 1,
        "final_thesis": final_thesis,
    }
