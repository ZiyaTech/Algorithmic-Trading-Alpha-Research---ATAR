"""Seven-lag trend score, EMA breakout and three-candle confirmation."""
import numpy as np
import pandas as pd
from .common import inputs, signals, positive_int, finite

EMA_OPTIONS = {1: (8, 20), 2: (12, 26), 3: (20, 50)}


def three_soldiers(df, ema_slow, *, bullish, body_ratio_threshold=0.6, bar_size_threshold=0.001):
    body = (df.close - df.open).abs()
    width = df.high - df.low
    ratio = body.div(width.where(width != 0)).fillna(0.0)
    valid = pd.Series(True, index=df.index)
    for lag in (0, 1, 2):
        valid &= (body.shift(lag) > ema_slow * bar_size_threshold) & (ratio.shift(lag) > body_ratio_threshold)
        valid &= (df.close.shift(lag) > df.open.shift(lag)) if bullish else (df.close.shift(lag) < df.open.shift(lag))
    for lag in (0, 1):
        valid &= (df.close.shift(lag) > df.close.shift(lag + 1)) if bullish else (df.close.shift(lag) < df.close.shift(lag + 1))
        valid &= (df.open.shift(lag) > df.open.shift(lag + 1)) if bullish else (df.open.shift(lag) < df.open.shift(lag + 1))
    return valid


def generate(bars, *, ema_periods_choice=2, bar_size_threshold=0.001,
             price_threshold=0.001, lookback_start=15, provider=None):
    positive_int(ema_periods_choice, "ema_periods_choice")
    positive_int(lookback_start, "lookback_start")
    finite(bar_size_threshold, "bar_size_threshold")
    finite(price_threshold, "price_threshold")
    if ema_periods_choice not in EMA_OPTIONS:
        raise ValueError("Unknown EMA pair")
    df, ind = inputs(bars, provider)
    score = pd.Series(0.0, index=df.index)
    for lag in range(lookback_start, lookback_start + 7):
        score += np.where(df.close > df.close.shift(lag), 1, np.where(df.close < df.close.shift(lag), -1, 0))
    smooth = ind.ema(score, 5)
    a, b = EMA_OPTIONS[ema_periods_choice]
    fast, slow = ind.ema(df.close, a), ind.ema(df.close, b)
    up = fast > slow
    breakout_up = (df.close > fast) & ((df.close - fast) / fast > price_threshold)
    breakout_down = (df.close < fast) & ((fast - df.close) / fast > price_threshold)
    return signals((smooth > 0) & up & breakout_up & three_soldiers(df, slow, bullish=True, bar_size_threshold=bar_size_threshold),
                   (smooth < 0) & ~up & breakout_down & three_soldiers(df, slow, bullish=False, bar_size_threshold=bar_size_threshold), df.index)
