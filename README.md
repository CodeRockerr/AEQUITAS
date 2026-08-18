# AEQUITAS

**Agentic Equity & Quantitative Intelligence Trading Analysis System**

A full-stack quantitative research platform combining real financial algorithms, ML models, real-time price streaming, autonomous LLM agents, and an AI chat interface - all running at $0/month in production.

[![CI](https://github.com/CodeRockerr/AEQUITAS/actions/workflows/ci.yml/badge.svg)](https://github.com/CodeRockerr/AEQUITAS/actions)
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Node](https://img.shields.io/badge/Node-20-green)
![Tests](https://img.shields.io/badge/tests-152%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## What is this?

AEQUITAS is a personal research platform built to be both a serious portfolio project and the foundation of a real quant/fintech SaaS product. It streams live market data, runs a battery of quantitative finance algorithms and ML models, hands the results to a multi-agent LLM pipeline that researches a company and writes a structured investment thesis - and now includes a floating AI chat widget where users can ask anything about any stock in plain English and get answers grounded in real algorithm output.

Everything in this repo is real, working, and tested. No mocked endpoints, no placeholder data.

**Live demo:** [aequitas-three.vercel.app](https://aequitas-three.vercel.app)
**API docs:** [aequitas-api.onrender.com/docs](https://aequitas-api.onrender.com/docs)

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Algorithms & Models](#algorithms--models)
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
        F1["Overview"] --- F2["Dashboard"] --- F3["Backtests"] --- F4["Theses"] --- F5["Risk"] --- F6["Factors"] --- F7["Agents"] --- F8["Chat ◈"]
    end

    subgraph API["API Layer - FastAPI, Pydantic v2, SQLAlchemy async, WebSocket"]
        direction LR
        A1["health"] --- A2["market-data"] --- A3["ml"] --- A4["signals"] --- A5["agents"] --- A6["history"] --- A7["ws/prices"] --- A8["chat"]
    end

    subgraph Algo["Algorithm Layer"]
        AL1["Pricing & Risk · Portfolio · ML · Signals · Factor Model · Execution · Backtesting"]
    end

    subgraph Stream["Real-Time Layer"]
        ST1["Subscriber-tracked WebSocket · Auto-ingest · Market-closed fallback"]
    end

    subgraph Agent["Agent Layer"]
        AG1["LangGraph 4-node graph + News Sentiment + Earnings + Portfolio Construction"]
        AG2["Groq LLM - llama-3.3-70b-versatile (free tier)"]
    end

    subgraph Chat["AI Chat"]
        CH1["Groq tool_use - 10 tools → real AEQUITAS endpoints"]
    end

    subgraph Storage["Storage"]
        S1[("Neon - Postgres 16")]
        S2[("Upstash - Redis")]
    end

    Frontend -->|"REST + WebSocket"| API
    API --> Algo & Stream & Agent & Chat
    Algo & Stream & Agent & Chat --> Storage
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
| **LLM** | Groq API - `llama-3.3-70b-versatile` (free tier, used for agents + chat widget) |
| **ML** | XGBoost, SHAP, hmmlearn, scikit-learn, statsmodels |
| **Native Extensions** | C++20 feature kernels via pybind11 (zero-copy NumPy, GIL-released) |
| **Migrations** | Alembic (infrastructure-agnostic) |
| **CI/CD** | GitHub Actions (lint + type-check + test + build + keep-warm) |
| **Testing** | Pytest + pytest-asyncio (152 tests) |

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

### C++ Feature Kernels *(CppCon 2026 poster - accepted)*
- Rolling mean/std/max/min, EWM (span + Wilder), RSI, ATR reimplemented in **C++20** via **pybind11**
- Zero-copy NumPy buffer exchange, GIL released around every compute loop
- **1.3×–40× per-kernel** · **39.8× end-to-end** on multi-symbol parallel workloads (8 × 1M rows)
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

## AI Chat Widget

Every page has a floating **◈** button (bottom-right) that opens an AI chat panel. Powered by **Groq's free tier** with tool use - the model calls your real AEQUITAS endpoints to answer questions with actual data, never hallucinated numbers.

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

Plus three standalone agents: **news sentiment**, **earnings analysis**, **portfolio construction** - all on the Agents page with step-by-step progress indicators and Observed → Why it matters → Next action insight strips.

---

## Directory Structure

```
AEQUITAS/
├── backend/
│   ├── app/
│   │   ├── agents/                  # LangGraph + news/earnings/portfolio agents
│   │   ├── algorithms/              # pricing, risk, portfolio, ml, signals, execution, backtesting
│   │   ├── services/
│   │   │   └── price_stream.py      # WebSocket subscriber manager
│   │   └── api/v1/
│   │       ├── chat.py              # Groq chat endpoint with 10 AEQUITAS tools
│   │       ├── extended_agents.py   # news sentiment, earnings, portfolio endpoints
│   │       ├── history.py           # full price history with auto-ingest
│   │       ├── websocket.py         # /ws/prices
│   │       └── ...                  # health, market_data, pricing, ml, signals, advanced
│   ├── cpp/                         # C++20 kernels (pybind11, CMake, scikit-build-core)
│   ├── alembic/versions/            # infrastructure-agnostic migrations
│   ├── tests/unit/                  # 152 pytest tests
│   └── pyproject.toml
├── frontend/
│   ├── app/                         # 8 pages: Overview, Dashboard, Backtests, Theses, Risk, Factors, Agents, About
│   ├── components/
│   │   ├── chat/
│   │   │   └── ChatWidget.tsx       # floating AI chat widget
│   │   ├── loading/                 # animated loading screen (cold-start UX)
│   │   ├── layout/                  # Sidebar (grouped nav), ThemeProvider
│   │   ├── charts/
│   │   │   └── CandlestickChart.tsx # lightweight-charts OHLC + volume
│   │   └── ui/                      # PageHeader, StatCard, Badge, Spinner, AgentProgress, InsightStrip
│   ├── hooks/
│   │   └── usePriceStream.ts        # WebSocket client with subscription queueing
│   └── lib/api.ts                   # typed API client
├── infra/
│   └── docker-compose.yml
├── .github/workflows/
│   ├── ci.yml                       # lint, type-check, test, build
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
GROQ_MODEL=llama-3.3-70b-versatile
FINNHUB_API_KEY=your_finnhub_key_here
APP_ENV=development
APP_DEBUG=true
API_BASE_URL=http://localhost:8000   # set to Render URL in production
```

Frontend: `NEXT_PUBLIC_API_URL` (build-time variable - changing on Vercel requires redeploy).

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
| `POST` | `/api/v1/agents/news-sentiment/{ticker}` | News sentiment agent |
| `POST` | `/api/v1/agents/earnings/{ticker}` | Earnings analysis agent |
| `POST` | `/api/v1/agents/portfolio` | Portfolio construction agent |
| `GET`  | `/api/v1/benchmark/kernels` | Live C++ vs pandas benchmark |

Full interactive docs: `http://localhost:8000/docs`

---

## Testing

```bash
cd backend
ruff format app tests && ruff check app tests
mypy app
pytest tests/unit/ -v
```

**152 tests passing.** Coverage threshold: 65%.

---

## CI/CD

- **CI** (`ci.yml`): Ruff, Mypy, Pytest (backend) + ESLint, tsc, build (frontend) on every push and PR
- **Keep-warm** (`keep-warm.yml`): pings `/health` every 10 minutes - prevents Render idle spin-down, doubles as uptime monitoring
- Branch protection on `main` - both jobs must pass before merge

---

## Roadmap

### Completed
- [x] **Week 1-8** - Foundation, data pipeline, algorithms (Black-Scholes, VaR, portfolio, HMM, XGBoost, signals, backtesting)
- [x] **Week 9** - Production deployment (originally Railway, migrated to Render + Neon + Upstash)
- [x] **Week 10** - Real-time WebSocket streaming, auto-ingest, candlestick charts, Factors page
- [x] **Week 11** - 3 additional agents (news sentiment, earnings, portfolio construction); AgentProgress + InsightStrip UX
- [x] **Week 12** - Infrastructure migration to $0/month stack; keep-warm workflow
- [x] **Week 13** - C++20 acceleration layer; CppCon 2026 poster accepted
- [x] **Week 14** - Animated loading screen with mini game and portfolio link
- [x] **Week 15** - Groq-powered AI chat widget with 10 AEQUITAS tools

### In Progress / Next
- [ ] **MCP server** - Claude.ai compatible MCP endpoint so users can connect AEQUITAS as an integration in Claude.ai
- [ ] **C++ pipeline integration** - full `compute_features()` C++ backend, Render build
- [ ] **UI/UX design-system pass** - spacing tokens, unified Button, framer-motion across all pages

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
