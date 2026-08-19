# AEQUITAS

**Agentic Equity & Quantitative Intelligence Trading Analysis System**

A full-stack quantitative research platform combining real financial algorithms, ML models, real-time price streaming, autonomous LLM agents, and an AI chat interface - all running at $0/month in production.

[![CI](https://github.com/CodeRockerr/AEQUITAS/actions/workflows/ci.yml/badge.svg)](https://github.com/CodeRockerr/AEQUITAS/actions)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Node](https://img.shields.io/badge/Node-20-green)
![Tests](https://img.shields.io/badge/tests-167%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What is this?

AEQUITAS is a personal research platform built to be both a serious portfolio project and the foundation of a real quant/fintech SaaS product. It streams live market data, runs a battery of quantitative finance algorithms and ML models, hands the results to a multi-agent LLM pipeline that researches a company and writes a structured investment thesis - and now includes a floating AI chat widget where users can ask anything about any stock in plain English and get answers grounded in real algorithm output.

Everything in this repo is real, working, and tested. No mocked endpoints, no placeholder data.

**Live demo:** [aequitas-platform.vercel.app](https://aequitas-platform.vercel.app)
**API docs:** [aequitas-api.onrender.com/docs](https://aequitas-api.onrender.com/docs)

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Algorithms & Models](#algorithms--models)
- [Python vs C++ Performance Lab](#python-vs-c-performance-lab)
- [AI Chat Widget](#ai-chat-widget)
- [Real-Time Price Streaming](#real-time-price-streaming)
- [The Agentic Pipeline](#the-agentic-pipeline)
- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Testing](#testing)
- [CI/CD](#cicd)
- [Roadmap](#roadmap)
- [Author](#author)

---

## Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend - Next.js 14, TypeScript, Recharts, lightweight-charts"]
        direction LR
        F1["Overview"] --- F2["Dashboard"] --- F3["Backtests"] --- F4["Theses"] --- F5["Risk"] --- F6["Factors"] --- F7["Agents"] --- F8["Benchmarks"] --- F9["Trading Sim"] --- F10["Chat ◈"]
    end

    subgraph API["API Layer - FastAPI, Pydantic v2, SQLAlchemy async, WebSocket (13 routers)"]
        direction LR
        A1["health"] --- A2["market-data"] --- A3["ml"] --- A4["signals"] --- A5["agents"] --- A6["history"] --- A7["ws/prices"] --- A8["chat"] --- A9["benchmark"] --- A10["ws/live-decision"]
    end

    subgraph Algo["Algorithm Layer"]
        AL1["Pricing & Risk · Portfolio · ML · Signals · Factor Model · Execution · Backtesting"]
    end

    subgraph Native["Native Layer"]
        N1["C++20 kernels (pybind11) - built in prod Docker image, GIL released"]
    end

    subgraph Stream["Real-Time Layer"]
        ST1["Subscriber-tracked WebSocket · Auto-ingest · Market-closed fallback"]
    end

    subgraph Agent["Agent Layer"]
        AG1["LangGraph 4-node graph + News Sentiment + Earnings + Portfolio Construction"]
        AG2["Groq LLM - openai/gpt-oss-120b (free tier)"]
    end

    subgraph Chat["AI Chat"]
        CH1["Groq tool_use - 10 tools → real AEQUITAS endpoints"]
    end

    subgraph Storage["Storage"]
        S1[("Neon - Postgres 16")]
        S2[("Upstash - Redis")]
    end

    Frontend -->|"REST + WebSocket"| API
    API --> Algo & Native & Stream & Agent & Chat
    Algo & Native & Stream & Agent & Chat --> Storage
```

### Production Deployment

| Service | Platform | Notes |
|---|---|---|
| Frontend | Vercel | Auto-deploys on push to `main` |
| Backend (FastAPI) | Render (free tier) | Auto-deploys on push to `main`; migrations run at startup |
| Database | Neon (serverless Postgres 16) | Pooled connection over TLS |
| Cache | Upstash Redis | TLS (`rediss://`), LRU eviction |
| Keep-warm | GitHub Actions | Pings `/health` every 10 min - prevents Render idle spin-down |

**Total hosting cost: $0/month.**

**Cold-start handling:** Render's free tier takes ~50-60s to cold-start. A scheduled GitHub Actions workflow prevents this. On first visit, a full-screen animated loading experience engages the user - typewriter finance facts, a catch-the-ticker mini game, a link to the author's portfolio, and a skip button. Auto-dismisses when the API responds (90s hard cap).

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, lightweight-charts (TradingView) |
| **Backend** | FastAPI, Python 3.13, Pydantic v2, SQLAlchemy 2.0 (async), WebSocket |
| **Database** | PostgreSQL 16 - Neon in production, TimescaleDB Docker image locally |
| **Cache** | Redis - Upstash in production, Docker locally |
| **Agent Orchestration** | LangGraph 0.2 |
| **LLM** | Groq API - `openai/gpt-oss-120b` (free tier, used for agents + chat widget) |
| **ML** | XGBoost, SHAP, hmmlearn, scikit-learn, statsmodels |
| **Native Extensions** | C++20 feature kernels via pybind11 (zero-copy NumPy, GIL-released) - compiled into the production Docker image |
| **Document Processing** | BeautifulSoup4 (SEC filing HTML → text), pypdf (uploaded PDF reports → text) |
| **Migrations** | Alembic (infrastructure-agnostic) |
| **CI/CD** | GitHub Actions - backend (lint/type-check/test), C++ kernels (build + equivalence + benchmark, x86-64), frontend (type-check/lint/build), keep-warm |
| **Testing** | Pytest + pytest-asyncio (167 tests) |

---

## Algorithms & Models

### Pricing & Risk
- **Black-Scholes** option pricer with full Greeks (Delta, Gamma, Vega, Theta, Rho)
- **Implied volatility** solver via Newton-Raphson
- **VaR / CVaR** - historical, parametric, and Monte Carlo methods
- **Mean-variance portfolio optimisation** with efficient frontier

### Machine Learning
- **HMM regime detector** - Bull / Bear / High-Volatility classification
- **XGBoost forecaster** with `TimeSeriesSplit` (zero lookahead bias) + SHAP attribution
- 19-feature pipeline with graceful degradation on short histories (`min_periods=1`)

### C++ Feature Kernels *(CppCon 2026 talk)*
- Rolling mean/std/max/min, EWM (span + Wilder), RSI, ATR reimplemented in **C++20** via **pybind11**
- Zero-copy NumPy buffer exchange, GIL released around every compute loop
- **1.3×–40× per-kernel** · **~20-30× end-to-end** on multi-symbol parallel workloads (measured live - see [Python vs C++ Performance Lab](#python-vs-c-performance-lab))
- Drop-in replacement - identical Python call signature, falls back to pandas if extension not built
- Numerically equivalent to pandas to ≤ 4×10⁻⁹

### Signals & Execution
- **RSI / MACD / Bollinger Bands** - normalised to [-1, +1], combinable into a weighted score
- **Pairs trading** - Engle-Granger cointegration + Kalman filter dynamic hedge ratio
- **Fama-French 3-factor model** - alpha + Market/SMB/HML decomposition with t-statistic
- **TWAP / VWAP / Implementation Shortfall** - execution scheduling with share-distribution charts

### Backtesting
- Vectorised engine (pure numpy/pandas), full tearsheet: Sharpe, Sortino, Calmar, max drawdown, win rate, alpha

---

## Python vs C++ Performance Lab

Two live pages built for the CppCon 2026 talk - every number on them is measured against whatever host is currently serving the request, not hardcoded from a slide.

**Benchmarks** (`/performance`):
- Per-kernel pandas vs. C++ vs. hand-vectorised NumPy comparison, with cold-call vs. warm-call timing and peak-memory (via `tracemalloc`) side by side
- NaN edge-case explorer - runs `rolling_std`/`rolling_max` against clean, leading-NaN, interior-NaN, and all-NaN inputs to show where the NaN-aware sliding-sum fix matters and where the NaN-unsafe kernels are deliberately out of scope
- Thread-count scaling chart (1/2/4/8 threads) on a fixed multi-symbol workload
- Full-pipeline benchmark (`compute_features` vs `compute_features_cpp`, all 19 features) and multi-symbol parallel benchmark, both with GIL-released C++ threads
- "Real backtest, not synthetic" - fetches real ingested OHLCV history, runs the same MACD strategy through the pandas and C++ feature pipelines, and asserts the trading decisions match bar-for-bar
- Click-to-expand source snippets per kernel, a live run counter (Redis), and a reference-vs-live overlay bar for the original dev-machine numbers
- `backend/cpp/make_live_benchmark_chart.py` regenerates the poster-style comparison chart from a running host (local or deployed) instead of hand-updated constants

**Trading Simulation** (`/trading-simulation`):
- `/ws/live-decision` WebSocket streams a synthetic tick feed and races a pandas RSI signal against the C++ kernel on identical data, visualized as two dots crossing the finish line per tick

---

## AI Chat Widget

Every page has a floating **◈** button that opens an AI chat panel. Powered by **Groq's free tier** with tool use - the model calls your real AEQUITAS endpoints to answer questions with actual data, never hallucinated numbers.

**Draggable anywhere on screen** - both the closed button and the open panel can be dragged to any position via pointer events; the panel auto-flips above/below and left/right so it always stays fully visible relative to wherever the button currently is. Position persists across reloads via `localStorage`.

**10 tools available to the model:**

| Tool | What it calls |
|---|---|
| `get_signals` | RSI / MACD / Bollinger momentum signals |
| `get_regime` | HMM market regime detection |
| `get_forecast` | XGBoost return forecast + SHAP |
| `compute_var` | Value at Risk / CVaR |
| `run_thesis` | Full 4-node LangGraph research agent |
| `get_news_sentiment` | Finnhub headlines + LLM scoring |
| `get_earnings` | Earnings calendar + fundamentals analysis |
| `build_portfolio` | Mean-variance optimisation + cointegration |
| `run_backtest` | RSI / MACD / Bollinger backtest |
| `get_factor_model` | Fama-French 3-factor decomposition |

**Example interactions:**
- *"Is AAPL worth buying right now?"* → calls signals + regime + forecast, synthesizes a grounded view
- *"Compare NVDA and AMD risk"* → calls `compute_var` twice, compares results
- *"Build me a portfolio with AAPL, MSFT, NVDA"* → runs full portfolio construction agent
- *"Backtest RSI on TSLA"* → runs backtest, returns Sharpe/drawdown/win rate vs buy-and-hold

Green tool badges on each response show exactly which algorithms were called.

---

## Real-Time Price Streaming

```
Search any ticker → auto-ingest if never seen → WebSocket subscription
→ background refresh every ~12s (only for active subscribers)
→ price pushed to browser instantly
→ market closed? → last known close from DB, flagged is_live=false
```

Dashboard supports full price history (back to IPO) with candlestick + volume charts and 1M/6M/1Y/5Y/All range controls.

This auto-ingest-on-demand behavior now covers every ticker-driven endpoint, not just the Dashboard's search - backtests, signals, the factor model, and thesis generation all auto-ingest price bars (and, for thesis generation, company metadata + SEC filings) the first time a ticker is requested, instead of 404ing with "insufficient data" until someone manually calls `/ingest`.

---

## The Agentic Pipeline

```mermaid
flowchart LR
    research["research<br/>Company data + RAG"] --> quant["quant<br/>HMM + XGBoost + VaR"]
    quant --> thesis_gen["thesis_gen<br/>LLM synthesis"]
    thesis_gen --> critic["critic<br/>Self-critique"]
    critic -->|"revision needed"| research
    critic -->|"approved"| END(["END"])
```

The `research` node auto-ingests on first request for a ticker, so a thesis for a name nobody's touched before still comes back grounded in real data instead of "no company data found":
- **Company metadata** via yFinance's `.info`, if not already stored
- **Real SEC filings** - the most recent 10-K and 10-Q, fetched straight from SEC EDGAR's public API, with iXBRL taxonomy noise stripped before chunking so the RAG store gets actual filing prose (Business, Risk Factors, MD&A) instead of machine-readable tagging data

Plus three standalone agents: **news sentiment**, **earnings analysis**, **portfolio construction** - all on the Agents page with step-by-step progress indicators and Observed → Why it matters → Next action insight strips. News sentiment supports two sources: live Finnhub headlines, or a pasted/uploaded document (`.txt`/`.md`/`.pdf`) for reports Finnhub doesn't index - same LLM scoring either way.

---

## Directory Structure

```
AEQUITAS/
├── backend/
│   ├── app/
│   │   ├── agents/                  # LangGraph + news/earnings/portfolio agents
│   │   ├── algorithms/              # pricing, risk, portfolio, ml, signals, execution, backtesting
│   │   ├── data/ingestion/
│   │   │   ├── market_data.py       # yFinance OHLCV/company-info + ensure_min_bars auto-ingest
│   │   │   └── edgar.py             # SEC EDGAR 10-K/10-Q auto-ingest for the RAG store
│   │   ├── services/
│   │   │   └── price_stream.py      # WebSocket subscriber manager
│   │   └── api/v1/
│   │       ├── chat.py              # Groq chat endpoint with 10 AEQUITAS tools
│   │       ├── extended_agents.py   # news sentiment, earnings, portfolio endpoints
│   │       ├── history.py           # full price history with auto-ingest
│   │       ├── websocket.py         # /ws/prices
│   │       ├── benchmark.py         # kernels/pipeline/parallel/scaling/edge-case/real-backtest/run-count
│   │       ├── live_decision.py     # /ws/live-decision pandas-vs-C++ race
│   │       └── ...                  # health, market_data, pricing, ml, signals, advanced
│   ├── cpp/                         # C++20 kernels (pybind11, CMake, scikit-build-core)
│   │   ├── kernels.cpp              # rolling_mean/std/max/min, ewm, rsi, atr
│   │   ├── benchmark.py             # local pandas-vs-C++ benchmark script
│   │   ├── make_benchmark_chart.py  # static chart from hardcoded numbers
│   │   └── make_live_benchmark_chart.py  # same chart, pulled from a running host
│   ├── alembic/versions/            # infrastructure-agnostic migrations
│   ├── tests/unit/                  # 167 pytest tests
│   └── pyproject.toml
├── frontend/
│   ├── app/                         # 10 pages: Overview, Dashboard, Backtests, Theses, Risk, Factors,
│   │                                 #   Agents, Benchmarks, Trading Simulation, About
│   ├── components/
│   │   ├── chat/
│   │   │   └── ChatWidget.tsx       # floating AI chat widget (renders markdown replies)
│   │   ├── loading/                 # animated loading screen (cold-start UX)
│   │   ├── layout/                  # Sidebar (grouped nav), ThemeProvider
│   │   ├── charts/
│   │   │   └── CandlestickChart.tsx # lightweight-charts OHLC + volume
│   │   └── ui/                      # PageHeader, StatCard, CardGrid, Markdown, Badge, Spinner,
│   │                                 #   AgentProgress, InsightStrip, SectionHeader, QRFooter, SimulationDiagram
│   ├── hooks/
│   │   └── usePriceStream.ts        # WebSocket client with subscription queueing
│   └── lib/api.ts                   # typed API client
├── infra/
│   └── docker-compose.yml
├── .github/workflows/
│   ├── ci.yml                       # backend + C++ kernels (x86-64) + frontend jobs
│   └── keep-warm.yml                # /health ping every 10 min
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.13, Node.js 20, Docker Desktop
- Free [Groq API key](https://console.groq.com)
- Free [Finnhub API key](https://finnhub.io)

### 1. Clone and configure
```bash
git clone https://github.com/CodeRockerr/AEQUITAS.git
cd AEQUITAS
cp .env.example .env   # fill in your values
```

### 2. Start infrastructure
```bash
docker compose -f infra/docker-compose.yml up db redis -d
```

### 3. Backend
```bash
cd backend
pip install -e ".[dev]" --break-system-packages
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend
```bash
cd frontend
npm install && npm run dev
```

Open `http://localhost:3000` - click the **◈** button to try the AI chat widget.

---

## Environment Variables

```bash
DATABASE_URL=postgresql://aequitas:aequitas@localhost:5433/aequitas
REDIS_URL=redis://localhost:6379
CORS_ORIGINS=["http://localhost:3000"]
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=openai/gpt-oss-120b
FINNHUB_API_KEY=your_finnhub_key_here
EDGAR_USER_AGENT=Your Company Name AdminContact@yourdomain.com
APP_ENV=development
APP_DEBUG=true
API_BASE_URL=http://localhost:8000   # set to Render URL in production
```

Frontend: `NEXT_PUBLIC_API_URL` (build-time variable - changing on Vercel requires redeploy).

`EDGAR_USER_AGENT` needs no API key, but SEC's EDGAR does require a User-Agent containing a real, monitored contact - literally the format `"Company Name AdminContact@domain.com"`, not just a descriptive string. Verified empirically: an otherwise-identical request with no email-shaped string in the UA gets 403'd; add one and it's a 200. The default in `config.py` is a placeholder - replace it before relying on filing ingestion in production.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/health` | Liveness check |
| `POST` | `/api/v1/chat` | AI chat with Groq tool use (10 AEQUITAS tools) |
| `WS`   | `/ws/prices` | Real-time price streaming |
| `GET`  | `/api/v1/history/{ticker}?range_=1y` | Full price history, auto-ingests |
| `POST` | `/api/v1/ml/regime/{ticker}` | HMM regime detection |
| `POST` | `/api/v1/ml/forecast/{ticker}` | XGBoost forecast + SHAP |
| `GET`  | `/api/v1/signals/{ticker}` | Combined momentum signal |
| `POST` | `/api/v1/risk/var` | VaR / CVaR |
| `POST` | `/api/v1/pricing/black-scholes` | Options pricing + Greeks |
| `POST` | `/api/v1/backtest/{ticker}/{strategy}` | Backtest (rsi/macd/bollinger) |
| `POST` | `/api/v1/factor-model/{ticker}` | Fama-French 3-factor |
| `POST` | `/api/v1/execution/{ticker}/twap` | TWAP schedule |
| `POST` | `/api/v1/execution/{ticker}/vwap` | VWAP schedule |
| `POST` | `/api/v1/execution/{ticker}/is` | Implementation Shortfall |
| `POST` | `/api/v1/agents/research/{ticker}` | Full 4-node research agent |
| `POST` | `/api/v1/agents/news-sentiment/{ticker}` | News sentiment agent (Finnhub headlines) |
| `POST` | `/api/v1/agents/news-sentiment/analyze-text` | News sentiment on a pasted article/report |
| `POST` | `/api/v1/agents/news-sentiment/extract-text` | Extract text from an uploaded `.txt`/`.md`/`.pdf` |
| `POST` | `/api/v1/agents/earnings/{ticker}` | Earnings analysis agent |
| `POST` | `/api/v1/agents/portfolio` | Portfolio construction agent |
| `GET`  | `/api/v1/benchmark/kernels` | Per-kernel pandas vs C++ vs NumPy benchmark |
| `GET`  | `/api/v1/benchmark/pipeline` | Full `compute_features()` pipeline benchmark |
| `GET`  | `/api/v1/benchmark/parallel` | Multi-symbol parallel (GIL-released) benchmark |
| `GET`  | `/api/v1/benchmark/scaling` | Thread-count scaling sweep |
| `GET`  | `/api/v1/benchmark/edge-case` | NaN edge-case kernel comparison |
| `GET`  | `/api/v1/benchmark/real-backtest` | Real-data pandas vs C++ backtest validation |
| `GET`  | `/api/v1/benchmark/run-count` | Redis-backed live demo run counter |
| `WS`   | `/ws/live-decision` | Live pandas-vs-C++ signal-latency race |

Full interactive docs: `http://localhost:8000/docs`

---

## Testing

```bash
cd backend
ruff format app tests && ruff check app tests
mypy app
pytest tests/unit/ -v
```

**167 tests passing.** Coverage threshold: 65%.

To also test the C++ kernels locally:
```bash
cd backend/cpp
pip install -e .
python test_equivalence.py   # numerical equivalence vs. pandas, ≤4e-9
python benchmark.py          # pandas vs C++ timings, 10K/100K/1M rows
```

---

## CI/CD

- **CI** (`ci.yml`): three parallel jobs on every push and PR -
  1. **Backend** - Ruff, Mypy, Pytest
  2. **C++ kernels (x86-64)** - builds `aequitas_kernels`, checks numerical equivalence vs. pandas, runs the benchmark, publishes results to the job summary
  3. **Frontend** - tsc, ESLint, `next build`
- **Keep-warm** (`keep-warm.yml`): pings `/health` every 10 minutes - prevents Render idle spin-down, doubles as uptime monitoring
- Branch protection on `main` - all jobs must pass before merge

---

## Roadmap

### Completed
- [x] **Week 1-8** - Foundation, data pipeline, algorithms (Black-Scholes, VaR, portfolio, HMM, XGBoost, signals, backtesting)
- [x] **Week 9** - Production deployment (originally Railway, migrated to Render + Neon + Upstash)
- [x] **Week 10** - Real-time WebSocket streaming, auto-ingest, candlestick charts, Factors page
- [x] **Week 11** - 3 additional agents (news sentiment, earnings, portfolio construction); AgentProgress + InsightStrip UX
- [x] **Week 12** - Infrastructure migration to $0/month stack; keep-warm workflow
- [x] **Week 13** - C++20 acceleration layer; CppCon 2026 talk accepted
- [x] **Week 14** - Animated loading screen with mini game and portfolio link
- [x] **Week 15** - Groq-powered AI chat widget with 10 AEQUITAS tools
- [x] **Week 16** - Python vs C++ Performance Lab: Benchmarks + Trading Simulation pages, NumPy/memory/thread-scaling comparisons, NaN edge-case explorer, real-data backtest validation, live run counter, C++ kernels CI job, compiled extension in the production Docker image
- [x] **Week 17** - Markdown rendering for all AI-generated text (theses, critiques, chat replies); fixed stat-card overflow/dead-space layout bugs across every page; capped backtest lookback windows to prevent return-compounding blowups; Groq model migration off a deprecated model
- [x] **Week 18** - Draggable AI chat widget (position persists via `localStorage`); document/report sentiment scoring via pasted text or uploaded `.txt`/`.md`/`.pdf`; automatic SEC EDGAR filing ingestion for thesis generation (real 10-K/10-Q citations); auto-ingest now covers every ticker-driven endpoint, not just the Dashboard's search; replaced CSS Grid card layouts with flexbox to eliminate dead space in unevenly-filled rows; fixed chart-tooltip text contrast in dark mode across all 9 tooltips

### In Progress / Next
- [ ] **MCP server** - Claude.ai compatible MCP endpoint so users can connect AEQUITAS as an integration in Claude.ai
- [ ] **C++ pipeline integration in production** - `compute_features_cpp()` exists and is benchmarked live, but the real ML forecaster still calls the pure-Python `compute_features()`; swap it once the C++ path has more production soak time
- [ ] **Locked-in benchmark numbers** - a few clean parallel-benchmark re-runs on an idle machine to settle on one headline speedup figure (currently ranges ~20-31× depending on machine load)
- [ ] **Sidebar mobile responsiveness** - not yet revisited for small viewports

### Planned - Enterprise SaaS Phase
1. Auth + RBAC (NextAuth.js)
2. Billing (Stripe)
3. Consumer dashboard (watchlists, saved theses, portfolio tracker)
4. Admin panel
5. Scale (rate limiting, Sentry, PostHog)

---

## Author

**Adit Shah** - MS Computer Science, NC State University

- GitHub: [@CodeRockerr](https://github.com/CodeRockerr)
- LinkedIn: [@shah-adit0404](https://www.linkedin.com/in/shah-adit0404/)
- Portfolio: [adit-2d-portfolio.vercel.app](https://adit-2d-portfolio.vercel.app/)

---

## License

MIT - see [LICENSE](LICENSE) for details.
