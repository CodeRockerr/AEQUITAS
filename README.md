# AEQUITAS

**Agentic Equity & Quantitative Intelligence Trading Analysis System**

A full-stack quantitative research platform combining real financial algorithms, ML models, real-time price streaming, and an autonomous LLM agent pipeline to generate institutional-grade investment theses — automatically.

[![CI](https://github.com/CodeRockerr/AEQUITAS/actions/workflows/ci.yml/badge.svg)](https://github.com/CodeRockerr/AEQUITAS/actions)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Node](https://img.shields.io/badge/Node-20-green)
![Tests](https://img.shields.io/badge/tests-152%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What is this?

AEQUITAS is a personal research platform built to be both a serious portfolio project and the foundation of a real quant/fintech SaaS product. It streams live market data, runs a battery of quantitative finance algorithms and ML models, then hands the results to a multi-agent LLM pipeline that researches a company, evaluates the data, and writes a structured investment thesis — citing sources and critiquing its own conclusions before presenting them.

Everything in this repo is real, working, and tested. No mocked endpoints, no placeholder data — search any ticker and the platform auto-ingests it.

**Live demo:** [aequitas-three.vercel.app](https://aequitas-three.vercel.app)
**API docs:** [aequitas-api.onrender.com/docs](https://aequitas-api.onrender.com/docs)

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Algorithms & Models](#algorithms--models)
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
    subgraph Frontend["Frontend — Next.js 14, TypeScript, Recharts, lightweight-charts"]
        direction LR
        F1["Overview"] --- F2["Dashboard"] --- F3["Backtests"] --- F4["Theses"] --- F5["Risk"] --- F6["Factors"] --- F7["Agents"] --- F8["About"]
    end

    subgraph API["API Layer — FastAPI, Pydantic v2, SQLAlchemy async, WebSocket"]
        direction LR
        A1["health"] --- A2["market-data"] --- A3["pricing-risk"] --- A4["ml"] --- A5["signals"] --- A6["agents"] --- A7["history"] --- A8["ws/prices"]
    end

    subgraph Algo["Algorithm Layer"]
        direction TB
        AL1["Pricing & Risk<br/>Black-Scholes · Greeks · VaR/CVaR · Monte Carlo"]
        AL2["Portfolio<br/>Mean-variance optimiser"]
        AL3["ML<br/>HMM regime · XGBoost + SHAP"]
        AL4["Signals<br/>RSI/MACD/Bollinger · Pairs trading + Kalman filter"]
        AL5["Factor Model & Execution<br/>Fama-French · TWAP/VWAP/IS"]
        AL6["Backtester<br/>Vectorised, full tearsheet"]
    end

    subgraph Stream["Real-Time Layer"]
        direction TB
        ST1["Subscriber-tracked WebSocket<br/>broadcast manager"]
        ST2["Background refresh loop<br/>per actively-watched ticker"]
        ST3["Auto-ingest on first request<br/>+ market-closed fallback to last close"]
    end

    subgraph Agent["Agent Layer"]
        direction TB
        AG1["LangGraph 4-node graph:<br/>research → quant → thesis_gen → critic"]
        AG2["Groq LLM<br/>llama-3.3-70b-versatile"]
    end

    subgraph Data["Data Layer"]
        direction TB
        D1["yFinance ingestion"]
        D2["Time-series OHLCV store<br/>(composite-indexed Postgres)"]
        D3["Document chunk store<br/>for filing RAG"]
    end

    subgraph Storage["Storage"]
        direction LR
        S1[("PostgreSQL 16<br/>(Neon)")]
        S2[("Redis<br/>(Upstash)")]
    end

    Frontend -->|"REST + WebSocket"| API
    API --> Algo
    API --> Stream
    API --> Agent
    API --> Data
    Algo --> Storage
    Stream --> Storage
    Agent --> Storage
    Data --> Storage
```

### Production Deployment

| Service | Platform | Notes |
|---|---|---|
| Frontend | Vercel | Auto-deploys on push to `main`, root directory `frontend` |
| Backend (FastAPI) | Render (free tier) | Auto-deploys on push to `main`, root directory `backend`, build `pip install .`, migrations run at startup (`alembic upgrade head && uvicorn ...`) |
| Database | Neon (serverless Postgres 16) | Pooled (PgBouncer) connection over TLS |
| Cache | Upstash Redis | TLS (`rediss://`), regional, LRU eviction |
| Keep-warm | GitHub Actions | Scheduled workflow pings `/health` every 10 minutes so Render's free tier never idles into a cold start — and doubles as uptime monitoring (failed pings show red in the Actions tab) |

All three infrastructure services are co-located in AWS us-west (Oregon) to keep query latency down. Total hosting cost: **$0/month**.

**Portability note:** the schema migrations are written to be infrastructure-agnostic. Migration 001 converts `ohlcv_bars` into a TimescaleDB hypertable *when the extension is available* (e.g. the local `timescale/timescaledb-ha:pg16` Docker image) and falls back to a plain composite-indexed table on managed Postgres that doesn't ship the extension (e.g. Neon). At current data volumes the `(ticker, time)` index covers all query patterns either way. Similarly, `config.py` translates libpq-style connection parameters (`sslmode=require`, `channel_binding`) into their asyncpg equivalents, so the same code accepts local Docker URLs and managed-Postgres connection strings unchanged.

**Cold-start handling:** Render's free tier spins down after inactivity and takes ~50-60s to cold-start. A scheduled GitHub Actions workflow pings `/health` every 10 minutes to prevent this. On first visit, a full-screen animated loading experience engages the user while the API warms up — typewriter finance facts, a catch-the-ticker mini game, a link to the author's portfolio, and a skip button. The loading screen auto-dismisses the moment the API responds.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, lightweight-charts (TradingView) |
| **Backend** | FastAPI, Python 3.13, Pydantic v2, SQLAlchemy 2.0 (async), native WebSocket support |
| **Database** | PostgreSQL 16 — Neon (serverless) in production, TimescaleDB Docker image locally; migrations apply hypertables automatically where the extension exists |
| **Cache/Queue** | Redis — Upstash in production, Docker locally |
| **Agent Orchestration** | LangGraph 0.2 |
| **LLM** | Groq API — `llama-3.3-70b-versatile` (free tier) |
| **ML** | XGBoost, SHAP, hmmlearn, scikit-learn, statsmodels |
| **Native Extensions** | C++20 feature kernels via pybind11 (zero-copy NumPy interop, GIL-released), CMake + scikit-build-core |
| **Migrations** | Alembic (async, infrastructure-agnostic) |
| **CI/CD** | GitHub Actions (backend + frontend jobs, branch protection, scheduled keep-warm ping) |
| **Linting** | Ruff (backend), ESLint (frontend) |
| **Type Checking** | Mypy (backend), TypeScript strict (frontend) |
| **Testing** | Pytest + pytest-asyncio (152 tests) |
| **Deployment** | Vercel (frontend) + Render (backend) + Neon (Postgres) + Upstash (Redis) — **live, $0/month** |

---

## Algorithms & Models

### Pricing & Risk
- **Black-Scholes** option pricer with full Greeks (Delta, Gamma, Vega, Theta, Rho)
- **Implied volatility** solver via Newton-Raphson
- **VaR / CVaR** — historical, parametric, and Monte Carlo methods
- **Mean-variance portfolio optimisation** with efficient frontier generation

### Machine Learning
- **Hidden Markov Model** regime detector — classifies market state as Bull / Bear / High-Volatility
- **XGBoost return forecaster** trained with `TimeSeriesSplit` (zero lookahead bias), explained via **SHAP**
- 19-feature engineering pipeline (returns, volatility, RSI, MACD, distance from 52-week high/low, volume ratios, etc.)
- 52-week high/low features use `rolling(window, min_periods=1)` with a dynamically capped window, so the pipeline degrades gracefully for tickers with less than 252 days of history instead of dropping every row to `NaN`

### C++ Feature Kernels *(CppCon 2026 poster work)*
- The rolling-window primitives behind the 19-feature pipeline (rolling mean/std/max/min, EWM in span and Wilder parameterisations, RSI, ATR) reimplemented in **C++20**, exposed via **pybind11** with zero-copy NumPy buffer exchange and the **GIL released** around every compute loop
- Verified numerically equivalent to the pandas implementations to ≤4e-9 (`backend/cpp/test_equivalence.py`)
- Measured **1.3x–40x per-kernel speedups** and a **39.8x end-to-end** improvement on multi-symbol parallel workloads (8 × 1M rows RSI: 194.3 ms → 4.9 ms via `ThreadPoolExecutor` on 8 cores, Apple M-series, Apple clang -O3)
- Live head-to-head demo on the **Python vs C++** page, backed by `GET /api/v1/benchmark/kernels` (degrades gracefully where the extension isn't built)
- Full details, build instructions, and benchmark methodology: [`backend/cpp/README.md`](backend/cpp/README.md)

### Signals
- **Momentum signals**: RSI, MACD, Bollinger Bands — each normalised to `[-1, +1]` and combinable into a single weighted score
- **Pairs trading**: Engle-Granger cointegration test + **Kalman filter** for dynamic hedge ratio estimation (more realistic than static OLS)
- **Fama-French 3-factor model**: decomposes returns into Market, SMB (size), and HML (value) factor exposures with alpha t-statistic. UI on the **Factors** page.

### Execution Algorithms
- **TWAP** (Time-Weighted Average Price) — splits an order equally across time intervals
- **VWAP** (Volume-Weighted Average Price) — distributes shares proportional to a U-shaped intraday volume profile
- **Implementation Shortfall** — urgency-parameterised schedule; includes post-trade execution quality analysis. All three visualised as a share-distribution bar chart on the **Factors** page.

### Backtesting
- Vectorised backtesting engine (pure numpy/pandas — no Python loops over time)
- Full tearsheet: Sharpe, Sortino, Calmar ratios, max drawdown, win rate, alpha vs buy-and-hold benchmark

---

## Real-Time Price Streaming

Every ticker on the platform updates live via WebSocket — no manual ingestion required.

```
Person searches any ticker
        ↓
Backend auto-ingests if never seen, or if data is stale (>20h old)
        ↓
WebSocket subscription registers interest in that ticker
        ↓
Background refresh loop fetches a fresh price every ~12s,
  but ONLY for tickers with at least one active subscriber
        ↓
Price pushed to every connected browser watching that ticker
        ↓
If markets are closed (weekends, holidays), falls back to the
  last known daily close from the database, flagged is_live=false
```

The **Dashboard** page supports searching any ticker for full price history — candlestick chart with volume, auto-ingesting back to IPO/listing day on first request, with 1M/6M/1Y/5Y/All range controls.

---

## The Agentic Pipeline

AEQUITAS's signature feature is a 4-node LangGraph agent that autonomously produces investment research:

```mermaid
flowchart TD
    START(["START"]) --> research

    research["<b>research</b><br/>Retrieves company info + SEC filing<br/>chunks via full-text search.<br/>Summarises via LLM."]
    research --> quant

    quant["<b>quant</b><br/>Computes live regime (HMM), momentum<br/>signal, XGBoost forecast + SHAP, and<br/>VaR — using the real algorithm layer."]
    quant --> thesis_gen

    thesis_gen["<b>thesis_gen</b><br/>LLM synthesises a structured thesis:<br/>Overview, Bull Case, Bear Case, Quant<br/>Evidence, Risk Factors, Verdict."]
    thesis_gen --> critic

    critic["<b>critic</b><br/>LLM critiques its own thesis:<br/>unsupported claims, missing risks,<br/>inconsistencies with quant data."]

    critic -->|"revision needed<br/>(max 2 loops)"| research
    critic -->|"approved"| END(["END"])

    style START fill:#1A6B4A,color:#fff
    style END fill:#1A6B4A,color:#fff
    style research fill:#EAF0FB,color:#111
    style quant fill:#EAF0FB,color:#111
    style thesis_gen fill:#EAF0FB,color:#111
    style critic fill:#FBF4E6,color:#111
```

Alongside the research graph, three further standalone agents: **news sentiment** (Finnhub headlines + Groq), **earnings analysis** (Finnhub calendar + fundamentals + Groq), and **portfolio construction** (mean-variance + cointegration + Groq) — all on the **Agents** page with live pipeline-step progress indicators and Observed → Why it matters → Next action insight strips.

---

## Directory Structure

```
AEQUITAS/
├── backend/
│   ├── app/
│   │   ├── agents/                  # LangGraph agent system
│   │   │   ├── state.py             # ResearchState TypedDict
│   │   │   ├── nodes.py             # research/quant/thesis/critic node functions
│   │   │   └── graph.py             # graph construction & compilation
│   │   ├── algorithms/
│   │   │   ├── pricing/             # Black-Scholes + Greeks
│   │   │   ├── risk/                # VaR/CVaR
│   │   │   ├── portfolio/           # mean-variance optimiser
│   │   │   ├── ml/                  # HMM regime, XGBoost forecaster, features
│   │   │   ├── signals/             # momentum, pairs trading, Fama-French
│   │   │   ├── execution/           # TWAP, VWAP, Implementation Shortfall
│   │   │   └── backtesting/         # vectorised backtest engine
│   │   ├── services/
│   │   │   └── price_stream.py      # WebSocket subscriber manager, refresh loop, fallback
│   │   ├── api/v1/                  # FastAPI routers
│   │   │   ├── health.py
│   │   │   ├── market_data.py
│   │   │   ├── market_data_autofetch.py
│   │   │   ├── pricing.py
│   │   │   ├── ml.py
│   │   │   ├── signals.py
│   │   │   ├── agents.py
│   │   │   ├── extended_agents.py   # news sentiment, earnings, portfolio agents
│   │   │   ├── advanced.py          # factor model + execution endpoints
│   │   │   ├── history.py           # full price history with auto-ingest
│   │   │   ├── benchmark.py         # live pandas-vs-C++ kernel benchmark
│   │   │   └── websocket.py         # /ws/prices endpoint
│   │   ├── data/
│   │   │   └── vector/store.py      # document chunk store for RAG
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── config.py                # pydantic-settings + asyncpg URL translation
│   │   ├── db.py                    # async engine + session factory
│   │   └── main.py                  # FastAPI app factory
│   ├── cpp/                         # C++20 feature kernels (pybind11)
│   │   ├── kernels.cpp              # rolling/EWM/RSI/ATR kernels + bindings
│   │   ├── test_equivalence.py      # numerical equivalence vs pandas (≤4e-9)
│   │   ├── benchmark.py             # pandas vs C++ benchmark suite
│   │   ├── CMakeLists.txt
│   │   └── pyproject.toml           # scikit-build-core (pip install ./backend/cpp)
│   ├── alembic/versions/            # infrastructure-agnostic migrations
│   ├── tests/unit/                  # 152 pytest tests
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Overview — real-time ticker tape
│   │   ├── dashboard/page.tsx       # live signals, regime, SHAP, candlestick chart
│   │   ├── backtests/page.tsx       # strategy runner + equity curve
│   │   ├── theses/page.tsx          # agent thesis generator
│   │   ├── risk/page.tsx            # VaR/CVaR + options pricer
│   │   ├── factors/page.tsx         # Fama-French + execution algorithms
│   │   ├── performance/page.tsx     # Python vs C++ live benchmark
│   │   ├── agents/page.tsx          # news sentiment, earnings, portfolio agents
│   │   ├── about/page.tsx
│   │   └── globals.css              # design system (CSS custom properties)
│   ├── components/
│   │   ├── loading/                 # animated loading screen (cold-start UX)
│   │   │   ├── LoadingScreen.tsx    # typewriter facts, catch-the-ticker game, portfolio link
│   │   │   ├── LoadingProvider.tsx  # polls /health, auto-dismisses on connect (90s cap)
│   │   │   └── facts.ts             # 15 verified trading/finance facts
│   │   ├── layout/                  # Sidebar (grouped nav), ThemeProvider
│   │   ├── charts/
│   │   │   └── CandlestickChart.tsx # lightweight-charts OHLC + volume
│   │   └── ui/                      # PageHeader, StatCard, Badge, Spinner, AgentProgress, InsightStrip
│   ├── hooks/
│   │   └── usePriceStream.ts        # WebSocket client with subscription queueing
│   ├── lib/api.ts                   # typed API client
│   └── package.json
├── infra/
│   └── docker-compose.yml           # local Postgres (TimescaleDB) + Redis
├── .github/workflows/
│   ├── ci.yml                       # lint, type-check, test, build
│   └── keep-warm.yml                # /health ping every 10 min — prevents Render idle spin-down
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.13
- Node.js 20
- Docker Desktop
- A free [Groq API key](https://console.groq.com)

### 1. Clone and configure

```bash
git clone https://github.com/CodeRockerr/AEQUITAS.git
cd AEQUITAS
cp .env.example .env   # fill in your values — see Environment Variables below
```

### 2. Start infrastructure (Postgres + Redis)

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

API docs available at `http://localhost:8000/docs`

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at `http://localhost:3000`

### 5. Try it out

```bash
# Search any ticker on the Dashboard — auto-ingests automatically
# Or trigger the agent directly:
curl -X POST "http://localhost:8000/api/v1/agents/research/AAPL"
```

---

## Environment Variables

```bash
# Database — config.py converts to asyncpg and translates managed-Postgres
# SSL params (sslmode/channel_binding) automatically; Neon connection strings
# can be pasted here unchanged.
DATABASE_URL=postgresql://aequitas:aequitas@localhost:5433/aequitas

# Redis — rediss:// (TLS, e.g. Upstash) also supported unchanged
REDIS_URL=redis://localhost:6379

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# LLM (Groq — free tier, no credit card required)
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Finnhub (free tier — news sentiment + earnings agents)
FINNHUB_API_KEY=your_finnhub_key_here

# App
APP_ENV=development
APP_DEBUG=true
```

> `.env` lives in the repo root. `backend/app/config.py` reads it via `env_file=["../.env", ".env"]` and Docker Compose reads it directly.

Frontend needs `NEXT_PUBLIC_API_URL` pointing at your backend (`http://localhost:8000` locally, the Render URL in production). It is a **build-time** variable — changing it on Vercel requires a redeploy.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/health` | Liveness check |
| `WS`   | `/ws/prices` | Real-time price streaming — subscribe/unsubscribe to any ticker |
| `GET`  | `/api/v1/ws/status` | Debug: tickers with active refresh loops |
| `POST` | `/api/v1/market-data/{ticker}/ingest` | Manually ingest OHLCV data from yFinance |
| `GET`  | `/api/v1/market-data/{ticker}/bars` | Retrieve stored price bars |
| `GET`  | `/api/v1/market-data/{ticker}/info` | Company info (name, sector, description, market cap) |
| `GET`  | `/api/v1/history/{ticker}?range_=1mo\|6mo\|1y\|5y\|max` | Full price history, auto-ingests if needed |
| `POST` | `/api/v1/pricing/black-scholes` | Price an option + Greeks |
| `POST` | `/api/v1/risk/var` | Compute VaR/CVaR |
| `POST` | `/api/v1/ml/regime/{ticker}` | HMM regime detection |
| `POST` | `/api/v1/ml/forecast/{ticker}` | XGBoost return forecast + SHAP |
| `GET`  | `/api/v1/signals/{ticker}` | Combined momentum signal |
| `POST` | `/api/v1/signals/pairs/test` | Cointegration test for a pair |
| `POST` | `/api/v1/signals/pairs/signal` | Pairs trading signal (Kalman) |
| `POST` | `/api/v1/backtest/{ticker}/{strategy}` | Run a backtest (`rsi`/`macd`/`bollinger`) |
| `POST` | `/api/v1/factor-model/{ticker}` | Fama-French 3-factor decomposition |
| `POST` | `/api/v1/execution/{ticker}/twap` | TWAP execution schedule |
| `POST` | `/api/v1/execution/{ticker}/vwap` | VWAP execution schedule |
| `POST` | `/api/v1/execution/{ticker}/is` | Implementation Shortfall schedule |
| `POST` | `/api/v1/agents/ingest-filing/{ticker}` | Store a document for RAG |
| `POST` | `/api/v1/agents/research/{ticker}` | Run the full 4-node research agent |
| `POST` | `/api/v1/agents/news-sentiment/{ticker}` | News sentiment agent (Finnhub + Groq) |
| `POST` | `/api/v1/agents/earnings/{ticker}` | Earnings analysis agent (Finnhub + Groq) |
| `POST` | `/api/v1/agents/portfolio` | Portfolio construction agent |
| `GET`  | `/api/v1/benchmark/kernels?rows=N` | Live pandas vs C++20 kernel benchmark |

Full interactive docs: `http://localhost:8000/docs`

---

## Testing

```bash
cd backend
ruff format app tests && ruff check app tests
mypy app
pytest tests/unit/ -v
```

**152 tests passing** across pricing, risk, portfolio optimisation, ML models, signals, pairs trading, Fama-French, TWAP/VWAP/IS execution, backtesting, real-time price streaming, and all agent components.

Coverage threshold: 65% — I/O-heavy paths (live yfinance calls, WebSocket transport) are validated through manual integration testing.

---

## CI/CD

Every push and PR triggers two GitHub Actions jobs:

- **Backend**: Ruff format/lint, Mypy type check, Pytest with coverage
- **Frontend**: ESLint, TypeScript check, `next build`

`main` is protected — both checks must pass before merge.

A third scheduled workflow (`keep-warm.yml`) pings `/health` every 10 minutes, preventing Render idle spin-down and doubling as uptime monitoring.

---

## Roadmap

### Completed
- [x] **Week 1** — Foundation: Docker Compose, FastAPI skeleton, Next.js shell, CI/CD
- [x] **Week 2** — Data pipeline: yFinance ingestion, TimescaleDB hypertables
- [x] **Week 3** — Pricing & Risk: Black-Scholes, Greeks, VaR/CVaR, portfolio optimiser
- [x] **Week 4** — ML models: HMM regime detection, XGBoost forecaster + SHAP
- [x] **Week 5** — Signals & Backtesting: momentum signals, pairs trading + Kalman filter, vectorised backtester
- [x] **Week 6** — Agentic layer: LangGraph 4-node graph, document RAG, Groq LLM, critic revision loop
- [x] **Week 7** — Frontend: full dashboard with dark/light theme, 8 pages, About/landing page
- [x] **Week 8** — Advanced algorithms: Fama-French 3-factor model, TWAP/VWAP/Implementation Shortfall
- [x] **Week 9** — Production deployment: Vercel + Railway (TimescaleDB, Redis), fixed production-only ML bug
- [x] **Week 10** — Real-time layer: WebSocket streaming, auto-ingest, market-closed fallback, candlestick charts, Factors page
- [x] **Week 11** — Advanced agents: news sentiment, earnings analysis, portfolio construction; AgentProgress + InsightStrip UX patterns
- [x] **Week 12** — Infra migration to $0/month: Railway → Render + Neon + Upstash; infrastructure-agnostic migrations, asyncpg SSL translation, scheduled keep-warm workflow
- [x] **Week 13** — C++ acceleration layer: C++20 rolling-window kernels via pybind11 (GIL-released, zero-copy), 1.3x–40x per-kernel speedups, 39.8x end-to-end multi-symbol parallel, CMake/scikit-build-core packaging, live benchmark page; CppCon 2026 poster submission
- [x] **Week 14** — Cold-start UX: animated loading screen with typewriter finance facts, catch-the-ticker mini game, portfolio link, auto-dismiss on API connect (90s cap for Render free tier)

### In Progress / Next
- [ ] **C++ pipeline integration** — full 19-feature `compute_features` C++ backend, expanded benchmark matrix (x86-64, thread/symbol scaling), extension built inside Render deployment
- [ ] **UI/UX design-system pass** — spacing tokens, unified Button variants, framer-motion primitives across all pages

### Planned — Enterprise SaaS Phase
1. **Auth + RBAC** — NextAuth.js, email/password + OAuth, role tiers
2. **Billing** — Stripe subscriptions, usage-based rate limiting
3. **Consumer dashboard** — watchlists, saved thesis history, portfolio tracker with live VaR alerts
4. **Admin panel** — user management, usage metrics, API key issuance
5. **Scale** — rate limiting, Sentry, PostHog

---

## Author

**Adit Shah**
MS Computer Science, NC State University

- GitHub: [@CodeRockerr](https://github.com/CodeRockerr)
- LinkedIn: [@LinkedIn](https://www.linkedin.com/in/shah-adit0404/)
- Portfolio: [@Portfolio](https://adit-2d-portfolio.vercel.app/)
- Resume: [@Resume](https://drive.google.com/file/d/16_bFetVUPBOT01t3aSIqqDIR703DT7Lc/view?usp=sharing)

Built as a deep-dive into production quantitative systems, agentic AI architecture, real-time systems design, full-stack engineering, and native C++ acceleration — with the explicit goal of being both a credible job-application portfolio piece and the seed of a real fintech product.

---

## License

MIT — see [LICENSE](LICENSE) for details.
