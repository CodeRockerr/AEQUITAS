"""
AEQUITAS — Pricing and risk API endpoints.

POST /api/v1/pricing/black-scholes     price an option
POST /api/v1/pricing/implied-vol       compute implied volatility
POST /api/v1/risk/var                  compute VaR and CVaR
POST /api/v1/portfolio/optimise        optimise portfolio weights
GET  /api/v1/portfolio/frontier        compute efficient frontier
"""

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.portfolio.optimiser import (
    maximum_sharpe,
    minimum_variance,
)
from app.algorithms.pricing.black_scholes import (
    BlackScholesInputs,
    OptionType,
    implied_volatility,
    price,
)
from app.algorithms.risk.var_cvar import (
    historical_var,
    montecarlo_var,
    parametric_var,
)
from app.db import get_db
from app.models.market_data import OHLCVBar

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────


class BlackScholesRequest(BaseModel):
    spot: float = Field(gt=0, description="Current stock price")
    strike: float = Field(gt=0, description="Option strike price")
    rate: float = Field(description="Risk-free rate e.g. 0.05 for 5%")
    volatility: float = Field(gt=0, description="Implied vol e.g. 0.20 for 20%")
    expiry: float = Field(gt=0, description="Time to expiry in years e.g. 0.25")
    option_type: OptionType = OptionType.CALL


class GreeksResponse(BaseModel):
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class BlackScholesResponse(BaseModel):
    price: float
    greeks: GreeksResponse
    d1: float
    d2: float
    option_type: str
    moneyness: str  # ITM, ATM, OTM


class ImpliedVolRequest(BaseModel):
    market_price: float = Field(gt=0)
    spot: float = Field(gt=0)
    strike: float = Field(gt=0)
    rate: float
    expiry: float = Field(gt=0)
    option_type: OptionType = OptionType.CALL


class VaRRequest(BaseModel):
    ticker: str
    portfolio_value: float = Field(gt=0, description="Portfolio value in dollars")
    confidence_level: float = Field(default=0.95, ge=0.9, le=0.99)
    horizon_days: int = Field(default=1, ge=1, le=30)
    method: str = Field(
        default="historical", pattern="^(historical|parametric|montecarlo)$"
    )


class VaRResponse(BaseModel):
    var: float
    cvar: float
    confidence_level: float
    horizon_days: int
    method: str
    portfolio_value: float
    interpretation: str


class PortfolioOptimiseRequest(BaseModel):
    tickers: list[str] = Field(min_length=2, max_length=20)
    objective: str = Field(
        default="max_sharpe",
        pattern="^(max_sharpe|min_variance)$",
    )
    risk_free_rate: float = Field(default=0.05)


class PortfolioWeightResponse(BaseModel):
    ticker: str
    weight: float
    weight_pct: str


class PortfolioOptimiseResponse(BaseModel):
    weights: list[PortfolioWeightResponse]
    expected_return_pct: str
    volatility_pct: str
    sharpe_ratio: float
    objective: str


# ── Endpoints ─────────────────────────────────────────────────


@router.post("/api/v1/pricing/black-scholes", response_model=BlackScholesResponse)
async def black_scholes_price(req: BlackScholesRequest) -> BlackScholesResponse:
    """
    Price a European option using Black-Scholes.

    Returns the option price and all five Greeks.
    Moneyness tells you whether the option is in, at, or out of the money.
    """
    try:
        inputs = BlackScholesInputs(
            spot=req.spot,
            strike=req.strike,
            rate=req.rate,
            volatility=req.volatility,
            expiry=req.expiry,
            option_type=req.option_type,
        )
        result = price(inputs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Moneyness
    ratio = req.spot / req.strike
    if ratio > 1.02:
        moneyness = "ITM" if req.option_type == OptionType.CALL else "OTM"
    elif ratio < 0.98:
        moneyness = "OTM" if req.option_type == OptionType.CALL else "ITM"
    else:
        moneyness = "ATM"

    return BlackScholesResponse(
        price=result.price,
        greeks=GreeksResponse(
            delta=result.greeks.delta,
            gamma=result.greeks.gamma,
            vega=result.greeks.vega,
            theta=result.greeks.theta,
            rho=result.greeks.rho,
        ),
        d1=result.d1,
        d2=result.d2,
        option_type=req.option_type.value,
        moneyness=moneyness,
    )


@router.post("/api/v1/pricing/implied-vol")
async def compute_implied_vol(req: ImpliedVolRequest) -> dict:
    """
    Compute implied volatility from a market option price.

    Uses Newton-Raphson iteration — typically converges in ~5 steps.
    """
    try:
        inputs = BlackScholesInputs(
            spot=req.spot,
            strike=req.strike,
            rate=req.rate,
            volatility=0.20,  # initial guess — overridden by IV solver
            expiry=req.expiry,
            option_type=req.option_type,
        )
        iv = implied_volatility(req.market_price, inputs)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    return {
        "implied_volatility": iv,
        "implied_volatility_pct": f"{iv * 100:.2f}%",
    }


@router.post("/api/v1/risk/var", response_model=VaRResponse)
async def compute_var(
    req: VaRRequest,
    db: AsyncSession = Depends(get_db),
) -> VaRResponse:
    """
    Compute VaR and CVaR for a ticker using stored price history.

    Requires the ticker to be ingested first via the market data endpoint.
    Uses daily close prices to compute returns.
    """
    # Fetch stored OHLCV bars
    result = await db.execute(
        select(OHLCVBar.close, OHLCVBar.time)
        .where(
            OHLCVBar.ticker == req.ticker.upper(),
            OHLCVBar.interval == "1d",
        )
        .order_by(OHLCVBar.time.asc())
    )
    rows = result.all()

    if len(rows) < 31:
        raise HTTPException(
            status_code=404,
            detail=f"Not enough data for {req.ticker}. "
            f"Need 31+ bars, have {len(rows)}. "
            f"Call POST /api/v1/market-data/{req.ticker}/ingest first.",
        )

    # Compute daily log returns: ln(P_t / P_{t-1})
    closes = np.array([float(r.close) for r in rows])
    returns = np.diff(np.log(closes))

    try:
        if req.method == "historical":
            var_result = historical_var(
                returns,
                req.portfolio_value,
                req.confidence_level,
                req.horizon_days,
            )
        elif req.method == "parametric":
            var_result = parametric_var(
                returns,
                req.portfolio_value,
                req.confidence_level,
                req.horizon_days,
            )
        else:
            var_result = montecarlo_var(
                returns,
                req.portfolio_value,
                req.confidence_level,
                req.horizon_days,
            )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    pct = int(req.confidence_level * 100)
    interpretation = (
        f"With {pct}% confidence, the maximum {req.horizon_days}-day loss "
        f"on a ${req.portfolio_value:,.0f} {req.ticker.upper()} position "
        f"is ${var_result.var:,.2f}. "
        f"In the worst {100 - pct}% of scenarios, "
        f"the expected loss is ${var_result.cvar:,.2f}."
    )

    return VaRResponse(
        var=var_result.var,
        cvar=var_result.cvar,
        confidence_level=var_result.confidence_level,
        horizon_days=var_result.horizon_days,
        method=var_result.method,
        portfolio_value=var_result.portfolio_value,
        interpretation=interpretation,
    )


@router.post("/api/v1/portfolio/optimise", response_model=PortfolioOptimiseResponse)
async def optimise_portfolio(
    req: PortfolioOptimiseRequest,
    db: AsyncSession = Depends(get_db),
) -> PortfolioOptimiseResponse:
    """
    Optimise portfolio weights for a list of tickers.

    Fetches stored price history for each ticker and runs
    mean-variance optimisation. Tickers must be ingested first.
    """
    returns_list = []
    valid_tickers = []

    for ticker in req.tickers:
        result = await db.execute(
            select(OHLCVBar.close)
            .where(
                OHLCVBar.ticker == ticker.upper(),
                OHLCVBar.interval == "1d",
            )
            .order_by(OHLCVBar.time.asc())
        )
        closes = [float(r.close) for r in result.all()]

        if len(closes) < 31:
            continue  # skip tickers with insufficient data

        returns = np.diff(np.log(np.array(closes)))
        returns_list.append(returns)
        valid_tickers.append(ticker.upper())

    if len(valid_tickers) < 2:
        raise HTTPException(
            status_code=422,
            detail="Need at least 2 tickers with 31+ days of data. "
            "Ingest more tickers first.",
        )

    # Align return series to same length (use minimum)
    min_len = min(len(r) for r in returns_list)
    returns_matrix = np.column_stack([r[-min_len:] for r in returns_list])

    try:
        if req.objective == "max_sharpe":
            portfolio = maximum_sharpe(
                returns_matrix, valid_tickers, req.risk_free_rate
            )
        else:
            portfolio = minimum_variance(
                returns_matrix, valid_tickers, req.risk_free_rate
            )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    weights_response = [
        PortfolioWeightResponse(
            ticker=t,
            weight=w,
            weight_pct=f"{w * 100:.1f}%",
        )
        for t, w in zip(portfolio.tickers, portfolio.weights, strict=False)
    ]

    return PortfolioOptimiseResponse(
        weights=weights_response,
        expected_return_pct=f"{portfolio.expected_return * 100:.2f}%",
        volatility_pct=f"{portfolio.volatility * 100:.2f}%",
        sharpe_ratio=round(portfolio.sharpe_ratio, 4),
        objective=req.objective,
    )
