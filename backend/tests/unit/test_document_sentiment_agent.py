"""
AEQUITAS - Unit tests for run_document_sentiment_agent.

Unlike run_news_sentiment_agent (which hits Finnhub directly and is
integration-tested manually, per test_extended_agents.py's docstring),
this function takes llm_call as an injected parameter with no other
external dependency - so a stub llm_call exercises the real control
flow without needing to mock anything or reach a real LLM.
"""

import pytest

from app.agents.news_sentiment_agent import (
    MAX_DOCUMENT_CHARS,
    run_document_sentiment_agent,
)

_WELL_FORMED_RESPONSE = (
    "SENTIMENT: bullish\n"
    "SCORE: 0.7\n"
    "CONFIDENCE: 0.8\n"
    "THEMES: iPhone sales, services growth\n"
    "SUMMARY: Strong quarter driven by hardware and services."
)


async def _stub_llm(system: str, user: str, max_tokens: int) -> str:
    return _WELL_FORMED_RESPONSE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_sentiment_agent_returns_parsed_result() -> None:
    result = await run_document_sentiment_agent(
        "aapl", "Apple reported record iPhone sales this quarter.", _stub_llm
    )

    assert result.ticker == "AAPL"
    assert result.sentiment == "bullish"
    assert result.sentiment_score == 0.7
    assert result.confidence == 0.8
    assert result.key_themes == ["iPhone sales", "services growth"]
    assert result.recent_articles == []
    assert result.finnhub_sentiment_available is False
    assert result.errors == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_sentiment_agent_trend_always_stable() -> None:
    """
    There's no prior-period baseline for a single pasted document, so
    trend should never be LLM-derived here - it's always "stable",
    unlike run_news_sentiment_agent's headline-vs-headline comparison.
    """
    result = await run_document_sentiment_agent(
        "TSLA", "Some report text here.", _stub_llm
    )
    assert result.trend == "stable"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_sentiment_agent_truncates_long_document() -> None:
    long_text = "word " * (MAX_DOCUMENT_CHARS)  # comfortably over the cap
    captured = {}

    async def capturing_llm(system: str, user: str, max_tokens: int) -> str:
        captured["user"] = user
        return _WELL_FORMED_RESPONSE

    result = await run_document_sentiment_agent("MSFT", long_text, capturing_llm)

    assert any("truncated" in e.lower() for e in result.errors)
    # the prompt actually sent to the LLM should be capped, not the full document
    assert len(captured["user"]) < len(long_text)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_sentiment_agent_short_document_not_flagged_truncated() -> None:
    result = await run_document_sentiment_agent("NVDA", "Short document.", _stub_llm)
    assert result.errors == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_sentiment_agent_captures_multiline_summary() -> None:
    """SUMMARY is the last field in the requested format, and the "2-3
    sentence narrative" the LLM is asked for often wraps across more
    than one line - the parser must keep everything after the marker,
    not just the first line, or later sentences get silently dropped."""

    async def multiline_llm(system: str, user: str, max_tokens: int) -> str:
        return (
            "SENTIMENT: bullish\n"
            "SCORE: 0.6\n"
            "CONFIDENCE: 0.7\n"
            "THEMES: growth\n"
            "SUMMARY: First sentence of the summary.\n"
            "Second sentence continues on its own line.\n"
            "Third sentence too."
        )

    result = await run_document_sentiment_agent("AAPL", "Some text.", multiline_llm)

    assert "First sentence" in result.summary
    assert "Second sentence" in result.summary
    assert "Third sentence" in result.summary
