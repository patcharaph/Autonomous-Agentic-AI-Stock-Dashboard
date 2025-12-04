import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_prices() -> pd.DataFrame:
    """
    Synthetic OHLCV with both ups and downs so all indicators are populated.
    """
    idx = pd.date_range("2024-01-01", periods=200, freq="D")
    values = 100 + np.sin(np.linspace(0, 12, 200)) * 5 + np.linspace(0, 2, 200)
    close = pd.Series(values, index=idx)
    return pd.DataFrame(
        {
            "open": close + 0.1,
            "high": close + 0.2,
            "low": close - 0.2,
            "close": close,
            "volume": np.arange(200, 400),
        }
    )
