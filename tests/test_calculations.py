import pytest

from backend.calculations import compute_indicators


def test_compute_indicators_expected_values(sample_prices):
    indicators = compute_indicators(sample_prices)

    assert indicators["signals"]["trend"] == "Downtrend"
    assert indicators["signals"]["rsi_state"] == "Overbought"
    assert indicators["signals"]["macd_cross"] == "Bullish"

    assert indicators["sma_50"] == pytest.approx(98.80665407239309, rel=1e-6)
    assert indicators["sma_200"] == pytest.approx(101.0580087672747, rel=1e-6)
    assert indicators["ema_20"] == pytest.approx(98.12882667433976, rel=1e-6)
    assert indicators["rsi_14"] == pytest.approx(75.25181892478082, rel=1e-6)

    macd = indicators["macd"]
    assert macd["macd"] == pytest.approx(0.10522781432237593, rel=1e-6)
    assert macd["signal"] == pytest.approx(-0.2480240583127879, rel=1e-6)
    assert macd["histogram"] == pytest.approx(0.35325187263516383, rel=1e-6)

    bb = indicators["bollinger_bands"]
    assert bb["upper"] == pytest.approx(99.22430998302828, rel=1e-6)
    assert bb["middle"] == pytest.approx(97.632585192431, rel=1e-6)
    assert bb["lower"] == pytest.approx(96.04086040183371, rel=1e-6)
