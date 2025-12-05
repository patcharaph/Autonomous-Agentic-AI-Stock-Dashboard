# Autonomous Agentic AI Stock Dashboard
![tests](https://img.shields.io/badge/tests-pytest-%234C1.svg)

This project delivers a TradingView-style dashboard backed by a LangGraph multi-agent workflow (Researcher → Analyst → Writer → Critic) with FastAPI and a Next.js 14 frontend. Philosophy: deterministic math in Python; LLM only for reasoning and Thai-language reporting.

## Stack
- Frontend: Next.js 14 (App Router), TypeScript, Tailwind CSS, lightweight-charts
- Backend: FastAPI, LangGraph for state workflow, pandas/yfinance for deterministic TA
- DB (planned): PostgreSQL + TimescaleDB for time-series (hooks ready to attach)
- LLM: GPT-4o (default, configurable), Claude 3.5 Sonnet compatible

## Key Files
- `backend/agents/graph.py` — LangGraph pipeline (Researcher, Analyst, Writer, Critic, retry guard)
- `backend/agents/tools.py` — robust OHLCV + news fetchers (hard fail for prices, soft fail for news)
- `backend/calculations.py` — pure Python technical indicators (RSI, MACD, SMA50/200, EMA20, Bollinger)
- `backend/main.py` — FastAPI endpoints: history, news, analyze trigger/poll
- `frontend/components/Chart.tsx` — lightweight-charts candlestick with overlays and sub-panels
- `frontend/app/page.tsx` — dashboard shell (ticker search, timeframe, analyze trigger, news, AI insight)

## Running (dev)
1) Backend (Python 3.11+):
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```
If `pip install -r backend/requirements.txt` fails on Windows, first upgrade pip:
```bash
python -m pip install --upgrade pip
```
Then rerun `pip install -r backend/requirements.txt`.
Set `OPENROUTER_API_KEY` (and `TAVILY_API_KEY` for news) in your environment.

2) Frontend (Node 18+):
```bash
cd frontend
npm install
npm run dev
```
Configure the frontend to call `http://localhost:8000` or proxy via `NEXT_PUBLIC_API_BASE`.

## Configuration
Set env vars (or use `.env`):
```
OPENROUTER_API_KEY=sk-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_REFERRER=http://localhost
OPENROUTER_APP_NAME=Agentic Stock Dashboard
TAVILY_API_KEY=tvly-...
REPORT_MODEL=gpt-4o
NEWS_SUMMARY_MODEL=gpt-4o-mini
NEXT_PUBLIC_API_BASE=http://localhost:8000
# Or use OpenAI directly (leave the OpenRouter vars unset)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
```
Optional DB hook (placeholder for future persistence): `POSTGRES_URL=postgresql://user:password@localhost:5432/agentic_db`.

If you see `401 User not found`, it usually means an OpenAI key is being sent to the OpenRouter endpoint; clear the `OPENROUTER_*` vars or supply a valid OpenRouter key.

## API
- `GET /api/market/history?ticker=AAPL&period=1y&interval=1d` → OHLCV for charts
- `GET /api/market/news?ticker=AAPL` → soft-fail news list
- `POST /api/analyze?ticker=AAPL` → starts agent task, returns `task_id`
- `GET /api/analyze/{task_id}` → task status + final JSON report

## System Flow (Mermaid)
```mermaid
graph TD
    %% Nodes
    Start((Start)) --> Researcher[Node A: Researcher]
    Researcher -->|Raw Data| Analyst[Node B: Analyst]
    Analyst -->|Math & Signals| Writer[Node C: Writer]
    
    Writer -->|JSON Draft| Critic[Node D: Critic]
    
    Critic --> Check{Pass Quality?}
    
    Check -- "❌ NO (Hallucination/Error)" --> Writer
    Check -- "✅ YES" --> End([🏁 Final Output])
    
    %% Styles
    style Analyst fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    style Critic fill:#ffcdd2,stroke:#c62828,stroke-width:2px
    style End fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
```

## Notes
- Researcher retries prices (3x) then fails; news failures return `[]` so the pipeline never crashes.
- Critic enforces JSON + numeric parity with computed indicators; after 2 failed revisions it publishes with `Low` confidence to avoid infinite loops.
- Frontend renders the AI report in Thai with exact technical values; export-to-PDF/Markdown can be added by wiring the JSON to your preferred exporter.

## Testing
- Unit: `pytest` (or `tox -e py310`) — covers indicator math (RSI, MACD, SMA50/200, EMA20, Bollinger) and FastAPI endpoints with mocked dependencies.
- Dev deps: `pip install -r backend/requirements-dev.txt`.

## Docker / Compose
- Backend: `Dockerfile.backend` (FastAPI + uvicorn)
- Frontend: `Dockerfile.frontend` (Next.js build + start)
- One-shot: `docker-compose up --build` (frontend on `:3000`, backend on `:8000`, optional Postgres on `:5432`).

## Screenshots
Add a dashboard capture (e.g., `docs/screenshot.png`) showing candlesticks + overlays + Thai analysis to make the repo presentation-ready.

## Architecture Overview
- Frontend (Next.js) ↔ Backend (FastAPI) ↔ LLM (OpenRouter/OpenAI) ↔ Market Data (yfinance) ↔ News (Tavily).
- Agents: Researcher (data), Analyst (math), Writer (Thai narrative), Critic (structure/consistency).

## Agent Nodes (4-step workflow)
- **Node 1: Researcher (`researcher_node`)** — pulls market data and news via `fetch_prices` and `fetch_news`, drops both into the shared state as `raw_prices` and `news_data`.
- **Node 2: Analyst (`analyst_node`)** — deterministic math only; calls `compute_indicators` (pandas-based RSI, MACD, SMA50/200, EMA20, Bollinger, simple signals) and stores results in `technical_indicators`.
- **Node 3: Writer (`writer_node`)** — LLM (default GPT-4o) crafts a Thai report from the indicators + news, forcing JSON output and injecting the exact numeric payload; loops with critic feedback if present.
- **Node 4: Critic (`critic_node`)** — checks JSON completeness and exact indicator parity; if mismatched, adds feedback and triggers up to two rewrites, otherwise marks confidence High and ends the graph.

## Disclaimer
This dashboard is for educational/research purposes only and is **not** financial advice. Use at your own risk. 
