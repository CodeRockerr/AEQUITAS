"""
AEQUITAS — ML model API endpoints.

POST /api/v1/ml/regime/{ticker}     detect market regimes
POST /api/v1/ml/forecast/{ticker}   forecast next-day return
"""

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.algorithms.ml.forecaster import forecast_next_day, train_forecaster
from app.algorithms.ml.regime_detector import (
    REGIME_COLORS,
    Regime,
    detect_regimes,
    fit_regime_model,
)
from app.db import get_db
from app.models.market_data import OHLCVBar

router = APIRouter(prefix="/api/v1/ml")


# ── Response schemas ──────────────────────────────────────────


class RegimeResponse(BaseModel):
    ticker: str
    current_regime: str
    current_regime_prob: float
    current_regime_color: str
    regime_sequence: list[str]
    regime_stats: dict
    transition_matrix: list[list[float]]
    n_observations: int


class ShapDriverResponse(BaseModel):
    feature: str
    shap_value: float
    direction: str
    magnitude: float


class ForecastResponse(BaseModel):
    ticker: str
    predicted_return_pct: str
    direction: str
    confidence: float
    top_drivers: list[ShapDriverResponse]
    model_metrics: dict
    n_training_samples: int


# ── Helpers ───────────────────────────────────────────────────


async def _fetch_ohlcv_df(
    db: AsyncSession,
    ticker: str,
    min_rows: int = 100,
) -> pd.DataFrame:
    """Fetch stored OHLCV bars as a pandas DataFrame."""
    result = await db.execute(
        select(
            OHLCVBar.time,
            OHLCVBar.open,
            OHLCVBar.high,
            OHLCVBar.low,
            OHLCVBar.close,
            OHLCVBar.volume,
        )
        .where(
            OHLCVBar.ticker == ticker.upper(),
            OHLCVBar.interval == "1d",
        )
        .order_by(OHLCVBar.time.asc())
    )
    rows = result.all()

    if len(rows) < min_rows:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Need {min_rows}+ bars for {ticker}, have {len(rows)}. "
                f"Call POST /api/v1/market-data/{ticker}/ingest?period=2y first."
            ),
        )

    df = pd.DataFrame(
        rows,
        columns=["time", "open", "high", "low", "close", "volume"],
    )
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    return df


# ── Endpoints ─────────────────────────────────────────────────


@router.post("/regime/{ticker}", response_model=RegimeResponse)
async def detect_market_regime(
    ticker: str,
    n_regimes: int = 3,
    db: AsyncSession = Depends(get_db),
) -> RegimeResponse:
    """
    Detect market regimes using Hidden Markov Model.

    Classifies each trading day into Bull, Bear, or High Volatility
    based on return patterns. Requires 100+ days of data.
    """
    df = await _fetch_ohlcv_df(db, ticker, min_rows=100)

    # Compute log returns as a pandas Series first, then drop NaN,
    # then convert to numpy — avoids calling .dropna() on NDArray
    close_series: pd.Series = df["close"]
    lratio_series: pd.Series = close_series / close_series.shift(1)
    log_returns_series: pd.Series = lratio_series.apply(np.log).dropna()
    returns: np.ndarray = log_returns_series.to_numpy(dtype=np.float64)

    try:
        fitted = fit_regime_model(returns, n_regimes=n_regimes)
        result = detect_regimes(fitted, returns)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Regime detection failed: {e}",
        ) from e

    current_regime_enum = Regime(result.current_regime)
    color = REGIME_COLORS.get(current_regime_enum, "#888780")

    return RegimeResponse(
        ticker=ticker.upper(),
        current_regime=result.current_regime_label,
        current_regime_prob=result.current_regime_prob,
        current_regime_color=color,
        regime_sequence=result.regime_labels[-60:],
        regime_stats=result.regime_stats,
        transition_matrix=result.transition_matrix,
        n_observations=len(returns),
    )


@router.post("/forecast/{ticker}", response_model=ForecastResponse)
async def forecast_return(
    ticker: str,
    db: AsyncSession = Depends(get_db),
) -> ForecastResponse:
    """
    Forecast next-day return using XGBoost + SHAP explanations.

    Trains on technical features from stored price history.
    Requires 200+ trading days (~1 year) for reliable training.
    Training takes ~2-5 seconds.
    """
    df = await _fetch_ohlcv_df(db, ticker, min_rows=200)

    try:
        trained = train_forecaster(df)
        forecast = forecast_next_day(trained, df)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Forecasting failed: {e}",
        ) from e

    return ForecastResponse(
        ticker=ticker.upper(),
        predicted_return_pct=forecast.predicted_return_pct,
        direction=forecast.direction,
        confidence=forecast.confidence,
        top_drivers=[ShapDriverResponse(**d) for d in forecast.top_drivers],
        model_metrics={
            "mae": trained.mae,
            "rmse": trained.rmse,
            "directional_accuracy": f"{trained.directional_accuracy * 100:.1f}%",
        },
        n_training_samples=trained.n_train,
    )
