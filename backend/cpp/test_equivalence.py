"""Verify C++ kernels match AEQUITAS pandas implementations."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
import aequitas_kernels as ck
from app.algorithms.ml.features import _rsi, _atr

rng = np.random.default_rng(42)
n = 50_000
close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
s = pd.Series(close)

def check(name, ours, ref, rtol=1e-9, atol=1e-9):
    ref = np.asarray(ref, dtype=float)
    ok = np.allclose(ours, ref, rtol=rtol, atol=atol, equal_nan=True)
    maxdiff = np.nanmax(np.abs(ours - ref)) if len(ours) else 0
    print(f"{'PASS' if ok else 'FAIL'}  {name:24s} max|diff|={maxdiff:.2e}")
    return ok

results = []
results.append(check("rolling_mean(20)", ck.rolling_mean(close, 20), s.rolling(20).mean()))
results.append(check("rolling_std(20)", ck.rolling_std(close, 20), s.rolling(20).std(), rtol=1e-7, atol=1e-9))
results.append(check("rolling_max(252,mp=1)", ck.rolling_max(high, 252, 1), pd.Series(high).rolling(252, min_periods=1).max()))
results.append(check("rolling_min(252,mp=1)", ck.rolling_min(low, 252, 1), pd.Series(low).rolling(252, min_periods=1).min()))
results.append(check("ewm(span=12)", ck.ewm_mean(close, 2/13, 0), s.ewm(span=12, adjust=False).mean()))
results.append(check("rsi(14) vs repo _rsi", ck.rsi(close, 14), _rsi(s, 14), rtol=1e-9, atol=1e-6))
results.append(check("atr(14) vs repo _atr", ck.atr(high, low, close, 14),
                     _atr(pd.Series(high), pd.Series(low), s, 14), rtol=1e-9, atol=1e-9))

# Leading-NaN case: return_1d-style series (np.log(close/close.shift(1)))
# has a single NaN at index 0. This is what vol_10d/21d/63d roll over in
# the full pipeline — pandas "forgets" a stale NaN once it exits the
# window; a naive sliding sum does not. Regression coverage for that fix.
ret = np.log(close[1:] / close[:-1])
ret = np.concatenate([[np.nan], ret])
rs = pd.Series(ret)
results.append(check("rolling_mean(20) w/ leading NaN", ck.rolling_mean(ret, 20), rs.rolling(20).mean()))
results.append(check("rolling_std(21) w/ leading NaN", ck.rolling_std(ret, 21), rs.rolling(21).std(), rtol=1e-7, atol=1e-9))

print("\nALL PASS" if all(results) else "\nSOME FAILED")
sys.exit(0 if all(results) else 1)
