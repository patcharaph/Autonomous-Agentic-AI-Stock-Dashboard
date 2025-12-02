from typing import Dict

import pandas as pd
import pandas_ta as ta


def compute_indicators(prices: pd.DataFrame) -> Dict[str, float | dict]:
    """
    Deterministic technical indicator computation (no LLM involvement).
    Returns raw float values to be consumed by downstream agents/critic.
    """
    if prices.empty:
        raise ValueError("Price dataframe is empty.")

    df = prices.copy()
    indicators: Dict[str, float | dict] = {}

    # RSI
    rsi_series = ta.rsi(df["close"], length=14)
    indicators["rsi_14"] = float(rsi_series.iloc[-1])

    # MACD
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    indicators["macd"] = {
        "macd": float(macd["MACD_12_26_9"].iloc[-1]),
        "signal": float(macd["MACDs_12_26_9"].iloc[-1]),
        "histogram": float(macd["MACDh_12_26_9"].iloc[-1]),
    }

    # SMA / EMA
    sma50 = ta.sma(df["close"], length=50)
    sma200 = ta.sma(df["close"], length=200)
    ema20 = ta.ema(df["close"], length=20)
    indicators["sma_50"] = float(sma50.iloc[-1])
    indicators["sma_200"] = float(sma200.iloc[-1])
    indicators["ema_20"] = float(ema20.iloc[-1])

    # Bollinger Bands
    bb = ta.bbands(df["close"], length=20, std=2)
    indicators["bollinger_bands"] = {
        "upper": float(bb["BBU_20_2.0"].iloc[-1]),
        "middle": float(bb["BBM_20_2.0"].iloc[-1]),
        "lower": float(bb["BBL_20_2.0"].iloc[-1]),
        "bandwidth": float(bb["BBB_20_2.0"].iloc[-1]),
    }

    # Rule-based signals
    indicators["signals"] = {
        "trend": "Uptrend" if indicators["sma_50"] > indicators["sma_200"] else "Downtrend",
        "rsi_state": "Oversold" if indicators["rsi_14"] < 30 else "Overbought" if indicators["rsi_14"] > 70 else "Neutral",
        "macd_cross": "Bullish" if indicators["macd"]["macd"] > indicators["macd"]["signal"] else "Bearish",
    }

    return indicators
