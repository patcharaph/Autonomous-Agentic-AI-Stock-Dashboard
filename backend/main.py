import asyncio
import uuid
from typing import Any, Dict, Literal

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.graph import run_workflow
from backend.agents.tools import fetch_news, fetch_prices


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
    return [
        {
            "time": idx.isoformat(),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for idx, row in df.iterrows()
    ]


@app.get("/api/market/history")
def get_history(ticker: str, period: str = "1y", interval: str = "1d"):
    df = fetch_prices(ticker, period=period, interval=interval)
    return {"ticker": ticker, "candles": df_to_ohlcv(df)}


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
