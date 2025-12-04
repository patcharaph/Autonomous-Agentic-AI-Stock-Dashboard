import asyncio
import uuid
from typing import Any, Dict, Literal, Tuple

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.agents.graph import run_workflow
from backend.agents.tools import fetch_news, fetch_prices


# Load environment variables from .env (local dev convenience)
load_dotenv()


app = FastAPI(title="Agentic Stock Dashboard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


TaskStatus = Literal["pending", "running", "complete", "error"]
tasks: Dict[str, Dict[str, Any]] = {}


def df_to_ohlcv(df: pd.DataFrame) -> list[dict[str, Any]]:
    candles: list[dict[str, Any]] = []
    for row in df.itertuples():
        ts = getattr(row, "Index")
        time_str = ts.date().isoformat() if hasattr(ts, "date") else str(ts)
        candles.append(
            {
                "time": time_str,
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": float(row.volume),
            }
        )
    return candles


def indicator_series(df: pd.DataFrame) -> Tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """
    Build lightweight-charts-ready series for SMA/EMA overlays plus RSI & MACD panels.
    Uses min_periods=1 so short timeframes still render lines instead of empty overlays.
    """
    close = df["close"]

    sma50 = close.rolling(window=50, min_periods=1).mean()
    sma200 = close.rolling(window=200, min_periods=1).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi_series = 100 - (100 / (1 + rs))

    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line

    def to_line(series: pd.Series) -> list[dict[str, Any]]:
        return [
            {"time": idx.date().isoformat() if hasattr(idx, "date") else str(idx), "value": float(val)}
            for idx, val in series.dropna().items()
        ]

    overlays = {
        "sma50": to_line(sma50),
        "sma200": to_line(sma200),
        "ema20": to_line(ema20),
    }
    rsi = to_line(rsi_series)
    macd = {
        "macd": to_line(macd_line),
        "signal": to_line(signal_line),
        "histogram": to_line(macd_hist),
    }
    return overlays, rsi, macd


@app.get("/api/market/history")
def get_history(ticker: str, period: str = "1y", interval: str = "1d"):
    df = fetch_prices(ticker, period=period, interval=interval)
    overlays, rsi, macd = indicator_series(df)
    return {
        "ticker": ticker,
        "candles": df_to_ohlcv(df),
        "indicators": overlays,
        "rsi": rsi,
        "macd": macd,
    }


@app.get("/api/market/news")
def get_news(ticker: str, limit: int = 10):
    return {"ticker": ticker, "news": fetch_news(ticker, limit=limit)}


async def _run_task(task_id: str, ticker: str):
    tasks[task_id]["status"] = "running"
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, run_workflow, ticker)
        tasks[task_id]["status"] = "complete"
        tasks[task_id]["result"] = result
    except Exception as exc:
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(exc)


@app.post("/api/analyze")
async def analyze(ticker: str, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "pending"}
    background_tasks.add_task(_run_task, task_id, ticker)
    return {"task_id": task_id, "status": "pending"}


@app.get("/api/analyze/{task_id}")
def get_analysis(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
