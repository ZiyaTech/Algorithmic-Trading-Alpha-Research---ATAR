"""Vectorized PinBarEMARSI signal logic on explicitly completed OHLC bars.

Adapted from the author's vectorized implementation. The >= tail condition and
EMA sign-state reset are intentionally distinct from the serialized variant.
For the original minute-to-timeframe VBT API see integrations/vbtpro_pinbar.py.
"""
import numpy as np
import pandas as pd
from .common import inputs, signals, positive_int, finite


def generate(bars, *, pinbar_ratio=0.65, fast_ema_period=20, slow_ema_period=50,
             rsi_period=14, provider=None):
    finite(pinbar_ratio, "pinbar_ratio", 0.0, 1.0)
    for value in (fast_ema_period, slow_ema_period, rsi_period):
        positive_int(value, "indicator period", 2)
    if fast_ema_period >= slow_ema_period:
        raise ValueError("fast_ema_period must be smaller than slow_ema_period")
    df, ind = inputs(bars, provider)
    fast = ind.ema(df.close, fast_ema_period)
    slow = ind.ema(df.close, slow_ema_period)
    rsi = ind.rsi(df.close, rsi_period)
    state = pd.Series(np.nan, index=df.index)
    state[rsi > 80] = 1
    state[rsi < 20] = -1
    sign = pd.Series(np.where(fast - slow > 0, 2, -2), index=df.index)
    state[(sign == 2) & (sign.shift() == -2)] = 2
    state[(sign == -2) & (sign.shift() == 2)] = -2
    state = state.ffill()
    width = df.high - df.low
    upper = df.high - df[["open", "close"]].max(axis=1)
    lower = df[["open", "close"]].min(axis=1) - df.low
    bullish = (lower >= pinbar_ratio * width) & (df.close > df.open)
    bearish = (upper >= pinbar_ratio * width) & (df.close < df.open)
    return signals(bullish & (fast > slow) & (df.low < fast) & (state == 1),
                   bearish & (fast < slow) & (df.high > fast) & (state == -1), df.index)
