# AEQUITAS

**Agentic Equity & Quantitative Intelligence Trading Analysis System**

A full-stack quantitative research platform combining real financial algorithms, ML models, and an autonomous LLM agent pipeline to generate institutional-grade investment theses — automatically.

[![CI](https://github.com/CodeRockerr/AEQUITAS/actions/workflows/ci.yml/badge.svg)](https://github.com/CodeRockerr/AEQUITAS/actions)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Node](https://img.shields.io/badge/Node-20-green)
![Tests](https://img.shields.io/badge/tests-120%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What is this?

AEQUITAS is a personal research platform built to be both a serious portfolio project and the foundation of a real quant/fintech SaaS product. It ingests live market data, runs a battery of quantitative finance algorithms and ML models, then hands the results to a multi-agent LLM pipeline that researches a company, evaluates the data, and writes a structured investment thesis — citing sources and critiquing its own conclusions before presenting them.

Everything in this repo is real, working, and tested. No mocked endpoints, no placeholder data once a ticker is ingested.

**Live demo:** _(add Vercel URL here once deployed)_
**API docs:** _(add Railway URL + `/docs` once deployed)_

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Algorithms & Models](#algorithms--models)
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
    subgraph Frontend["Frontend — Next.js 14, TypeScript, Recharts"]
        direction LR
        F1["Overview"] --- F2["Dashboard"] --- F3["Backtests"] --- F4["Theses"] --- F5["Risk"] --- F6["About"]
    end

    subgraph API["API Layer — FastAPI, Pydantic v2, SQLAlchemy async"]
        direction LR
        A1["health"] --- A2["market-data"] --- A3["pricing-risk"] --- A4["ml"] --- A5["signals"] --- A6["agents"]
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

    subgraph Agent["Agent Layer"]
        direction TB
        AG1["LangGraph 4-node graph:<br/>research → quant → thesis_gen → critic"]
        AG2["Groq LLM<br/>llama-3.3-70b-versatile"]
    end

    subgraph Data["Data Layer"]
        direction TB
        D1["yFinance ingestion"]
        D2["TimescaleDB hypertables"]
        D3["pgvector RAG over SEC filings"]
    end

    subgraph Storage["Storage"]
        direction LR
        S1[("PostgreSQL /<br/>TimescaleDB +<br/>pgvector")]
        S2[("Redis")]
    end

    Frontend -->|"REST — typed client in lib/api.ts"| API
    API --> Algo
    API --> Agent
    API --> Data
    Algo --> Storage
    Agent --> Storage
    Data --> Storage
```


---

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts |
| **Backend** | FastAPI, Python 3.13, Pydantic v2, SQLAlchemy 2.0 (async) |
| **Database** | PostgreSQL + TimescaleDB (hypertables), pgvector (RAG) |
| **Cache/Queue** | Redis |
| **Agent Orchestration** | LangGraph 0.2 |
| **LLM** | Groq API — `llama-3.3-70b-versatile` (free tier) |
| **ML** | XGBoost, SHAP, hmmlearn, scikit-learn, statsmodels |
| **Migrations** | Alembic |
| **CI/CD** | GitHub Actions (backend + frontend jobs, branch protection) |
| **Linting** | Ruff (backend), ESLint (frontend) |
| **Type Checking** | Mypy (backend), TypeScript strict (frontend) |
| **Testing** | Pytest + pytest-asyncio (97 tests) |
| **Deployment (planned)** | Vercel (frontend) + Railway (backend/DB/Redis) |

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

### Signals
- **Momentum signals**: RSI, MACD, Bollinger Bands — each normalised to `[-1, +1]` and combinable into a single weighted score
- **Pairs trading**: Engle-Granger cointegration test + **Kalman filter** for dynamic hedge ratio estimation (more realistic than static OLS)
- **Fama-French 3-factor model**: decomposes returns into Market, SMB (size), and HML (value) factor exposures. Reports alpha with a t-statistic, so you can tell skill from beta exposure.

### Execution Algorithms
- **TWAP** (Time-Weighted Average Price) — splits an order equally across time intervals
- **VWAP** (Volume-Weighted Average Price) — distributes shares proportional to a U-shaped intraday volume profile, matching real market microstructure
- **Implementation Shortfall** — urgency-parameterised schedule that trades off market impact against timing risk; includes post-trade execution quality analysis (IS in basis points vs decision price)

### Backtesting
- Vectorised backtesting engine (no Python loops over time — pure numpy/pandas operations)
- Full tearsheet: Sharpe, Sortino, Calmar ratios, max drawdown, win rate, alpha vs buy-and-hold benchmark

---

## The Agentic Pipeline

AEQUITAS's signature feature is a 4-node LangGraph agent that autonomously produces investment research:

```mermaid
flowchart TD
    START(["START"]) --> research

    research["<b>research</b><br/>Retrieves company info + SEC filing<br/>chunks via pgvector full-text search.<br/>Summarises via LLM."]
    research --> quant

    quant["<b>quant</b><br/>Computes live regime (HMM), momentum<br/>signal, XGBoost forecast + SHAP, and<br/>VaR — using the real algorithm layer,<br/>not mocked data."]
    quant --> thesis_gen

    thesis_gen["<b>thesis_gen</b><br/>LLM synthesises a structured thesis:<br/>Overview, Bull Case, Bear Case, Quant<br/>Evidence, Risk Factors, Verdict —<br/>citing the research above."]
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

This isn't a single prompt to an LLM — it's a stateful graph where each node does real computational work, and the critic node has caught genuine issues in testing (e.g. flagging a bullish verdict that contradicted bearish quant signals).


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
│   │   │   ├── signals/             # momentum, pairs trading, Fama-French factor model
│   │   │   ├── execution/           # TWAP, VWAP, Implementation Shortfall
│   │   │   └── backtesting/         # vectorised backtest engine
│   │   ├── api/v1/                  # FastAPI routers
│   │   │   ├── health.py
│   │   │   ├── market_data.py
│   │   │   ├── pricing.py
│   │   │   ├── ml.py
│   │   │   ├── signals.py
│   │   │   ├── agents.py
│   │   │   └── advanced.py          # factor model + execution endpoints
│   │   ├── data/
│   │   │   └── vector/store.py      # pgvector document store for RAG
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── tasks/                   # background/Celery tasks
│   │   ├── config.py                # pydantic-settings configuration
│   │   ├── db.py                    # async engine + session factory
│   │   └── main.py                  # FastAPI app factory
│   ├── alembic/versions/            # database migrations
│   ├── tests/unit/                  # 97 pytest tests
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Overview / landing
│   │   ├── dashboard/page.tsx       # live signals, regime, SHAP
│   │   ├── backtests/page.tsx       # strategy runner + equity curve
│   │   ├── theses/page.tsx          # agent thesis generator
│   │   ├── risk/page.tsx            # VaR/CVaR + options pricer
│   │   ├── about/page.tsx           # marketing/about page
│   │   └── globals.css              # design system (CSS custom properties)
│   ├── components/
│   │   ├── layout/                  # Sidebar, ThemeProvider
│   │   └── ui/                      # PageHeader, StatCard, Badge, Spinner
│   ├── lib/api.ts                   # typed API client
│   └── package.json
├── infra/
│   └── docker-compose.yml
├── .github/workflows/ci.yml
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
cp .env.example .env   # then fill in your values, see below
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

### 5. Ingest some data and try the agent

```bash
curl -X POST "http://localhost:8000/api/v1/market-data/AAPL/ingest?period=1y&interval=1d"
curl -X POST "http://localhost:8000/api/v1/agents/research/AAPL"
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://aequitas:aequitas@localhost:5433/aequitas

# Redis
REDIS_URL=redis://localhost:6379

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# LLM (Groq — free tier, no credit card required)
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# App
APP_ENV=development
APP_DEBUG=true
```

> **Note on `.env` location**: place this file in the repo root. Both `backend/app/config.py` (via `env_file=["../.env", ".env"]`) and Docker Compose read from here.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/health` | Liveness check |
| `POST` | `/api/v1/market-data/{ticker}/ingest` | Ingest OHLCV data from yFinance |
| `GET`  | `/api/v1/market-data/{ticker}/bars` | Retrieve stored price bars |
| `POST` | `/api/v1/pricing/black-scholes` | Price an option + Greeks |
| `POST` | `/api/v1/risk/var` | Compute VaR/CVaR |
| `POST` | `/api/v1/ml/regime/{ticker}` | HMM regime detection |
| `POST` | `/api/v1/ml/forecast/{ticker}` | XGBoost return forecast + SHAP |
| `GET`  | `/api/v1/signals/{ticker}` | Combined momentum signal |
| `POST` | `/api/v1/signals/pairs/test` | Cointegration test for a pair |
| `POST` | `/api/v1/signals/pairs/signal` | Pairs trading signal (Kalman) |
| `POST` | `/api/v1/backtest/{ticker}/{strategy}` | Run a backtest (`rsi`/`macd`/`bollinger`) |
| `POST` | `/api/v1/agents/ingest-filing/{ticker}` | Store a document for RAG |
| `POST` | `/api/v1/agents/research/{ticker}` | Run the full 4-node research agent |
| `POST` | `/api/v1/factor-model/{ticker}` | Fama-French 3-factor decomposition (alpha, beta, SMB, HML) |
| `POST` | `/api/v1/execution/{ticker}/twap` | TWAP execution schedule |
| `POST` | `/api/v1/execution/{ticker}/vwap` | VWAP execution schedule (U-shaped volume profile) |
| `POST` | `/api/v1/execution/{ticker}/is` | Implementation Shortfall schedule (urgency-parameterised) |

Full interactive documentation: `http://localhost:8000/docs`

---

## Testing

```bash
cd backend
ruff format app tests && ruff check app tests
mypy app
pytest tests/unit/ -v
```

**~120 tests passing** across pricing, risk, portfolio optimisation, ML models, signals, pairs trading, Fama-French factor model, TWAP/VWAP/Implementation Shortfall execution algorithms, backtesting, and agent components.

---

## CI/CD

Every push and PR triggers two GitHub Actions jobs:

- **Backend**: Ruff format/lint, Mypy type check, Pytest with coverage
- **Frontend**: ESLint, TypeScript check, `next build`

`main` is protected — both checks must pass before merge.

---

## Roadmap

AEQUITAS started as an 8-week portfolio project but is being extended into a full enterprise-grade SaaS platform. Build order matters here — each phase depends on the previous one.

### Completed
- [x] **Week 1** — Foundation: Docker Compose, FastAPI skeleton, Next.js shell, CI/CD
- [x] **Week 2** — Data pipeline: yFinance ingestion, TimescaleDB hypertables
- [x] **Week 3** — Pricing & Risk: Black-Scholes, Greeks, VaR/CVaR, portfolio optimiser
- [x] **Week 4** — ML models: HMM regime detection, XGBoost forecaster + SHAP
- [x] **Week 5** — Signals & Backtesting: momentum signals, pairs trading + Kalman filter, vectorised backtester
- [x] **Week 6** — Agentic layer: LangGraph 4-node graph, pgvector RAG, Groq LLM, critic revision loop
- [x] **Week 7** — Frontend: full dashboard with dark/light theme, 6 pages, About/landing page
- [x] **Week 8** — Advanced algorithms: Fama-French 3-factor model, TWAP/VWAP/Implementation Shortfall execution algorithms

### In Progress / Next
- [ ] **Deploy** — Vercel (frontend) + Railway (backend/DB/Redis), get a live public URL
- [ ] **Advanced agents** — Earnings call analysis agent, news sentiment agent, portfolio construction agent

### Planned — Enterprise SaaS Phase
The long-term vision is a full multi-tenant SaaS product, not just a demo. Target users: retail traders, professional quants, and institutions. Build order is a strict dependency chain:

1. **Auth + RBAC** — NextAuth.js, email/password + OAuth, Free/Pro/Admin roles. Everything below depends on this.
2. **Billing** — Stripe subscriptions, usage-based rate limiting per plan tier
3. **Consumer dashboard** — personalised watchlists, saved thesis history, portfolio tracker with live VaR alerts
4. **Admin panel** — user management, usage metrics, revenue dashboard, API key issuance
5. **API access** — programmatic API keys for quant/institutional users with usage-based pricing
6. **Scale** — rate limiting, caching layer, error monitoring (Sentry), product analytics (PostHog)

---

## Author

**Adit Shah**
MS Computer Science, NC State University (GPA 3.80)
AI-Assisted Learning Lab — Graduate Researcher

- GitHub: [@GitHub](https://github.com/CodeRockerr)
- LinkedIn: [@LinkedIn](https://www.linkedin.com/in/shah-adit0404/)
- Portfolio: [@Portfolio](https://adit-2d-portfolio.vercel.app/)
- Resume: [@Resume](https://drive.google.com/file/d/16_bFetVUPBOT01t3aSIqqDIR703DT7Lc/view?usp=sharing)

Built as a deep-dive into production quantitative systems, agentic AI architecture, and full-stack engineering — with the explicit goal of being both a credible job-application portfolio piece and the seed of a real fintech product.

---

## License

MIT — see [LICENSE](LICENSE) for details.
