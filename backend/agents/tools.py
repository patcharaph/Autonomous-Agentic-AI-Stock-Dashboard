import logging
import time
import json
from typing import Any, List, Literal

import pandas as pd
import requests
import yfinance as yf
from openai import OpenAI


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
            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
            if df is None or df.empty:
                raise ValueError("Received empty price data.")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(level=1)
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


def build_llm_client() -> OpenAI:
    """
    Build an OpenAI client that prefers OpenRouter when configured; otherwise fall back to OpenAI.
    Mirrors the Writer node setup so auth errors are consistent.
    """
    openrouter_key = getenv_default("OPENROUTER_API_KEY")
    openai_key = getenv_default("OPENAI_API_KEY")
    if openrouter_key:
        default_headers = {
            "HTTP-Referer": getenv_default("OPENROUTER_REFERRER", "http://localhost"),
            "X-Title": getenv_default("OPENROUTER_APP_NAME", "Agentic Stock Dashboard"),
        }
        return OpenAI(
            api_key=openrouter_key,
            base_url=getenv_default("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_headers=default_headers,
        )
    if openai_key:
        base_url = getenv_default("OPENAI_BASE_URL")
        if base_url:
            return OpenAI(api_key=openai_key, base_url=base_url)
        return OpenAI(api_key=openai_key)
    raise RuntimeError("Missing LLM credentials: set OPENROUTER_API_KEY or OPENAI_API_KEY.")


def summarize_news_items(
    items: List[dict[str, Any]],
    model: str | None = None,
) -> tuple[List[dict[str, Any]], str | None]:
    """
    Summarize news list with a single LLM call. Soft-fails: returns originals if LLM is unavailable.
    Returns (news_with_summaries, overall_summary).
    """
    if not items:
        return items, None

    chosen_model = model or getenv_default("NEWS_SUMMARY_MODEL") or getenv_default("REPORT_MODEL") or "gpt-4o-mini"
    try:
        client = build_llm_client()
    except Exception as exc:  # pragma: no cover - auth issues
        logger.warning("LLM client unavailable for news summarization: %s", exc)
        return items, None

    payload = [
        {
            "title": item.get("title") or "",
            "excerpt": item.get("excerpt") or "",
            "score": item.get("score"),
        }
        for item in items
    ]
    messages = [
        {
            "role": "system",
            "content": "You are a financial news summarizer. Return JSON only.",
        },
        {
            "role": "user",
            "content": (
                "Summarize each item into one concise Thai sentence (keep tickers/company names in English). "
                "Also provide one overall market take in Thai. "
                "Input:\n"
                f"{json.dumps(payload, ensure_ascii=False)}\n\n"
                "Output JSON shape:\n"
                '{"per_item": ["..."], "overall": "..."}'
            ),
        },
    ]
    try:
        response = client.chat.completions.create(
            model=chosen_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        per_item = data.get("per_item") or []
        overall = data.get("overall")
        for item, summary in zip(items, per_item):
            item["summary"] = summary
        return items, overall
    except Exception as exc:  # pragma: no cover - LLM path
        logger.warning("News summarization failed: %s", exc)
        return items, None


def getenv_default(key: str, default: str | None = None) -> str | None:
    import os

    return os.getenv(key, default)
