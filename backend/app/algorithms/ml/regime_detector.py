"""
AEQUITAS — HMM market regime detector.

Uses a Gaussian Hidden Markov Model to classify market into
latent regimes from daily return observations.

The model learns three things from data:
  1. Transition matrix A: P(regime_t | regime_{t-1})
  2. Emission params: μ and σ for returns in each regime
  3. Initial distribution π: P(regime_0)

After fitting, we use Viterbi decoding to find the most likely
sequence of regimes given the observed returns.

Library: hmmlearn — a scikit-learn compatible HMM implementation.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import cast

import numpy as np
from hmmlearn import hmm  # type: ignore[import-untyped]
from numpy.typing import NDArray


class Regime(IntEnum):
    """
    Market regimes detected by the HMM.

    We label them post-hoc by inspecting the emission parameters:
    - The state with highest mean return → Bull
    - The state with lowest mean return → Bear
    - The state with highest volatility → HighVol
    """

    BULL = 0
    BEAR = 1
    HIGH_VOL = 2


REGIME_LABELS = {
    Regime.BULL: "Bull",
    Regime.BEAR: "Bear",
    Regime.HIGH_VOL: "High Volatility",
}

REGIME_COLORS = {
    Regime.BULL: "#1D9E75",
    Regime.BEAR: "#E24B4A",
    Regime.HIGH_VOL: "#EF9F27",
}


@dataclass
class RegimeResult:
    """Output of the HMM regime detector."""

    regimes: list[int]
    regime_labels: list[str]
    regime_probs: list[list[float]]
    current_regime: int
    current_regime_label: str
    current_regime_prob: float
    transition_matrix: list[list[float]]
    regime_stats: dict


@dataclass
class FittedHMM:
    """A trained HMM model with metadata."""

    model: hmm.GaussianHMM
    n_regimes: int
    regime_map: dict[int, Regime]
    score: float


def fit_regime_model(
    returns: NDArray[np.float64],
    n_regimes: int = 3,
    n_iter: int = 200,
    random_state: int = 42,
) -> FittedHMM:
    """
    Fit a Gaussian HMM to return data using Baum-Welch (EM).

    Args:
        returns: 1D array of daily log returns
        n_regimes: number of hidden states
        n_iter: maximum EM iterations
        random_state: for reproducibility
    """
    X = returns.reshape(-1, 1)

    model = hmm.GaussianHMM(
        n_components=n_regimes,
        covariance_type="diag",
        n_iter=n_iter,
        random_state=random_state,
        tol=1e-4,
    )
    model.fit(X)
    score = float(model.score(X))

    # ── Label regimes by emission characteristics ─────────────
    means = model.means_.flatten()

    # covars_ can be None before fitting — guard against it
    covars = model.covars_
    if covars is None:
        raise ValueError("HMM fitting failed — covars_ is None")

    sorted_by_mean = np.argsort(means)

    if n_regimes == 3:
        bear_state = int(sorted_by_mean[0])
        bull_state = int(sorted_by_mean[2])
        high_vol_state = int(sorted_by_mean[1])

        regime_map: dict[int, Regime] = {
            bull_state: Regime.BULL,
            bear_state: Regime.BEAR,
            high_vol_state: Regime.HIGH_VOL,
        }
    else:
        regime_map = {}
        for i, state in enumerate(sorted_by_mean):
            regime_map[int(state)] = Regime(min(i, 2))

    return FittedHMM(
        model=model,
        n_regimes=n_regimes,
        regime_map=regime_map,
        score=score,
    )


def detect_regimes(
    fitted: FittedHMM,
    returns: NDArray[np.float64],
) -> RegimeResult:
    """
    Decode regime sequence from returns using fitted HMM.

    Uses Viterbi algorithm for the most likely state sequence,
    and forward-backward for posterior probabilities.
    """
    X = returns.reshape(-1, 1)
    n = fitted.n_regimes

    # Viterbi decoding
    _, raw_states = fitted.model.decode(X, algorithm="viterbi")

    # Posterior probabilities — shape (n_samples, n_states)
    raw_probs = fitted.model.predict_proba(X)

    # Map raw states → named Regime enum values
    regimes = [int(fitted.regime_map[int(s)].value) for s in raw_states]
    regime_labels = [REGIME_LABELS[Regime(r)] for r in regimes]

    # Reorder probability columns to match Regime enum order
    reordered_probs = np.zeros_like(raw_probs)
    for model_state, regime in fitted.regime_map.items():
        if model_state < raw_probs.shape[1]:
            reordered_probs[:, regime.value] = raw_probs[:, model_state]

    # Explicit cast so Pylance knows this is list[list[float]]
    regime_probs = cast(
        list[list[float]],
        reordered_probs.tolist(),
    )

    # Current regime
    current_raw = regimes[-1]
    current_regime = Regime(current_raw)
    current_prob = float(reordered_probs[-1, current_raw])

    # Transition matrix reordered to match regime labels
    raw_trans = fitted.model.transmat_
    trans = np.zeros((n, n))
    for from_state, from_regime in fitted.regime_map.items():
        for to_state, to_regime in fitted.regime_map.items():
            if from_state < n and to_state < n:
                trans[from_regime.value, to_regime.value] = raw_trans[
                    from_state, to_state
                ]

    transition_matrix = cast(list[list[float]], trans.tolist())

    # Per-regime statistics
    regime_array = np.array(regimes)
    regime_stats: dict = {}

    for regime in Regime:
        mask = regime_array == regime.value
        if mask.sum() > 0:
            r_returns = returns[mask]
            durations: list[int] = []
            count = 0
            for r in regime_array:
                if r == regime.value:
                    count += 1
                elif count > 0:
                    durations.append(count)
                    count = 0
            if count > 0:
                durations.append(count)

            regime_stats[REGIME_LABELS[regime]] = {
                "mean_daily_return": round(float(np.mean(r_returns)), 6),
                "daily_volatility": round(float(np.std(r_returns)), 6),
                "days_in_regime": int(mask.sum()),
                "pct_of_time": round(float(mask.mean()) * 100, 1),
                "avg_duration_days": round(
                    float(np.mean(durations)) if durations else 0.0, 1
                ),
            }

    return RegimeResult(
        regimes=regimes,
        regime_labels=regime_labels,
        regime_probs=regime_probs,
        current_regime=current_regime.value,
        current_regime_label=REGIME_LABELS[current_regime],
        current_regime_prob=round(current_prob, 4),
        transition_matrix=transition_matrix,
        regime_stats=regime_stats,
    )
