"""
AEQUITAS — AI chat endpoint powered by Groq with tool use.

POST /api/v1/chat
Request:  { "messages": [{"role": "user", "content": "..."}] }
Response: { "message": "...", "tools_used": [...] }
"""

import json
from typing import cast

import httpx
from fastapi import APIRouter
from groq import AsyncGroq
from groq.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from pydantic import BaseModel

from app.config import settings

router = APIRouter()
groq_client = AsyncGroq(api_key=settings.groq_api_key)

API_BASE = "http://localhost:8000"

SYSTEM_PROMPT = """You are AEQUITAS Assistant — an AI analyst embedded in the AEQUITAS quantitative research platform.

You have access to real financial data tools. When a user asks about a stock, market, or portfolio:
1. ALWAYS call the relevant tools to get real data — never guess or hallucinate numbers
2. Use multiple tools when needed for a complete picture
3. Synthesize tool results into a clear, concise answer
4. Be honest about uncertainty — if confidence is low, say so
5. Keep answers focused and actionable

You can analyze any valid stock ticker. Common ones: AAPL, MSFT, NVDA, TSLA, SPY, AMZN, META, GOOGL, JPM.
Always ground your answers in tool data. Never make up prices, percentages, or signals.

You get exactly ONE round of tool calls per user message. Once tool results come back, you must
write a final plain-language answer using only those results — never attempt another tool call and
never output text formatted as a function/tool call (no JSON like {"function_name": ...}, no
<function=...> tags). If a tool result shows an error or insufficient data (e.g. "Need N+ bars",
"ingest data first", "insufficient price history"), you cannot fetch more data yourself — just tell
the user plainly that this ticker isn't cached yet and suggest one of the common tickers above."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_signals",
            "description": "Get live RSI, MACD, and Bollinger Band momentum signals for a ticker. Returns combined signal score and direction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol e.g. AAPL",
                    }
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_regime",
            "description": "Get current market regime (Bull/Bear/High Volatility) using HMM detection with confidence level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Get XGBoost ML return forecast with SHAP feature attribution for a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_var",
            "description": "Compute Value at Risk (VaR) and CVaR for a ticker position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "portfolio_value": {
                        "type": "number",
                        "description": "Portfolio value in USD (default 100000)",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_thesis",
            "description": "Run the full 4-node LangGraph research agent to generate a structured investment thesis. Takes 20-30 seconds. Use for comprehensive analysis requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news_sentiment",
            "description": "Get news sentiment analysis using recent headlines. Returns bullish/bearish/neutral sentiment, trend, and key themes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings",
            "description": "Get earnings analysis including next date, beat/miss history, and LLM-synthesized earnings analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_portfolio",
            "description": "Run mean-variance portfolio optimisation and cointegration analysis across tickers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of 2-10 ticker symbols",
                    }
                },
                "required": ["tickers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": "Backtest a trading strategy (rsi/macd/bollinger) on a ticker.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"},
                    "strategy": {
                        "type": "string",
                        "enum": ["rsi", "macd", "bollinger"],
                        "description": "Strategy to backtest",
                    },
                },
                "required": ["ticker", "strategy"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_factor_model",
            "description": "Run Fama-French 3-factor model decomposition. Returns alpha, market beta, SMB and HML exposures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol"}
                },
                "required": ["ticker"],
            },
        },
    },
]


async def _call(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> dict:
    """Make a request and raise with the API's own error detail on failure."""
    r = await client.request(method, url, **kwargs)
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(str(detail))
    return cast(dict, r.json())


async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool call against the real AEQUITAS backend."""
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            if name == "get_signals":
                d = await _call(
                    client, "GET", f"{API_BASE}/api/v1/signals/{args['ticker']}"
                )
                return (
                    f"Signals for {args['ticker']}:\n"
                    f"Direction: {d['direction']} | Score: {d['combined_signal']:.4f}\n"
                    f"RSI: {d['signals']['rsi']['value']:.3f} ({d['signals']['rsi']['note']})\n"
                    f"MACD: {d['signals']['macd']['value']:.3f} ({d['signals']['macd']['note']})\n"
                    f"Bollinger: {d['signals']['bollinger']['value']:.3f} ({d['signals']['bollinger']['note']})"
                )

            elif name == "get_regime":
                d = await _call(
                    client, "POST", f"{API_BASE}/api/v1/ml/regime/{args['ticker']}"
                )
                return (
                    f"Market regime for {args['ticker']}:\n"
                    f"Current: {d['current_regime']} ({d['current_regime_prob']*100:.0f}% confidence)\n"
                    f"Recent: {', '.join(d['regime_sequence'][-10:])}"
                )

            elif name == "get_forecast":
                d = await _call(
                    client, "POST", f"{API_BASE}/api/v1/ml/forecast/{args['ticker']}"
                )
                drivers = ", ".join(
                    f"{x['feature']} ({x['direction']})" for x in d["top_drivers"][:3]
                )
                return (
                    f"ML forecast for {args['ticker']}:\n"
                    f"Predicted: {d['predicted_return_pct']} | Direction: {d['direction']}\n"
                    f"Confidence: {d['confidence']*100:.0f}% | "
                    f"Dir accuracy: {d['model_metrics']['directional_accuracy']}\n"
                    f"Top drivers: {drivers}"
                )

            elif name == "compute_var":
                pv = args.get("portfolio_value", 100000)
                d = await _call(
                    client,
                    "POST",
                    f"{API_BASE}/api/v1/risk/var",
                    json={
                        "ticker": args["ticker"],
                        "portfolio_value": pv,
                        "method": "historical",
                    },
                )
                return (
                    f"Risk for {args['ticker']} (${pv:,.0f}):\n"
                    f"VaR 95%: ${d['var']:,.2f} | CVaR 95%: ${d['cvar']:,.2f}\n"
                    f"{d['interpretation']}"
                )

            elif name == "run_thesis":
                d = await _call(
                    client,
                    "POST",
                    f"{API_BASE}/api/v1/agents/research/{args['ticker']}",
                    timeout=90.0,
                )
                return (
                    f"Thesis for {args['ticker']}:\n"
                    f"Sentiment: {d['thesis_sentiment']} | "
                    f"Confidence: {d['confidence_score']*100:.0f}%\n"
                    f"Regime: {d['current_regime']} | "
                    f"Forecast: {d['predicted_return_pct']}\n\n"
                    f"{d['final_thesis'][:1200]}..."
                )

            elif name == "get_news_sentiment":
                d = await _call(
                    client,
                    "POST",
                    f"{API_BASE}/api/v1/agents/news-sentiment/{args['ticker']}",
                )
                themes = ", ".join(d["key_themes"][:3]) if d["key_themes"] else "none"
                return (
                    f"News sentiment for {args['ticker']}:\n"
                    f"Sentiment: {d['sentiment']} | Score: {d['sentiment_score']:.2f} | "
                    f"Trend: {d['trend']}\n"
                    f"Themes: {themes}\n"
                    f"Summary: {d['summary']}"
                )

            elif name == "get_earnings":
                d = await _call(
                    client,
                    "POST",
                    f"{API_BASE}/api/v1/agents/earnings/{args['ticker']}",
                )
                next_date = d.get("next_earnings_date") or "not scheduled"
                beat = (
                    "Beat"
                    if d.get("last_earnings_beat") is True
                    else "Missed"
                    if d.get("last_earnings_beat") is False
                    else "N/A"
                )
                return (
                    f"Earnings for {args['ticker']}:\n"
                    f"Next: {next_date} | Last: {beat} | "
                    f"Guidance: {d['guidance_sentiment']}\n"
                    f"{d['analysis'][:800]}..."
                )

            elif name == "build_portfolio":
                d = await _call(
                    client,
                    "POST",
                    f"{API_BASE}/api/v1/agents/portfolio",
                    json={"tickers": args["tickers"]},
                    timeout=90.0,
                )
                allocs = "\n".join(
                    f"  {a['ticker']}: {a['max_sharpe_weight']*100:.1f}% Sharpe / "
                    f"{a['min_variance_weight']*100:.1f}% MinVar"
                    for a in d["allocations"]
                )
                pairs = (
                    ", ".join(
                        f"{p['ticker_a']}/{p['ticker_b']}"
                        for p in d["cointegrated_pairs"]
                    )
                    if d["cointegrated_pairs"]
                    else "none"
                )
                return (
                    f"Portfolio ({', '.join(args['tickers'])}):\n"
                    f"Max-Sharpe: {d['max_sharpe_return']*100:.1f}% return, "
                    f"Sharpe {d['max_sharpe_ratio']:.2f}\n"
                    f"Allocations:\n{allocs}\n"
                    f"Cointegrated pairs: {pairs}\n\n"
                    f"{d['thesis'][:600]}..."
                )

            elif name == "run_backtest":
                d = await _call(
                    client,
                    "POST",
                    f"{API_BASE}/api/v1/backtest/{args['ticker']}/{args['strategy']}",
                )
                return (
                    f"Backtest — {args['strategy'].upper()} on {args['ticker']}:\n"
                    f"Return: {d['total_return_pct']:.2f}% | "
                    f"Sharpe: {d['sharpe_ratio']:.2f} | "
                    f"Max DD: {d['max_drawdown_pct']:.2f}%\n"
                    f"Win rate: {d['win_rate_pct']:.1f}% | "
                    f"vs B&H: {d['benchmark_return_pct']:.2f}% | "
                    f"Alpha: {d['alpha_pct']:.2f}%"
                )

            elif name == "get_factor_model":
                d = await _call(
                    client, "POST", f"{API_BASE}/api/v1/factor-model/{args['ticker']}"
                )
                return (
                    f"Fama-French for {args['ticker']}:\n"
                    f"Alpha: {d['alpha_pct']:.2f}%/yr "
                    f"({'significant' if d['alpha_significant'] else 'not significant'}, "
                    f"t={d['alpha_tstat']:.2f})\n"
                    f"Market β: {d['beta_market']:.2f} | "
                    f"SMB: {d['beta_smb']:.2f} | HML: {d['beta_hml']:.2f}\n"
                    f"R²: {d['r_squared']*100:.1f}%\n"
                    f"{d['interpretation']}"
                )

            else:
                return f"Unknown tool: {name}"

        except Exception as e:
            return f"Tool error ({name}): {str(e)}"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    message: str
    tools_used: list[str]


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Groq-powered chat with AEQUITAS tool use."""
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *[{"role": m.role, "content": m.content} for m in req.messages],
    ]

    tools_used: list[str] = []

    # First call — let Groq pick tools
    response = await groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=cast(list[ChatCompletionMessageParam], messages),
        tools=cast(list[ChatCompletionToolParam], TOOLS),
        tool_choice="auto",
        max_tokens=1000,
    )

    assistant_message = response.choices[0].message

    if not assistant_message.tool_calls:
        return ChatResponse(
            message=assistant_message.content or "I couldn't generate a response.",
            tools_used=[],
        )

    # Execute tool calls
    tool_results: list[dict] = []
    for tc in assistant_message.tool_calls:
        tool_args = json.loads(tc.function.arguments)
        tools_used.append(tc.function.name)
        result = await execute_tool(tc.function.name, tool_args)
        tool_results.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            }
        )

    # Second call — synthesize with results
    messages_with_tools: list[dict] = [
        *messages,
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in assistant_message.tool_calls
            ],
        },
        *tool_results,
    ]

    final = await groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=cast(list[ChatCompletionMessageParam], messages_with_tools),
        max_tokens=1500,
    )

    return ChatResponse(
        message=final.choices[0].message.content or "No response generated.",
        tools_used=tools_used,
    )
