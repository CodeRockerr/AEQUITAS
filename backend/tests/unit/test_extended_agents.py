"""
AEQUITAS — Unit tests for the news sentiment, earnings, and
portfolio construction agents.

We test the pure parsing/calculation logic without hitting Finnhub
or a real LLM — those paths are integration-tested manually.
"""

import pytest

from app.agents.earnings_agent import _safe_surprise_pct
from app.agents.news_sentiment_agent import _parse_llm_response

# ── News sentiment LLM response parsing ───────────────────────


@pytest.mark.unit
def test_parse_llm_response_well_formed() -> None:
    text = (
        "SENTIMENT: bullish\n"
        "SCORE: 0.65\n"
        "TREND: improving\n"
        "CONFIDENCE: 0.8\n"
        "THEMES: AI growth, strong margins, new product launch\n"
        "SUMMARY: The company shows strong positive momentum."
    )
    sentiment, score, trend, confidence, themes, summary = _parse_llm_response(text)
    assert sentiment == "bullish"
    assert score == 0.65
    assert trend == "improving"
    assert confidence == 0.8
    assert themes == ["AI growth", "strong margins", "new product launch"]
    assert "positive momentum" in summary


@pytest.mark.unit
def test_parse_llm_response_clips_score_range() -> None:
    text = "SENTIMENT: bullish\nSCORE: 5.0\nTREND: stable\nCONFIDENCE: 0.5\nTHEMES: x\nSUMMARY: test"
    _, score, _, _, _, _ = _parse_llm_response(text)
    assert score == 1.0  # clipped to max


@pytest.mark.unit
def test_parse_llm_response_clips_confidence_range() -> None:
    text = "SENTIMENT: bearish\nSCORE: -0.5\nTREND: worsening\nCONFIDENCE: -2.0\nTHEMES: x\nSUMMARY: test"
    _, _, _, confidence, _, _ = _parse_llm_response(text)
    assert confidence == 0.0  # clipped to min


@pytest.mark.unit
def test_parse_llm_response_handles_malformed_gracefully() -> None:
    text = "This is not formatted correctly at all, just prose."
    sentiment, score, trend, confidence, themes, summary = _parse_llm_response(text)
    assert sentiment == "neutral"  # safe default
    assert score == 0.0
    assert trend == "stable"
    assert themes == []


@pytest.mark.unit
def test_parse_llm_response_invalid_sentiment_value_ignored() -> None:
    text = "SENTIMENT: super-duper-bullish\nSCORE: 0.5\nTREND: stable\nCONFIDENCE: 0.5\nTHEMES: x\nSUMMARY: test"
    sentiment, _, _, _, _, _ = _parse_llm_response(text)
    assert sentiment == "neutral"  # invalid value falls back to default


# ── Earnings surprise calculation ─────────────────────────────


@pytest.mark.unit
def test_safe_surprise_pct_positive_beat() -> None:
    result = _safe_surprise_pct(actual=1.10, estimate=1.00)
    assert result == 10.0


@pytest.mark.unit
def test_safe_surprise_pct_negative_miss() -> None:
    result = _safe_surprise_pct(actual=0.90, estimate=1.00)
    assert result == -10.0


@pytest.mark.unit
def test_safe_surprise_pct_none_actual() -> None:
    assert _safe_surprise_pct(actual=None, estimate=1.00) is None


@pytest.mark.unit
def test_safe_surprise_pct_none_estimate() -> None:
    assert _safe_surprise_pct(actual=1.00, estimate=None) is None


@pytest.mark.unit
def test_safe_surprise_pct_zero_estimate() -> None:
    """Division by zero should return None, not raise."""
    assert _safe_surprise_pct(actual=1.00, estimate=0.0) is None


@pytest.mark.unit
def test_safe_surprise_pct_negative_estimate() -> None:
    """Surprise pct should use abs(estimate) in denominator."""
    result = _safe_surprise_pct(actual=-0.5, estimate=-1.0)
    # actual beat estimate (less negative) -> positive surprise
    assert result == 50.0
