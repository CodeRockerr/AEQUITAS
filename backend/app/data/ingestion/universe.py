"""
AEQUITAS - Canonical ticker universe for bulk ingestion.

Every ticker the frontend's ticker pickers actually reference, plus the
four Fama-French benchmark proxies the factor model depends on (SPY
does double duty as both a pickable ticker and the market-beta
benchmark). This list is only consulted by the scheduled bulk-refresh
job (POST /api/v1/market-data/refresh-universe) - any ticker NOT on it
still works fine on first request via ensure_min_bars/ensure_company_info's
existing on-demand auto-ingest. This just means the common tickers are
backfilled and kept current proactively, instead of every user's first
request each day paying the one-time yFinance fetch cost.
"""

TICKER_UNIVERSE = [
    # Frontend ticker pickers (backtests, theses, risk, factors, agents, dashboard)
    "AAPL",
    "MSFT",
    "SPY",
    "NVDA",
    "TSLA",
    "AMZN",
    # Home page ticker tape
    "META",
    "GOOGL",
    "BRK-B",
    "JPM",
    # Fama-French 3-factor model benchmark proxies (factor_model.py) -
    # IWM/IVE/IWF only, SPY already listed above
    "IWM",
    "IVE",
    "IWF",
]
