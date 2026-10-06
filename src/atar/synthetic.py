"""Deterministic artificial OHLC; not calibrated to any private instrument."""
import numpy as np
import pandas as pd


def market(*, bars=3200, seed=2026):
    if type(bars) is not int or bars < 2 or type(seed) is not int or seed < 0:
        raise ValueError("Require >=2 bars and a nonnegative integer seed")
    rng = np.random.default_rng(seed)
    t = np.arange(bars)
    innovation = rng.normal(0, 0.003, bars)
    movement = np.zeros(bars)
    for i in range(1, bars):
        movement[i] = 0.22 * movement[i - 1] + 0.0007 * np.sin(i / 140) + innovation[i]
    close = 100 * np.exp(np.cumsum(movement))
    opening = np.r_[100.0, close[:-1]] * np.exp(rng.normal(0, 0.0002, bars))
    upper = rng.gamma(1.1, 0.002, bars)
    lower = rng.gamma(1.1, 0.002, bars)
    return pd.DataFrame({"open": opening, "high": np.maximum(opening, close) * (1 + upper),
                         "low": np.minimum(opening, close) / (1 + lower), "close": close},
                        index=pd.date_range("2021-01-01", periods=bars, freq="h", tz="UTC"))
