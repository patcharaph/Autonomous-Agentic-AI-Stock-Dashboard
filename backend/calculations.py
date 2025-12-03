from typing import Dict

import pandas as pd


def compute_indicators(prices: pd.DataFrame) -> Dict[str, float | dict]:
    """
    Deterministic technical indicator computation (no LLM involvement).
    Returns raw float values to be consumed by downstream agents/critic.
    """
    if prices.empty:
        raise ValueError("Price dataframe is empty.")

    df = prices.copy()
    indicators: Dict[str, float | dict] = {}

    close = df["close"]

    # RSI (Wilder's smoothing)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi_series = 100 - (100 / (1 + rs))
    indicators["rsi_14"] = float(rsi_series.iloc[-1])

    # MACD (12, 26, 9)
    ema_fast = close.ewm(span=12, adjust=False).mean()
    ema_slow = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line
    indicators["macd"] = {
        "macd": float(macd_line.iloc[-1]),
        "signal": float(signal_line.iloc[-1]),
        "histogram": float(macd_hist.iloc[-1]),
    }

    # SMA / EMA
    sma50 = close.rolling(window=50, min_periods=50).mean()
    sma200 = close.rolling(window=200, min_periods=200).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    indicators["sma_50"] = float(sma50.iloc[-1])
    indicators["sma_200"] = float(sma200.iloc[-1])
    indicators["ema_20"] = float(ema20.iloc[-1])

    # Bollinger Bands (20, 2)
    rolling_mean = close.rolling(window=20, min_periods=20).mean()
    rolling_std = close.rolling(window=20, min_periods=20).std(ddof=0)
    upper = rolling_mean + 2 * rolling_std
    lower = rolling_mean - 2 * rolling_std
    bandwidth = (upper - lower) / rolling_mean.replace(0, pd.NA)
    indicators["bollinger_bands"] = {
        "upper": float(upper.iloc[-1]),
        "middle": float(rolling_mean.iloc[-1]),
        "lower": float(lower.iloc[-1]),
        "bandwidth": float(bandwidth.fillna(0).iloc[-1]),
    }

    # Rule-based signals
    indicators["signals"] = {
        "trend": "Uptrend" if indicators["sma_50"] > indicators["sma_200"] else "Downtrend",
        "rsi_state": "Oversold" if indicators["rsi_14"] < 30 else "Overbought" if indicators["rsi_14"] > 70 else "Neutral",
        "macd_cross": "Bullish" if indicators["macd"]["macd"] > indicators["macd"]["signal"] else "Bearish",
    }

    return indicators
