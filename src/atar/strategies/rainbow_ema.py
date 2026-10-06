"""EMA ribbon ordering, historical trend context, pullback and slope filters."""
import pandas as pd
from .common import inputs, signals, positive_int, finite

PERIODS = (9, 13, 18, 22, 26, 31, 35, 39, 44, 48, 52, 57, 61, 65, 70, 74, 78, 83, 87, 91, 96, 100)


def generate(bars, *, lookback_bars=5, pullback_level=11, slope_threshold=0.0, provider=None):
    positive_int(lookback_bars, "lookback_bars")
    positive_int(pullback_level, "pullback_level")
    finite(slope_threshold, "slope_threshold")
    if pullback_level > len(PERIODS):
        raise ValueError("Pullback level exceeds ribbon length")
    df, ind = inputs(bars, provider)
    ema = {n: ind.ema(df.close, n) for n in PERIODS}
    slope = ema[9].diff() / ema[9]
    pullback = ema[PERIODS[pullback_level - 1]]
    up = pd.Series(True, index=df.index)
    down = pd.Series(True, index=df.index)
    for a, b in zip(PERIODS, PERIODS[1:]):
        up &= ema[a].shift(lookback_bars) > ema[b].shift(lookback_bars)
        down &= ema[a].shift(lookback_bars) < ema[b].shift(lookback_bars)
    return signals((df.close < pullback) & up & (slope > slope_threshold),
                   (df.close > pullback) & down & (slope < -slope_threshold), df.index)
