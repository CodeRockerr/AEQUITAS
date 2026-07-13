# AEQUITAS C++ Kernels

C++20 implementations of the rolling-window and exponential-smoothing
primitives behind the AEQUITAS feature-engineering pipeline
([`backend/app/algorithms/ml/features.py`](../app/algorithms/ml/features.py)),
exposed to Python via [pybind11](https://github.com/pybind/pybind11).

This directory is the subject of a poster submission to **CppCon 2026**:
*"Accelerating Quantitative Feature Engineering: A C++20/pybind11 Extension
for a Python-Based Trading Research Platform."*

## Why

AEQUITAS computes 19 engineered features (log returns, RSI, MACD, rolling
realized volatility, Bollinger statistics, volume ratios, 52-week levels,
ATR) over OHLCV history. These rolling-window computations sit on the
platform's hottest path and were originally written in pandas. This
extension ports the underlying kernels to C++ and measures what that
actually buys — including the cases where it buys little.

## Kernels

| Kernel | Algorithm | pandas equivalent |
|---|---|---|
| `rolling_mean(x, window)` | single-pass sliding sum | `s.rolling(w).mean()` |
| `rolling_std(x, window)` | sliding sum + sum-of-squares, ddof=1 | `s.rolling(w).std()` |
| `rolling_max/min(x, window, min_periods)` | monotonic deque, O(n) amortized | `s.rolling(w, min_periods=m).max()` |
| `ewm_mean(x, alpha, min_periods)` | recurrence, `adjust=False` semantics | `s.ewm(alpha=a, adjust=False).mean()` |
| `rsi(close, period)` | Wilder smoothing (alpha = 1/n) | `_rsi()` in features.py |
| `atr(high, low, close, period)` | true range + EMA(span=n) | `_atr()` in features.py |

Design points:

- **Zero-copy interop** — inputs are `py::array_t<double, c_style>`;
  NumPy buffers are read and written in place, no copies at the boundary.
- **GIL released** around every compute loop (`py::gil_scoped_release`),
  so multi-symbol workloads parallelize from a plain
  `ThreadPoolExecutor`.
- **pandas-faithful NaN semantics** — `min_periods` emission rules,
  `adjust=False` EWM recurrence, and NaN skipping on diff()-derived
  series are reproduced deliberately, so kernels are drop-in
  replacements. Verified to ≤ 4e-9 absolute deviation
  (most kernels ≤ 1e-12) by `test_equivalence.py`.

## Build

Quick (development):

```bash
pip install pybind11
g++ -O3 -march=native -std=c++20 -shared -fPIC \
    $(python3 -m pybind11 --includes) kernels.cpp \
    -o aequitas_kernels$(python3-config --extension-suffix)
```

Packaged (CMake + scikit-build-core):

```bash
pip install .          # builds a wheel via CMake
pip install .[test]    # + pandas/pytest for the equivalence suite
```

## Verify & benchmark

```bash
python3 test_equivalence.py   # compares every kernel against pandas/features.py
python3 benchmark.py          # median-of-7 timings, 10K/100K/1M rows
```

Preliminary single-core results (Linux, g++ 13, -O3; run
`benchmark.py` on your own hardware — numbers vary):

| rows | kernel | pandas (ms) | C++ (ms) | speedup |
|---:|---|---:|---:|---:|
| 1,000,000 | rolling_std(21) | 44.95 | 4.84 | 9.3x |
| 1,000,000 | rolling_max(252) | 44.56 | 17.62 | 2.5x |
| 1,000,000 | ewm(span=12) | 22.37 | 3.21 | 7.0x |
| 1,000,000 | rsi(14) | 96.63 | 10.06 | 9.6x |
| 1,000,000 | atr(14) | 270.35 | 3.37 | 80.2x |

The spread is the point: gains are largest where the pandas formulation
forces intermediate DataFrame construction (ATR), and smallest where
pandas already uses an efficient algorithm (rolling max). Multi-core
scaling of the GIL-released parallel path is being validated on
multi-core hardware.

## Status / roadmap

- [x] Seven core kernels, pybind11 bindings, zero-copy, GIL release
- [x] Numerical-equivalence suite vs. the production pandas pipeline
- [x] Preliminary single-core benchmark matrix
- [x] CMake + scikit-build-core packaging
- [ ] Drop-in C++ backend for the full 19-feature `compute_features`
- [ ] Multi-core parallel scaling benchmarks
- [ ] Intraday-scale datasets, warm/cold cache, NumPy-vectorized middle ground
- [ ] Wire into the Dockerized deployment

## Author

Adit Jigneshbhai Shah — ashah45@ncsu.edu
