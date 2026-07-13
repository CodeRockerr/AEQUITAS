"""Benchmark: pandas vs C++ kernels, single-kernel and multi-symbol parallel."""
import sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/claude/AEQUITAS/backend/cpp")
sys.path.insert(0, "/home/claude/AEQUITAS/backend")
import aequitas_kernels as ck
from app.algorithms.ml.features import _rsi, _atr

rng = np.random.default_rng(7)

def bench(fn, reps=7):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return np.median(ts)

print(f"{'rows':>10} {'kernel':22} {'pandas(ms)':>11} {'C++(ms)':>9} {'speedup':>8}")
for n in (10_000, 100_000, 1_000_000):
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    s, hs, ls = pd.Series(close), pd.Series(high), pd.Series(low)

    cases = [
        ("rolling_std(21)", lambda: s.rolling(21).std(), lambda: ck.rolling_std(close, 21)),
        ("rolling_max(252)", lambda: hs.rolling(252, min_periods=1).max(), lambda: ck.rolling_max(high, 252, 1)),
        ("ewm(span=12)", lambda: s.ewm(span=12, adjust=False).mean(), lambda: ck.ewm_mean(close, 2/13, 0)),
        ("rsi(14)", lambda: _rsi(s, 14), lambda: ck.rsi(close, 14)),
        ("atr(14)", lambda: _atr(hs, ls, s, 14), lambda: ck.atr(high, low, close, 14)),
    ]
    for name, pfn, cfn in cases:
        tp, tc = bench(pfn) * 1e3, bench(cfn) * 1e3
        print(f"{n:>10,} {name:22} {tp:>11.3f} {tc:>9.3f} {tp/tc:>7.1f}x")
    print()

# multi-symbol parallel: 8 symbols x 1M rows, RSI, GIL released in C++
n, nsym = 1_000_000, 8
data = [100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))) for _ in range(nsym)]
series = [pd.Series(d) for d in data]

t_pd = bench(lambda: [_rsi(x, 14) for x in series], reps=3)
t_cpp_seq = bench(lambda: [ck.rsi(d, 14) for d in data], reps=3)
with ThreadPoolExecutor(max_workers=8) as ex:
    t_cpp_par = bench(lambda: list(ex.map(lambda d: ck.rsi(d, 14), data)), reps=3)

print(f"multi-symbol RSI, {nsym} x {n:,} rows:")
print(f"  pandas sequential : {t_pd*1e3:9.1f} ms")
print(f"  C++ sequential    : {t_cpp_seq*1e3:9.1f} ms  ({t_pd/t_cpp_seq:.1f}x)")
print(f"  C++ 8 threads     : {t_cpp_par*1e3:9.1f} ms  ({t_pd/t_cpp_par:.1f}x, GIL released)")
import os
print(f"\ncpus available: {os.cpu_count()}")
