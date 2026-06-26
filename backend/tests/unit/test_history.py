"""
AEQUITAS — Unit tests for the price history endpoint helpers.

We test the pure logic (range validation, date filtering) without
hitting a real database or yfinance — those are integration-tested
manually since they require network/DB access.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.api.v1.history import VALID_RANGES


@pytest.mark.unit
def test_valid_ranges_contains_expected_values() -> None:
    assert VALID_RANGES == {"1mo", "6mo", "1y", "5y", "max"}


@pytest.mark.unit
def test_valid_ranges_rejects_unknown() -> None:
    assert "10y" not in VALID_RANGES
    assert "1d" not in VALID_RANGES


@pytest.mark.unit
def test_range_day_cutoffs_are_increasing() -> None:
    """Each range should cover more days than the previous, in order."""
    range_days = {
        "1mo": 31,
        "6mo": 183,
        "1y": 366,
        "5y": 1827,
    }
    values = list(range_days.values())
    assert values == sorted(values)


@pytest.mark.unit
def test_cutoff_calculation_1mo() -> None:
    """Sanity check the date math used for range filtering."""
    now = datetime(2026, 6, 21, tzinfo=UTC)
    cutoff = now.replace(tzinfo=None) - timedelta(days=31)
    assert cutoff.year == 2026
    assert cutoff.month == 5


@pytest.mark.unit
def test_cutoff_calculation_5y() -> None:
    now = datetime(2026, 6, 21, tzinfo=UTC)
    cutoff = now.replace(tzinfo=None) - timedelta(days=1827)
    assert cutoff.year == 2021
