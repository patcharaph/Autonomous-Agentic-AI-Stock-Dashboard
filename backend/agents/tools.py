import logging
import time
from typing import Any, List, Literal

import pandas as pd
import requests
import yfinance as yf


logger = logging.getLogger(__name__)


def fetch_prices(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
    max_retries: int = 3,
    backoff: float = 1.0,
) -> pd.DataFrame:
    """
    Robust OHLCV fetcher using yfinance with retry and hard fail semantics.
    Raises on exhausted retries to allow the orchestrator to stop the workflow.
    """
    attempt = 0
    last_exception: Exception | None = None
    while attempt < max_retries:
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False)
            if df is None or df.empty:
                raise ValueError("Received empty price data.")
            df = df.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Adj Close": "adj_close",
                    "Volume": "volume",
                }
            )
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as exc:  # pragma: no cover - logging path
            last_exception = exc
            attempt += 1
            logger.warning("Price fetch failed (attempt %s/%s): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(backoff * attempt)

    # Exceeded retries
    raise RuntimeError(f"Failed to fetch prices for {ticker}: {last_exception}")


def fetch_news(
    ticker: str,
    limit: int = 10,
    provider: Literal["tavily", "newsapi"] | None = "tavily",
    timeout: float = 8.0,
) -> List[dict[str, Any]]:
    """
    Soft-fail news fetcher. Returns [] on network/API errors.
    Supports Tavily (semantic) or NewsAPI/Google-style responses if extended later.
    """
    if provider == "tavily":
        api_key = getenv_default("TAVILY_API_KEY")
        if not api_key:
            logger.info("TAVILY_API_KEY not configured; returning empty news list.")
            return []

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": f"{ticker} stock news",
            "max_results": limit,
        }
    else:
        logger.info("Unknown provider %s; returning empty news list.", provider)
        return []

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        results = data.get("results") or data.get("articles") or []
        # Normalize minimal fields used by UI
        normalized: List[dict[str, Any]] = []
        for item in results:
            normalized.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "published": item.get("published") or item.get("published_at"),
                    "excerpt": item.get("content") or item.get("snippet"),
                    "score": item.get("score") or item.get("relevance_score"),
                }
            )
        return normalized[:limit]
    except Exception as exc:  # pragma: no cover - error path
        logger.warning("News fetch failed for %s: %s", ticker, exc)
        return []


def getenv_default(key: str, default: str | None = None) -> str | None:
    import os

    return os.getenv(key, default)
