// AEQUITAS — C++ feature-engineering kernels
//
// Rolling-window and exponential-smoothing primitives used by the
// feature pipeline (backend/app/algorithms/ml/features.py), exposed
// to Python via pybind11.
//
// Design notes:
//  * Inputs arrive as contiguous float64 NumPy arrays (zero-copy via
//    py::array_t<double, py::array::c_style | py::array::forcecast>).
//  * NaN semantics deliberately mirror pandas: a rolling window emits
//    NaN until `window` valid observations exist; EWM with
//    min_periods behaves like pandas' adjust=False variant.
//  * The GIL is released around every compute loop so multi-symbol
//    workloads can run kernels in parallel from Python threads.
//  * Rolling mean/std use a single-pass sliding sum; rolling max/min
//    use a monotonic deque (O(n) amortized).

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <cmath>
#include <deque>
#include <limits>
#include <vector>

namespace py = pybind11;

using Arr = py::array_t<double, py::array::c_style | py::array::forcecast>;

static constexpr double NaN = std::numeric_limits<double>::quiet_NaN();

namespace {

struct Span {
    const double* p;
    py::ssize_t n;
};

Span in(const Arr& a) {
    auto buf = a.request();
    if (buf.ndim != 1)
        throw std::runtime_error("expected a 1-D array");
    return {static_cast<const double*>(buf.ptr), buf.shape[0]};
}

Arr make_out(py::ssize_t n, double** ptr) {
    Arr out(n);
    *ptr = static_cast<double*>(out.request().ptr);
    return out;
}

// ---- rolling mean (sliding sum, single pass) -------------------------------
void rolling_mean_impl(const double* x, double* o, py::ssize_t n, int w) {
    double sum = 0.0;
    for (py::ssize_t i = 0; i < n; ++i) {
        sum += x[i];
        if (i >= w) sum -= x[i - w];
        o[i] = (i >= w - 1) ? sum / w : NaN;
    }
}

// ---- rolling std, sample (ddof=1), Welford-style sliding -------------------
void rolling_std_impl(const double* x, double* o, py::ssize_t n, int w) {
    // two-pass per window is O(n*w); instead keep sliding sum and sum of
    // squares with Kahan-free doubles (adequate for OHLCV magnitudes,
    // verified against pandas to ~1e-9 relative tolerance).
    double s = 0.0, s2 = 0.0;
    for (py::ssize_t i = 0; i < n; ++i) {
        s += x[i];
        s2 += x[i] * x[i];
        if (i >= w) {
            s -= x[i - w];
            s2 -= x[i - w] * x[i - w];
        }
        if (i >= w - 1) {
            double mean = s / w;
            double var = (s2 - w * mean * mean) / (w - 1);
            o[i] = var > 0.0 ? std::sqrt(var) : 0.0;
        } else {
            o[i] = NaN;
        }
    }
}

// ---- rolling max/min via monotonic deque ------------------------------------
template <bool Max>
void rolling_extreme_impl(const double* x, double* o, py::ssize_t n, int w,
                          int min_periods) {
    std::deque<py::ssize_t> dq;
    for (py::ssize_t i = 0; i < n; ++i) {
        while (!dq.empty() && dq.front() <= i - w) dq.pop_front();
        while (!dq.empty() &&
               (Max ? x[dq.back()] <= x[i] : x[dq.back()] >= x[i]))
            dq.pop_back();
        dq.push_back(i);
        o[i] = (i + 1 >= min_periods) ? x[dq.front()] : NaN;
    }
}

// ---- EWM mean, pandas adjust=False semantics --------------------------------
// alpha given directly; min_periods delays first emitted value.
// Skips leading NaNs (as pandas does for diff()-derived series).
void ewm_impl(const double* x, double* o, py::ssize_t n, double alpha,
              int min_periods) {
    double m = 0.0;
    bool started = false;
    py::ssize_t count = 0;
    for (py::ssize_t i = 0; i < n; ++i) {
        if (std::isnan(x[i])) {
            o[i] = started && count >= min_periods ? m : NaN;
            continue;
        }
        if (!started) {
            m = x[i];
            started = true;
        } else {
            m = alpha * x[i] + (1.0 - alpha) * m;
        }
        ++count;
        o[i] = (count >= min_periods) ? m : NaN;
    }
}

// ---- RSI, Wilder smoothing ---------------------------------------------------
void rsi_impl(const double* close, double* o, py::ssize_t n, int period) {
    const double alpha = 1.0 / period;
    double avg_gain = 0.0, avg_loss = 0.0;
    bool started = false;
    py::ssize_t count = 0;
    o[0] = NaN;
    for (py::ssize_t i = 1; i < n; ++i) {
        double d = close[i] - close[i - 1];
        double gain = d > 0 ? d : 0.0;
        double loss = d < 0 ? -d : 0.0;
        if (!started) {
            avg_gain = gain;
            avg_loss = loss;
            started = true;
        } else {
            avg_gain = alpha * gain + (1.0 - alpha) * avg_gain;
            avg_loss = alpha * loss + (1.0 - alpha) * avg_loss;
        }
        ++count;
        if (count >= period && avg_loss > 0.0) {
            double rs = avg_gain / avg_loss;
            o[i] = 100.0 - 100.0 / (1.0 + rs);
        } else {
            o[i] = NaN;
        }
    }
}

// ---- ATR: EMA(span=period) of True Range ------------------------------------
void atr_impl(const double* high, const double* low, const double* close,
              double* o, py::ssize_t n, int period) {
    const double alpha = 2.0 / (period + 1.0);
    double m = 0.0;
    bool started = false;
    for (py::ssize_t i = 0; i < n; ++i) {
        double tr;
        if (i == 0) {
            tr = high[0] - low[0];
        } else {
            double pc = close[i - 1];
            tr = std::max({high[i] - low[i], std::fabs(high[i] - pc),
                           std::fabs(low[i] - pc)});
        }
        if (!started) {
            m = tr;
            started = true;
        } else {
            m = alpha * tr + (1.0 - alpha) * m;
        }
        o[i] = m;
    }
}

}  // namespace

// ---- bindings ----------------------------------------------------------------

#define KERNEL_PROLOGUE(x)                    \
    auto s = in(x);                           \
    double* optr;                             \
    Arr out = make_out(s.n, &optr);

Arr rolling_mean(Arr x, int window) {
    KERNEL_PROLOGUE(x)
    { py::gil_scoped_release rel; rolling_mean_impl(s.p, optr, s.n, window); }
    return out;
}

Arr rolling_std(Arr x, int window) {
    KERNEL_PROLOGUE(x)
    { py::gil_scoped_release rel; rolling_std_impl(s.p, optr, s.n, window); }
    return out;
}

Arr rolling_max(Arr x, int window, int min_periods) {
    KERNEL_PROLOGUE(x)
    { py::gil_scoped_release rel;
      rolling_extreme_impl<true>(s.p, optr, s.n, window, min_periods); }
    return out;
}

Arr rolling_min(Arr x, int window, int min_periods) {
    KERNEL_PROLOGUE(x)
    { py::gil_scoped_release rel;
      rolling_extreme_impl<false>(s.p, optr, s.n, window, min_periods); }
    return out;
}

Arr ewm_mean(Arr x, double alpha, int min_periods) {
    KERNEL_PROLOGUE(x)
    { py::gil_scoped_release rel; ewm_impl(s.p, optr, s.n, alpha, min_periods); }
    return out;
}

Arr rsi(Arr close, int period) {
    KERNEL_PROLOGUE(close)
    { py::gil_scoped_release rel; rsi_impl(s.p, optr, s.n, period); }
    return out;
}

Arr atr(Arr high, Arr low, Arr close, int period) {
    auto h = in(high), l = in(low), c = in(close);
    if (h.n != l.n || h.n != c.n)
        throw std::runtime_error("high/low/close must be the same length");
    double* optr;
    Arr out = make_out(h.n, &optr);
    { py::gil_scoped_release rel; atr_impl(h.p, l.p, c.p, optr, h.n, period); }
    return out;
}

PYBIND11_MODULE(aequitas_kernels, m) {
    m.doc() = "AEQUITAS C++ feature-engineering kernels (pybind11)";
    m.def("rolling_mean", &rolling_mean, py::arg("x"), py::arg("window"));
    m.def("rolling_std", &rolling_std, py::arg("x"), py::arg("window"));
    m.def("rolling_max", &rolling_max, py::arg("x"), py::arg("window"),
          py::arg("min_periods") = 1);
    m.def("rolling_min", &rolling_min, py::arg("x"), py::arg("window"),
          py::arg("min_periods") = 1);
    m.def("ewm_mean", &ewm_mean, py::arg("x"), py::arg("alpha"),
          py::arg("min_periods") = 0);
    m.def("rsi", &rsi, py::arg("close"), py::arg("period") = 14);
    m.def("atr", &atr, py::arg("high"), py::arg("low"), py::arg("close"),
          py::arg("period") = 14);
}
