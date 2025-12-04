import pytest
from fastapi.testclient import TestClient

from backend import main


def test_market_history_returns_indicators(monkeypatch, sample_prices):
    def fake_fetch_prices(ticker: str, period: str = "1y", interval: str = "1d"):
        return sample_prices

    monkeypatch.setattr(main, "fetch_prices", fake_fetch_prices)
    client = TestClient(main.app)

    resp = client.get("/api/market/history?ticker=TEST&period=1y&interval=1d")
    assert resp.status_code == 200

    data = resp.json()
    assert data["ticker"] == "TEST"
    assert len(data["candles"]) == len(sample_prices)
    assert "indicators" in data and data["indicators"]["sma50"]
    assert "rsi" in data and len(data["rsi"]) > 0
    assert "macd" in data and len(data["macd"]["macd"]) > 0

    # Ensure overlay values match expected closing price average
    last_sma200 = data["indicators"]["sma200"][-1]["value"]
    assert last_sma200 == pytest.approx(101.0580087672747, rel=1e-6)


def test_analyze_sets_task_and_reports(monkeypatch):
    client = TestClient(main.app)

    resp = client.post("/api/analyze?ticker=TEST")
    assert resp.status_code == 200
    payload = resp.json()
    task_id = payload["task_id"]

    # Simulate background completion
    main.tasks[task_id] = {
        "status": "complete",
        "result": {"draft_report": {"executive_summary": "ok", "technical_indicators": {}}},
    }

    poll = client.get(f"/api/analyze/{task_id}")
    assert poll.status_code == 200
    task = poll.json()
    assert task["status"] == "complete"
    assert task["result"]["draft_report"]["executive_summary"] == "ok"
