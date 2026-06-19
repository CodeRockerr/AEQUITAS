"""
AEQUITAS — Fama-French 3-factor model.

The Fama-French model decomposes a stock's returns into:
  - Market factor (β_mkt): sensitivity to overall market moves
  - SMB (Small Minus Big): exposure to small-cap premium
  - HML (High Minus Low): exposure to value premium

The intercept (alpha) is what's left over after accounting
for these three risk factors — it represents genuine skill
or mispricing, not just passive factor exposure.

Why this matters in interviews:
  "Your strategy returned 15%" is meaningless without asking
  "how much of that was just market beta?" Fama-French tells
  you the risk-adjusted alpha — the part that actually adds value.

Factor proxies:
  Market: SPY (S&P 500 ETF)
  SMB:    IWM - SPY returns (small-cap minus large-cap)
  HML:    IVE - IWF returns (value minus growth)
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FactorModelResult:
    """
    Result of Fama-French 3-factor regression.

    alpha:          annualised excess return unexplained by factors (true skill)
    alpha_tstat:    t-statistic for alpha (> 2.0 = statistically significant)
    beta_market:    sensitivity to market. 1.0 = moves with market, 1.5 = 50% more volatile
    beta_smb:       small-cap exposure. Positive = tilts small, negative = tilts large
    beta_hml:       value exposure. Positive = value tilt, negative = growth tilt
    r_squared:      % of variance explained by the 3 factors (0-1)
    residual_vol:   annualised volatility of unexplained returns
    interpretation: plain-English summary
    """

    ticker: str
    alpha: float
    alpha_tstat: float
    beta_market: float
    beta_smb: float
    beta_hml: float
    r_squared: float
    residual_vol: float
    interpretation: str


def _ols_multivariate(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    """
    OLS regression: y = X @ beta + epsilon.

    Returns:
        beta:     coefficient vector
        se:       standard errors for each coefficient
        r_sq:     R-squared
    """
    # Add intercept column
    n = x.shape[0]
    ones = np.ones((n, 1), dtype=np.float64)
    X_with_intercept = np.column_stack([ones, x])

    # beta = (X'X)^{-1} X'y
    XtX = X_with_intercept.T @ X_with_intercept
    Xty = X_with_intercept.T @ y

    try:
        beta = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]

    # Residuals and R-squared
    y_hat = X_with_intercept @ beta
    residuals: np.ndarray = y - y_hat
    ss_res = float(np.dot(residuals, residuals))
    ss_tot = float(np.dot(y - y.mean(), y - y.mean()))
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Standard errors: SE = sqrt(diag((X'X)^{-1} * s^2))
    s2 = ss_res / max(n - X_with_intercept.shape[1], 1)
    try:
        cov_beta = np.linalg.inv(XtX) * s2
        se = np.sqrt(np.maximum(np.diag(cov_beta), 0))
    except np.linalg.LinAlgError:
        se = np.zeros(len(beta))

    return beta, se, r_sq


def compute_factor_proxies(
    market_returns: pd.Series,
    small_returns: pd.Series,
    value_returns: pd.Series,
    growth_returns: pd.Series,
    risk_free_rate: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute Fama-French factor returns from ETF proxies.

    Market excess return: SPY - rf
    SMB (Small Minus Big): IWM - SPY
    HML (High Minus Low):  IVE - IWF

    All returns should be daily log returns.
    """
    mkt_excess = market_returns.to_numpy(dtype=np.float64) - risk_free_rate / 252
    smb = small_returns.to_numpy(dtype=np.float64) - market_returns.to_numpy(
        dtype=np.float64
    )
    hml = value_returns.to_numpy(dtype=np.float64) - growth_returns.to_numpy(
        dtype=np.float64
    )
    return mkt_excess, smb, hml


def run_factor_model(
    ticker_returns: pd.Series,
    market_returns: pd.Series,
    small_cap_returns: pd.Series,
    value_returns: pd.Series,
    growth_returns: pd.Series,
    ticker: str = "STOCK",
    risk_free_rate: float = 0.05,
) -> FactorModelResult:
    """
    Run Fama-French 3-factor regression on a return series.

    All return series should be daily log returns and aligned.

    Args:
        ticker_returns:     daily log returns for the stock
        market_returns:     SPY daily log returns (market proxy)
        small_cap_returns:  IWM daily log returns (small-cap proxy)
        value_returns:      IVE daily log returns (value proxy)
        growth_returns:     IWF daily log returns (growth proxy)
        risk_free_rate:     annualised risk-free rate (default 5%)
    """
    # Align all series
    df = pd.DataFrame(
        {
            "stock": ticker_returns,
            "market": market_returns,
            "small": small_cap_returns,
            "value": value_returns,
            "growth": growth_returns,
        }
    ).dropna()

    n = len(df)
    if n < 60:
        raise ValueError(f"Need at least 60 observations, got {n}")

    rf_daily = risk_free_rate / 252

    stock_excess = df["stock"].to_numpy(dtype=np.float64) - rf_daily
    mkt_excess, smb, hml = compute_factor_proxies(
        df["market"], df["small"], df["value"], df["growth"], rf_daily
    )

    # Design matrix: [market_excess, SMB, HML]
    X = np.column_stack([mkt_excess, smb, hml])

    # Run OLS
    beta, se, r_sq = _ols_multivariate(X, stock_excess)

    # beta[0] = intercept (daily alpha), beta[1-3] = factor betas
    daily_alpha = float(beta[0])
    annual_alpha = daily_alpha * 252

    # t-statistic for alpha
    alpha_se = float(se[0]) if float(se[0]) > 0 else 1e-10
    alpha_tstat = daily_alpha / alpha_se

    # Factor betas
    beta_mkt = float(beta[1])
    beta_smb = float(beta[2])
    beta_hml = float(beta[3])

    # Residual volatility (annualised)
    y_hat = np.column_stack([np.ones(n), X]) @ beta
    residuals = stock_excess - y_hat
    residual_vol = float(np.std(residuals)) * np.sqrt(252)

    # Build interpretation
    alpha_sig = "significant" if abs(alpha_tstat) > 2.0 else "not significant"
    style = []
    if beta_smb > 0.2:
        style.append("small-cap tilt")
    if beta_smb < -0.2:
        style.append("large-cap tilt")
    if beta_hml > 0.2:
        style.append("value tilt")
    if beta_hml < -0.2:
        style.append("growth tilt")
    style_str = ", ".join(style) if style else "no strong factor tilt"

    interp = (
        f"Alpha: {annual_alpha * 100:.2f}% p.a. ({alpha_sig}, t={alpha_tstat:.2f}). "
        f"Market beta: {beta_mkt:.2f} ({'more' if beta_mkt > 1 else 'less'} volatile than market). "
        f"Factor exposure: {style_str}. "
        f"Model explains {r_sq * 100:.1f}% of return variance."
    )

    return FactorModelResult(
        ticker=ticker.upper(),
        alpha=round(annual_alpha, 6),
        alpha_tstat=round(alpha_tstat, 4),
        beta_market=round(beta_mkt, 4),
        beta_smb=round(beta_smb, 4),
        beta_hml=round(beta_hml, 4),
        r_squared=round(r_sq, 4),
        residual_vol=round(residual_vol, 4),
        interpretation=interp,
    )
