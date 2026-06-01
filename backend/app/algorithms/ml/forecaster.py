"""
AEQUITAS — XGBoost return forecaster with SHAP explanations.

Predicts next-day log returns using technical features.
SHAP values explain which features drove each prediction.

XGBoost works by:
  1. Starting with a simple prediction (mean)
  2. Fitting a tree to the residuals (errors)
  3. Adding the tree * learning_rate to the prediction
  4. Repeating steps 2-3 for n_estimators trees

Each tree corrects the previous ensemble's mistakes.
This is gradient boosting — gradient descent in function space.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import shap  # type: ignore[import-untyped]
import xgboost as xgb
from sklearn.metrics import (  # type: ignore[import-untyped]
    mean_absolute_error,
    mean_squared_error,
)
from sklearn.model_selection import TimeSeriesSplit  # type: ignore[import-untyped]

from app.algorithms.ml.features import ML_FEATURE_COLS, compute_features


@dataclass
class ForecastResult:
    """Output of the return forecaster."""

    predicted_return: float  # next-day log return forecast
    predicted_return_pct: str  # human-readable e.g. "+0.42%"
    direction: str  # "up" or "down"
    confidence: float  # abs(predicted_return) normalised 0-1
    shap_values: dict[str, float]  # feature → SHAP contribution
    top_drivers: list[dict]  # top 5 features driving prediction


@dataclass
class TrainingResult:
    """Output of model training with cross-validation metrics."""

    model: xgb.XGBRegressor
    feature_cols: list[str]
    mae: float  # mean absolute error on validation
    rmse: float  # root mean squared error
    directional_accuracy: float  # % of time direction (up/down) is correct
    n_train: int
    n_val: int


def train_forecaster(
    df: pd.DataFrame,
    test_size: float = 0.2,
    n_cv_splits: int = 5,
) -> TrainingResult:
    """
    Train XGBoost forecaster with time-series cross-validation.

    We use TimeSeriesSplit instead of random train/test split.
    Why? Random splitting leaks future data into training —
    a form of lookahead bias. TimeSeriesSplit always trains on
    the past and validates on the future.

    Args:
        df: raw OHLCV DataFrame
        test_size: fraction of data for final test set
        n_cv_splits: number of cross-validation folds

    Returns:
        TrainingResult with trained model and metrics
    """
    # Compute features
    feat_df = compute_features(df)

    X = feat_df[ML_FEATURE_COLS].values
    y = feat_df["target_1d"].values

    # Temporal train/test split — never shuffle time-series data
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # XGBoost hyperparameters
    # These are reasonable defaults — in production you'd tune with Optuna
    model = xgb.XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,  # prevents overfitting on small samples
        reg_alpha=0.1,  # L1 regularisation
        reg_lambda=1.0,  # L2 regularisation
        random_state=42,
        n_jobs=-1,  # use all CPU cores
        verbosity=0,
    )

    # Time-series cross-validation for hyperparameter evaluation
    tscv = TimeSeriesSplit(n_splits=n_cv_splits)
    cv_mae_scores = []
    cv_dir_acc = []

    for train_idx, val_idx in tscv.split(X_train):
        X_cv_train = X_train[train_idx]
        X_cv_val = X_train[val_idx]
        y_cv_train = y_train[train_idx]
        y_cv_val = y_train[val_idx]

        model.fit(X_cv_train, y_cv_train)
        preds = model.predict(X_cv_val)

        cv_mae_scores.append(mean_absolute_error(y_cv_val, preds))
        # Directional accuracy: did we predict the right sign?
        dir_acc = np.mean(np.sign(preds) == np.sign(y_cv_val))
        cv_dir_acc.append(dir_acc)

    # Final fit on full training set
    model.fit(X_train, y_train)
    test_preds = model.predict(X_test)

    mae = float(mean_absolute_error(y_test, test_preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, test_preds)))
    dir_acc = float(np.mean(np.sign(test_preds) == np.sign(y_test)))

    return TrainingResult(
        model=model,
        feature_cols=ML_FEATURE_COLS,
        mae=round(mae, 6),
        rmse=round(rmse, 6),
        directional_accuracy=round(dir_acc, 4),
        n_train=len(X_train),
        n_val=len(X_test),
    )


def forecast_next_day(
    trained: TrainingResult,
    df: pd.DataFrame,
) -> ForecastResult:
    """
    Forecast next-day return and explain with SHAP values.

    Uses the most recent row of features as input.
    SHAP TreeExplainer is exact for tree models (not approximate).

    Args:
        trained: fitted model from train_forecaster()
        df: OHLCV DataFrame (needs recent history for feature computation)

    Returns:
        ForecastResult with prediction and SHAP explanation
    """
    feat_df = compute_features(df)
    X = feat_df[trained.feature_cols].values

    # Predict on the most recent observation
    X_latest = X[-1:, :]
    predicted = float(trained.model.predict(X_latest)[0])

    # SHAP explanation for this prediction
    # TreeExplainer is exact for XGBoost — O(TLD) complexity
    # where T=trees, L=leaves, D=depth
    explainer = shap.TreeExplainer(trained.model)
    shap_vals = explainer.shap_values(X_latest)[0]  # shape: (n_features,)

    shap_dict = {
        col: round(float(val), 6)
        for col, val in zip(trained.feature_cols, shap_vals, strict=False)
    }

    # Top 5 drivers by absolute SHAP value
    sorted_shap = sorted(
        shap_dict.items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )
    top_drivers = [
        {
            "feature": feat,
            "shap_value": val,
            "direction": "↑ bullish" if val > 0 else "↓ bearish",
            "magnitude": abs(val),
        }
        for feat, val in sorted_shap[:5]
    ]

    # Normalise confidence: larger |prediction| = higher confidence
    # Clip to [0, 1] using a typical daily return range of ±2%
    confidence = min(abs(predicted) / 0.02, 1.0)

    pct = predicted * 100
    sign = "+" if pct >= 0 else ""

    return ForecastResult(
        predicted_return=round(predicted, 6),
        predicted_return_pct=f"{sign}{pct:.3f}%",
        direction="up" if predicted >= 0 else "down",
        confidence=round(confidence, 4),
        shap_values=shap_dict,
        top_drivers=top_drivers,
    )
